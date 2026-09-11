"""คอมพ์ของแต่ละทีม — rov/draft/teamcomp.py

**สิ่งที่ไฟล์นี้ปกป้องเป็นหลัก**

    "ไม่รู้ class" ต้องไม่ถูกนับเป็น "รู้ว่าไม่มี class นั้น"

ถ้าคุณสมบัตินี้หลุด ทีมที่ใช้ฮีโร่นอกฐานข้อมูลจะถูกรายงานว่า "ไม่มีแทงค์"
ทั้งที่ความจริงคือเราไม่รู้ ซึ่งเป็นการเติมข้อเท็จจริงที่ไม่มีที่มา
"""

from __future__ import annotations

import pytest
from rov.domain.enums import HeroClass
from rov.draft.heroes import Hero, HeroDB
from rov.draft.importer.parser import GameDraft, SeriesDraft
from rov.draft.teamcomp import (
    MIN_COMPS,
    SHAPES,
    Comp,
    ShapeRule,
    ban_slots,
    chance_threshold,
    collect_comps,
    league_shape_rates,
    newest_first,
    pair_bonds,
    repeat_stats,
    report,
    shape_rates,
    team_comp_profiles,
)


def hero(hid: str, *classes: HeroClass) -> Hero:
    return Hero(id=hid, hero_class=list(classes))


@pytest.fixture
def db() -> HeroDB:
    """ฐานข้อมูลเล็ก ๆ — t* แทงค์ · m* เมจ · a* อัสแซสซิน · k* มาร์คแมน · s* ซัพ"""
    return HeroDB(
        heroes=[
            hero("t1", HeroClass.TANK), hero("t2", HeroClass.TANK),
            hero("m1", HeroClass.MAGE), hero("m2", HeroClass.MAGE),
            hero("a1", HeroClass.ASSASSIN), hero("a2", HeroClass.ASSASSIN),
            hero("k1", HeroClass.MARKSMAN),
            hero("s1", HeroClass.SUPPORT), hero("s2", HeroClass.SUPPORT),
            hero("w1", HeroClass.WARRIOR),
            hero("ghost"),  # อยู่ในฐานข้อมูลแต่ยังไม่รู้ class
        ]
    )


def by_id(db: HeroDB) -> dict:
    return {h.id: h for h in db.heroes}


def hits_by_key(rows: list[Comp], db: HeroDB) -> dict[str, int]:
    rates, _ = shape_rates(rows, by_id(db), {r.key: 0.0 for r in SHAPES})
    return {r.rule.key: r.hits for r in rates}


def comps(team: str, *rows: tuple[str, ...]) -> list[Comp]:
    return [Comp(team=team, heroes=r, won=i % 2 == 0, blue=True) for i, r in enumerate(rows)]


# ───────────────────────────────────── ไม่รู้ ≠ รู้ว่าไม่มี  (แกนของไฟล์นี้)


def test_unknown_hero_class_is_skipped_not_counted_as_absent(db):
    """★ คุณสมบัติหลัก

    คอมพ์ที่มี `unknown_hero` ต้องถูกข้าม ไม่ใช่ถูกนับว่า "ไม่มีแทงค์"
    """
    rows = comps("x", ("m1", "m2", "a1", "k1", "unknown_hero"))
    rates, skipped = shape_rates(rows, by_id(db), {r.key: 0.0 for r in SHAPES})
    assert skipped == 1
    assert all(r.n == 0 for r in rates), "คอมพ์ที่ไม่รู้ class ต้องไม่เข้าไปอยู่ในตัวหาร"
    assert all(r.hits == 0 for r in rates)


def test_hero_present_in_db_but_without_class_is_also_skipped(db):
    """'ghost' มีอยู่ในฐานข้อมูลแต่ช่อง hero_class ว่าง — ยังถือว่าไม่รู้"""
    rows = comps("x", ("m1", "m2", "a1", "k1", "ghost"))
    _rates, skipped = shape_rates(rows, by_id(db), {r.key: 0.0 for r in SHAPES})
    assert skipped == 1


def test_a_comp_with_every_class_known_is_counted(db):
    rows = comps("x", ("m1", "m2", "a1", "k1", "w1"))
    rates, skipped = shape_rates(rows, by_id(db), {r.key: 0.0 for r in SHAPES})
    assert skipped == 0
    assert all(r.n == 1 for r in rates)


# ────────────────────────────────────────────────── การตรวจจับรูปทรง


def test_no_tank_is_detected(db):
    rows = comps("x", ("m1", "m2", "a1", "k1", "w1"))
    rates, _ = shape_rates(rows, by_id(db), {r.key: 0.0 for r in SHAPES})
    got = {r.rule.key: r.hits for r in rates}
    assert got["no_tank"] == 1
    assert got["two_tank"] == 0


def test_two_tank_and_two_mage_are_detected(db):
    rows = comps("x", ("t1", "t2", "m1", "m2", "k1"))
    got = hits_by_key(rows, db)
    assert got["two_tank"] == 1
    assert got["two_mage"] == 1
    assert got["no_tank"] == 0
    assert got["no_marksman"] == 0


def test_no_marksman_is_detected(db):
    rows = comps("x", ("t1", "t2", "m1", "m2", "a1"))
    got = hits_by_key(rows, db)
    assert got["no_marksman"] == 1


def test_shape_rules_are_frozen_and_declared_up_front():
    """ชุดรูปทรงต้องเป็นค่าคงที่ ไม่ใช่สิ่งที่ถูกเลือกทีหลังตามผลของทีม"""
    assert isinstance(SHAPES, tuple)
    assert len(SHAPES) == 6
    assert all(isinstance(r, ShapeRule) for r in SHAPES)
    assert all(r.why.strip() for r in SHAPES), "ทุกทรงต้องอธิบายว่าทำไมถึงสำคัญ"
    assert len({r.key for r in SHAPES}) == len(SHAPES)


def test_a_rule_needs_at_least_one_bound():
    """กติกาที่ไม่มีขอบเขตจะเป็นจริงเสมอ — ตรวจว่าไม่มีอันแบบนั้นหลุดเข้ามา"""
    for r in SHAPES:
        assert r.at_least is not None or r.at_most is not None


# ────────────────────────────────────────────── เส้นฐานลีก และนัยสำคัญ


def test_league_baseline_pools_all_comps_not_average_of_teams(db):
    """ทีมเล็กต้องไม่มีน้ำหนักเท่าทีมใหญ่

    big เล่น 'ไม่มีแทงค์' 4 ครั้ง · small เล่น 0 ครั้งจาก 1 คอมพ์
    ถ้าเฉลี่ยรายทีมจะได้ 0.5 · ถ้ารวมกองเดียว (ถูกต้อง) จะได้ 4/5 = 0.8
    """
    rows = comps("big", *[("m1", "m2", "a1", "k1", "w1")] * 4)
    rows += comps("small", ("t1", "t2", "m1", "k1", "w1"))
    league, n = league_shape_rates(rows, by_id(db))
    assert n == 5
    assert league["no_tank"] == pytest.approx(0.8)


def test_shape_is_not_notable_when_interval_straddles_the_league(db):
    """ตัวอย่างน้อย ช่วงกว้าง ต้องไม่ประกาศว่าต่างจากลีก"""
    rows = comps("x", *[("m1", "m2", "a1", "k1", "w1")] * 3)
    rates, _ = shape_rates(rows, by_id(db), {r.key: 0.5 for r in SHAPES})
    assert all(not r.notable for r in rates), "n=3 ไม่ควรพอที่จะประกาศอะไร"


def test_shape_below_min_comps_is_never_notable(db):
    """แม้อัตราจะสุดขั้ว 100% ถ้าคอมพ์ไม่ถึงเกณฑ์ก็ยังห้ามประกาศ"""
    n = MIN_COMPS - 1
    rows = comps("x", *[("m1", "m2", "a1", "k1", "w1")] * n)
    rates, _ = shape_rates(rows, by_id(db), {r.key: 0.0 for r in SHAPES})
    no_tank = next(r for r in rates if r.rule.key == "no_tank")
    assert no_tank.rate == 1.0
    assert not no_tank.notable


def test_a_clear_difference_on_enough_comps_is_notable(db):
    rows = comps("x", *[("m1", "m2", "a1", "k1", "w1")] * MIN_COMPS)
    rates, _ = shape_rates(rows, by_id(db), {r.key: 0.1 for r in SHAPES})
    no_tank = next(r for r in rates if r.rule.key == "no_tank")
    assert no_tank.notable
    assert no_tank.direction == "มากกว่าลีก"


def test_win_rate_is_none_when_the_shape_never_happened(db):
    rows = comps("x", ("t1", "t2", "m1", "m2", "k1"))
    rates, _ = shape_rates(rows, by_id(db), {r.key: 0.0 for r in SHAPES})
    no_tank = next(r for r in rates if r.rule.key == "no_tank")
    assert no_tank.hits == 0
    assert no_tank.win_rate is None, "ไม่มีเกม ต้องเป็น None ไม่ใช่ 0.0"


# ──────────────────────────────────────────────────────── ความซ้ำของชุด


def test_repeat_stats_counts_distinct_sets():
    rows = comps(
        "x",
        ("a", "b", "c", "d", "e"),
        ("a", "b", "c", "d", "e"),
        ("a", "b", "c", "d", "f"),
    )
    st = repeat_stats(rows)
    assert (st.total, st.distinct, st.max_repeat, st.repeated_sets) == (3, 2, 2, 1)


def test_comp_identity_ignores_pick_order():
    """คอมพ์เดียวกันที่ดราฟต์คนละลำดับ ต้องนับเป็นชุดเดียวกัน"""
    rows = comps("x", ("a", "b", "c", "d", "e"), ("e", "d", "c", "b", "a"))
    assert repeat_stats(rows).distinct == 1


def test_verdict_says_no_repeat_when_nothing_repeats():
    rows = comps("x", *[(f"h{i}", "b", "c", "d", "e") for i in range(10)])
    assert repeat_stats(rows).verdict == "ไม่เล่นชุดเดิมซ้ำ"


def test_verdict_changes_when_a_set_really_does_repeat():
    rows = comps("x", *[("a", "b", "c", "d", "e")] * 6)
    st = repeat_stats(rows)
    assert st.max_repeat == 6
    assert st.verdict == "มีชุดที่ใช้ซ้ำจริง"


# ──────────────────────────────────────────── คู่ที่เกินความบังเอิญ


def test_chance_threshold_is_deterministic():
    """ตรึง seed ไว้ ผลต้องซ้ำได้ ไม่งั้นหน้าเว็บจะเปลี่ยนทุกครั้งที่ build"""
    rows = comps("x", *[(f"h{i}", f"g{i}", "c", "d", "e") for i in range(50)])
    assert chance_threshold(rows, rounds=50) == chance_threshold(rows, rounds=50)


def test_pair_bonds_is_empty_when_nothing_beats_chance():
    rows = comps("x", *[(f"h{i}", f"g{i}", f"j{i}", f"k{i}", f"l{i}") for i in range(30)])
    assert pair_bonds(rows, threshold=5) == []


def test_pair_bonds_finds_a_pair_that_moves_together():
    """คู่ที่โผล่ครึ่งหนึ่งของเกม แต่โผล่พร้อมกันเสมอ — นั่นคือความผูกพันจริง

    แต่ละตัวอยู่ 10 จาก 20 คอมพ์ ถ้าเลือกอิสระต่อกันจะเจอด้วยกัน 5 ครั้ง
    เจอจริง 10 ครั้ง = lift 2.0
    """
    rows = comps(
        "x",
        *[("glue1", "glue2", f"h{i}", f"g{i}", f"j{i}") for i in range(10)],
        *[(f"p{i}", f"q{i}", f"r{i}", f"s{i}", f"u{i}") for i in range(10)],
    )
    bonds = pair_bonds(rows, threshold=5)
    assert bonds, "คู่ที่ขยับไปด้วยกันเสมอต้องถูกพบ"
    assert {bonds[0].a, bonds[0].b} == {"glue1", "glue2"}
    assert bonds[0].together == 10
    assert bonds[0].expected == pytest.approx(5.0)
    assert bonds[0].lift == pytest.approx(2.0)


def test_two_heroes_the_team_always_picks_are_not_reported_as_a_bond():
    """★ คู่ที่อยู่ด้วยกันเพราะทั้งคู่ถูกหยิบทุกเกม ไม่ใช่คอมโบ

    ถ้าปล่อยผ่าน หน้าเว็บจะประกาศว่าสองตัวที่ทีมหยิบตลอดเป็น "คู่ประจำ"
    ทั้งที่ความถี่รายตัวอธิบายได้หมดแล้ว — lift ของมันคือ 1.0 พอดี
    """
    rows = comps("x", *[("always1", "always2", f"h{i}", f"g{i}", f"j{i}") for i in range(20)])
    assert pair_bonds(rows, threshold=5) == []


def test_zero_threshold_reports_nothing_rather_than_everything():
    """ทีมที่เล็กเกินจะตั้งเกณฑ์ได้ ต้องไม่กลายเป็นทีมที่ 'ทุกคู่มีความหมาย'"""
    rows = comps("x", ("a", "b", "c", "d", "e"))
    assert pair_bonds(rows, threshold=0) == []


# ─────────────────────────────────────────────────── การประกอบทั้งหมด


def draft(team_a: str, a_picks: list[str], team_b: str, b_picks: list[str]) -> GameDraft:
    return GameDraft(
        game_index=1, blue_team=team_a, red_team=team_b, winner_team=team_a,
        blue_picks=a_picks, red_picks=b_picks,
        blue_bans=[], red_bans=[],
    )


def test_collect_comps_reads_both_sides():
    s = SeriesDraft(
        team1="x", team2="y", best_of=1, date="2026-01-01",
        games=[draft("x", ["a", "b", "c", "d", "e"], "y", ["f", "g", "h", "i", "j"])],
    )
    got = collect_comps([s])
    assert set(got) == {"x", "y"}
    assert got["x"][0].won is True
    assert got["y"][0].won is False
    assert got["x"][0].blue is True and got["y"][0].blue is False


def test_teams_below_the_threshold_are_left_out(db):
    s = SeriesDraft(
        team1="x", team2="y", best_of=1, date="2026-01-01",
        games=[draft("x", ["t1", "t2", "m1", "m2", "k1"], "y", ["a1", "a2", "m1", "k1", "w1"])],
    )
    assert team_comp_profiles([s], db) == {}, "ทีมที่มีคอมพ์เดียวต้องไม่ถูกรายงาน"


def test_profile_reports_honestly_when_there_is_nothing_to_say(db):
    """ทีมที่เล่นเหมือนลีกเป๊ะ ต้องได้รายงานว่า 'ไม่มี' ไม่ใช่ถูกยัดอะไรมาให้"""
    rows = comps("x", *[("t1", "m1", "a1", "k1", "w1")] * 50)
    league, _ = league_shape_rates(rows, by_id(db))
    rates, _ = shape_rates(rows, by_id(db), league)
    assert not any(r.notable for r in rates)


def test_report_mentions_the_repeat_finding_and_survives_empty_sections(db):
    rows = comps("x", *[("t1", "m1", "a1", "k1", "w1")] * 45)
    league, _ = league_shape_rates(rows, by_id(db))
    rates, skipped = shape_rates(rows, by_id(db), league)
    from rov.draft.teamcomp import TeamCompProfile

    p = TeamCompProfile(
        team="x", comps=rows, repeats=repeat_stats(rows),
        shapes=rates, bonds=[], bond_threshold=7, skipped_unknown_class=skipped,
    )
    text = report(p)
    assert "ชุด 5 ตัวซ้ำไหม" in text
    assert "ไม่มี — ทุกทรงอยู่ในช่วงเดียวกับลีก" in text
    assert "ไม่มี — เกณฑ์ความบังเอิญอยู่ที่ 7 ครั้ง" in text


# ─────────────────────────────────── วันที่ · การเรียง · ตาแบน


def dated(team: str, *rows: tuple[str, tuple[str, ...]]) -> list[Comp]:
    return [
        Comp(team=team, heroes=h, won=True, blue=True, date=d)
        for d, h in rows
    ]


def test_newest_first_sorts_by_time_not_alphabetically():
    """★ บั๊กที่เคยหลุดจริง

    วันที่ดิบของ Liquipedia คือ "September 7, 2025 - 18:00 {{Abbr/ICT}}"
    การ sort สตริงแบบนั้นได้ลำดับตามตัวอักษร ทำให้ September มาก่อน May
    แล้วหน้าเว็บจะขึ้นเกมเก่าที่สุดในช่อง "30 เกมล่าสุด"
    """
    rows = dated(
        "x",
        ("2025-09-07", ("a",)),
        ("2026-05-09", ("b",)),
        ("2026-01-02", ("c",)),
    )
    assert [c.date for c in newest_first(rows)] == [
        "2026-05-09", "2026-01-02", "2025-09-07",
    ]


def test_comps_without_a_date_go_last_not_first():
    """เกมที่อ่านวันที่ไม่ได้ ต้องไม่ถูกนำเสนอว่าเป็นเกมล่าสุด"""
    rows = dated("x", ("2026-05-09", ("a",)), (None, ("b",)), ("2026-01-02", ("c",)))
    assert [c.date for c in newest_first(rows)] == ["2026-05-09", "2026-01-02", None]


def test_collect_comps_stores_an_iso_date_not_raw_wikitext():
    s = SeriesDraft(
        team1="x", team2="y", best_of=1,
        date="September 7, 2025 - 18:00 {{Abbr/ICT}}",
        games=[draft("x", ["a", "b", "c", "d", "e"], "y", ["f", "g", "h", "i", "j"])],
    )
    assert collect_comps([s])["x"][0].date == "2025-09-07"


def test_an_unparsable_date_becomes_none_rather_than_today():
    s = SeriesDraft(
        team1="x", team2="y", best_of=1, date="ไม่ใช่วันที่",
        games=[draft("x", ["a", "b", "c", "d", "e"], "y", ["f", "g", "h", "i", "j"])],
    )
    assert collect_comps([s])["x"][0].date is None


def test_collect_comps_records_the_opponent_and_side():
    s = SeriesDraft(
        team1="x", team2="y", best_of=1, date="2026-01-01",
        games=[draft("x", ["a", "b", "c", "d", "e"], "y", ["f", "g", "h", "i", "j"])],
    )
    got = collect_comps([s])
    assert got["x"][0].opponent == "y" and got["x"][0].blue is True
    assert got["y"][0].opponent == "x" and got["y"][0].blue is False


def test_ban_slots_keep_draft_order_separate():
    """ตาแบนที่ 1 กับที่ 3 ต้องนับแยกกัน ไม่ใช่กองรวมเป็นเซ็ตเดียว"""
    rows = [
        Comp(team="x", heroes=("a",), won=True, blue=True, bans=("first", "second")),
        Comp(team="x", heroes=("b",), won=True, blue=True, bans=("first", "third")),
    ]
    slots = ban_slots(rows)
    assert [s.slot for s in slots] == [1, 2]
    assert slots[0].picks["first"] == 2 and slots[0].n == 2
    assert slots[1].picks["second"] == 1 and slots[1].picks["third"] == 1


def test_ban_slot_concentration_shows_how_predictable_the_turn_is():
    same = [
        Comp(team="x", heroes=("a",), won=True, blue=True, bans=("always",))
        for _ in range(10)
    ]
    assert ban_slots(same)[0].concentration == pytest.approx(1.0)
    spread = [
        Comp(team="x", heroes=("a",), won=True, blue=True, bans=(f"h{i}",))
        for i in range(10)
    ]
    assert ban_slots(spread)[0].concentration == pytest.approx(0.3)


def test_a_team_with_no_bans_recorded_gets_an_empty_list():
    rows = [Comp(team="x", heroes=("a",), won=True, blue=True)]
    assert ban_slots(rows) == []
