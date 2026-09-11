"""ล็อก engine · หน้าต่างสะอาด · ความครอบคลุมความรู้ — PHASE M1.5

**สิ่งที่ไฟล์นี้ปกป้อง**

    1. หน้าต่างสะอาดต้องใช้ได้เฉพาะการวัด — การ fit น้ำหนักบนมันต้องพังทันที
    2. ลายนิ้วมือ engine ต้องขยับเมื่อไฟล์จริงขยับ ไม่ใช่ค่าคงที่ที่ต้องมาไล่แก้เอง
    3. ตัวที่ถูกแบนครั้งเดียวต้องไม่ขึ้นมาอยู่เหนือตัวที่เจอบ่อยจริง

ข้อ 1 สำคัญที่สุด — เราเหลือหลักฐานสะอาดศูนย์ชิ้นแล้ว ถ้าเผลอใช้หน้าต่างใหม่
ไปจูนอะไรสักอย่าง เราจะไม่มีวันพิสูจน์ได้อีกเลยว่า engine ดีขึ้นจริงไหม
"""

from __future__ import annotations

from datetime import date

import pytest
from rov.domain.enums import Confidence
from rov.draft import knowledgecoverage as kc
from rov.draft.counterknowledge import CounterBook, quality_report, quality_table
from rov.draft.heroes import Hero, HeroDB
from rov.draft.importer.parser import GameDraft, SeriesDraft
from rov.draft.stats import DraftStats, HeroStat
from rov.eval import version
from rov.eval.cleanwindow import (
    CLEAN_CUTOFF,
    CleanWindowMisuse,
    assert_measurement_only,
    clean_series,
    split_clean,
)


def game(winner: str = "x") -> GameDraft:
    return GameDraft(
        game_index=1, blue_team="x", red_team="y", winner_team=winner,
        blue_picks=["a", "b", "c", "d", "e"],
        red_picks=["f", "g", "h", "i", "j"],
        blue_bans=[], red_bans=[],
    )


def series(day: str, played: bool = True) -> SeriesDraft:
    return SeriesDraft(
        team1="x", team2="y", best_of=1, date=day,
        games=[game()] if played else [],
    )


# ───────────────────────────── หน้าต่างสะอาด · กติกาที่บังคับด้วยโค้ด


@pytest.mark.parametrize("purpose", ["measurement", "report"])
def test_measuring_is_allowed(purpose):
    assert_measurement_only(purpose)


@pytest.mark.parametrize(
    "purpose",
    ["weight_tuning", "threshold_tuning", "rule_selection", "fit", "training", ""],
)
def test_every_tuning_purpose_is_refused(purpose):
    """★ คุณสมบัติหลัก — ใช้หน้าต่างสะอาดจูนอะไรก็ตาม ต้องพังทันที"""
    with pytest.raises(CleanWindowMisuse):
        assert_measurement_only(purpose)


def test_the_refusal_says_why_not_just_that_it_refused():
    with pytest.raises(CleanWindowMisuse, match="หลักฐานอิสระ"):
        assert_measurement_only("weight_tuning")


def test_clean_series_refuses_the_same_way():
    with pytest.raises(CleanWindowMisuse):
        clean_series([series("October 1, 2026")], purpose="weight_tuning")


def test_the_cutoff_is_the_last_day_we_had_data_at_the_end_of_m1():
    assert CLEAN_CUTOFF == date(2026, 9, 6)


# ────────────────────────────────────────────── การแบ่งหน้าต่าง


def test_games_after_the_cutoff_land_in_the_clean_window():
    seen, win = split_clean([series("September 1, 2026"), series("October 1, 2026")])
    assert len(seen) == 1 and len(win.series) == 1
    assert win.games == 1 and win.ready


def test_a_game_exactly_on_the_cutoff_is_not_clean():
    """ตัดที่ 'หลัง' ไม่ใช่ 'ตั้งแต่' — วันนั้นถูกใช้ไปแล้ว"""
    seen, win = split_clean([series("September 6, 2026")])
    assert len(seen) == 1 and win.games == 0


def test_scheduled_but_unplayed_series_are_counted_separately():
    """นัดที่ยังไม่แข่ง ไม่ใช่ข้อมูล — แต่บอกได้ว่าอีกนานแค่ไหนจะมี"""
    _seen, win = split_clean([series("October 1, 2026", played=False)])
    assert win.games == 0 and win.scheduled == 1
    assert not win.ready
    assert win.first_scheduled == date(2026, 10, 1)


@pytest.mark.parametrize("raw", ["ไม่ใช่วันที่", "2026-10-01", None])
def test_an_unreadable_date_goes_to_the_seen_side_not_the_clean_side(raw):
    """★ เดาผิดทางไหนแพงกว่า — ปนเปื้อนหน้าต่างสะอาดแพงกว่าเสียตัวอย่าง

    `parse_date` ตั้งใจรับเฉพาะรูปแบบของ Liquipedia (ดู test_scouting.py)
    วันที่รูปแบบ ISO จึงอ่านไม่ออก และต้องตกไปฝั่ง "เคยดูแล้ว" ไม่ใช่ฝั่งสะอาด
    ซึ่งเป็นทิศทางที่ปลอดภัยกว่า
    """
    seen, win = split_clean([series(raw)])
    assert len(seen) == 1 and win.games == 0


def test_an_empty_window_says_so_instead_of_pretending():
    _seen, win = split_clean([series("January 1, 2026")])
    assert not win.ready
    assert "ว่าง" in win.status


def test_the_report_tells_people_not_to_fall_back_to_old_windows():
    _seen, win = split_clean([series("January 1, 2026")])
    from rov.eval.cleanwindow import report

    text = report(win)
    assert "ห้ามถอยไปใช้หน้าต่างเดิม" in text
    assert "ห้ามใช้" in text or "ใช้ไม่ได้" in text


# ──────────────────────────────────────────────── ลายนิ้วมือ engine


def test_version_reads_the_real_files():
    v = version.current()
    assert v.code and all(h for h in v.code.values()), "ไฟล์โค้ดต้องอ่านได้ทุกไฟล์"
    assert len(v.fingerprint) == 12


def test_the_fingerprint_moves_when_any_layer_moves():
    """ถ้าแก้โค้ด แก้ความรู้ หรือแก้น้ำหนัก ลายนิ้วมือต้องเปลี่ยน"""
    base = version.current()
    moved = version.EngineVersion(
        commit=base.commit, code={**base.code, "x.py": "ต่างออกไป"},
        knowledge=base.knowledge, weights=base.weights,
    )
    assert moved.fingerprint != base.fingerprint

    moved2 = version.EngineVersion(
        commit=base.commit, code=base.code,
        knowledge={**base.knowledge, "y.yaml": "ต่างออกไป"}, weights=base.weights,
    )
    assert moved2.fingerprint != base.fingerprint

    moved3 = version.EngineVersion(
        commit=base.commit, code=base.code, knowledge=base.knowledge,
        weights={**base.weights, "ban_meta_share": 0.99},
    )
    assert moved3.fingerprint != base.fingerprint


def test_the_same_state_gives_the_same_fingerprint():
    assert version.current().fingerprint == version.current().fingerprint


def test_a_dirty_tree_is_not_comparable():
    """ผลที่วัดจากของที่ยังไม่ commit ไม่มีใครย้อนกลับมาดูได้"""
    v = version.EngineVersion(commit="abc1234", dirty=True)
    assert not v.comparable
    assert version.EngineVersion(commit="abc1234", dirty=False).comparable
    assert not version.EngineVersion(commit=None).comparable


def test_the_version_report_shows_which_extra_weights_are_on():
    text = version.report()
    assert "extra" in text
    assert "ทุกตัวยัง 0" in text, "ตอนนี้ยังไม่ควรมี extra weight ตัวไหนเปิด"


# ──────────────────────────────────────── ความครอบคลุมความรู้


def hk(**kw) -> kc.HeroKnowledge:
    base = dict(hero_id="h", name="H", total_games=100)
    base.update(kw)
    return kc.HeroKnowledge(**base)


def test_tier_a_needs_all_three_layers():
    assert hk(has_class=True, has_assessment=True, has_threat=True).tier == "A"
    assert hk(has_class=True, has_assessment=True).tier == "B", "ขาด counter knowledge"
    assert hk(has_class=True, has_threat=True).tier == "B", "ขาด assessment"
    assert hk(has_class=True).tier == "C"
    assert hk().tier == "C"


def test_a_mechanism_alone_also_counts_as_counter_knowledge():
    assert hk(has_class=True, has_assessment=True, has_mechanism=True).tier == "A"


def test_a_complete_hero_never_needs_filling():
    h = hk(has_class=True, has_assessment=True, has_threat=True, picks=300, bans=300)
    assert h.priority == 0.0, "ตัวที่ครบแล้วต้องไม่โผล่ในคิว ไม่ว่าจะดังแค่ไหน"


def test_ban_lean_is_shrunk_by_sample_size():
    """★ บั๊กที่เจอจริง — แบน 1 เลือก 0 เคยได้ ban_lean เต็ม 1.0

    ผลคือ mortos กับ aleister (presence 0%) ขึ้นมาอันดับ 3 และ 4
    เหนือตัวที่ presence 20%
    """
    tiny = hk(bans=1, picks=0)
    big = hk(bans=110, picks=19)
    assert tiny.ban_lean < 0.2, "ตัวอย่างเดียวต้องไม่ได้ค่าเต็ม"
    assert big.ban_lean > tiny.ban_lean


def test_a_rarely_seen_hero_does_not_outrank_a_common_one():
    tiny = hk(bans=1, picks=0)
    common = hk(picks=107, bans=45)
    assert common.priority > tiny.priority


def test_being_a_counter_target_raises_priority():
    plain = hk(picks=100, bans=100)
    target = hk(picks=100, bans=100, is_counter_target=True)
    assert target.priority > plain.priority


def test_tier_b_is_cheaper_to_finish_than_tier_c():
    """ตัวที่กรอกไปครึ่งทางแล้ว ควรได้คะแนนน้อยกว่าตัวที่ยังไม่เริ่ม ถ้าดังเท่ากัน"""
    b = hk(has_class=True, has_assessment=True, picks=100, bans=100)
    c = hk(has_class=True, picks=100, bans=100)
    assert b.tier == "B" and c.tier == "C"
    assert c.priority > b.priority


def test_missing_lists_exactly_what_is_missing():
    h = hk(has_class=False, has_assessment=False, missing_fields=["a", "b"])
    assert h.missing == ["hero_class", "assessment (2 ช่อง)", "counter knowledge"]
    full = hk(has_class=True, has_assessment=True, has_threat=True)
    assert full.missing == []


def test_coverage_shares_add_up():
    db = HeroDB(heroes=[Hero(id="a"), Hero(id="b"), Hero(id="c")])
    stats = DraftStats(total_games=10)
    stats.heroes = {
        "a": HeroStat(hero_id="a", picks=5, bans=1),
        "b": HeroStat(hero_id="b", picks=1, bans=0),
        "c": HeroStat(hero_id="c", picks=0, bans=0),
    }
    cov = kc.build(db, stats, CounterBook())
    assert sum(cov.counts.values()) == 3
    assert cov.share("C") == pytest.approx(1.0), "ไม่มี assessment เลย ต้องเป็น C หมด"
    assert sum(cov.presence_share(t) for t in ("A", "B", "C")) == pytest.approx(1.0)


def test_presence_share_is_not_the_same_as_head_count():
    """รู้ 1 ตัวจาก 3 แต่ตัวนั้นถูกใช้ 80% ของเวลา — สองตัวเลขนี้ต้องต่างกัน"""
    db = HeroDB(heroes=[Hero(id="a"), Hero(id="b"), Hero(id="c")])
    stats = DraftStats(total_games=10)
    stats.heroes = {
        "a": HeroStat(hero_id="a", picks=8, bans=0),
        "b": HeroStat(hero_id="b", picks=1, bans=0),
        "c": HeroStat(hero_id="c", picks=1, bans=0),
    }
    cov = kc.build(db, stats, CounterBook())
    assert cov.share("C") == pytest.approx(1.0)
    assert cov.presence_share("C") == pytest.approx(1.0)


def test_the_real_database_is_mostly_unknown():
    """ตัวเลขจริงต้องรายงานตรง ๆ — ห้ามให้ใครมาทำให้มันดูดีกว่าความจริง"""
    from rov.draft.meta import pool

    try:
        from rov.cli.main import _regions

        regions = _regions()
    except Exception:  # noqa: BLE001
        pytest.skip("ยังไม่มีข้อมูลใน cache")
    if not regions:
        pytest.skip("ยังไม่มีข้อมูลใน cache")
    cov = kc.build(
        HeroDB.load("configs/draft/heroes.yaml"), pool(regions).stats, CounterBook.load()
    )
    assert cov.counts["C"] > cov.counts["A"], "ตอนนี้ยังไม่รู้มากกว่ารู้"
    assert cov.share("A") < 0.5


# ─────────────────────────────────────── คุณภาพหลักฐาน counter


def test_quality_table_keeps_both_sides():
    book = CounterBook.load()
    if not book.evidence:
        pytest.skip("ยังไม่มีความรู้")
    rows = quality_table(book)
    assert len(rows) == len(book.evidence)
    for r in rows:
        assert r.knowledge_claim.strip(), "ต้องเก็บข้ออ้างฝั่งความรู้ไว้"
        assert r.data_detail.strip(), "ต้องเก็บผลฝั่งข้อมูลไว้"
        assert r.verdict in ("agree", "disagree", "partial", "insufficient")


def test_a_disagreeing_rule_still_stands():
    """★ disagree ≠ rule invalid — ข้ออ้างทุกข้อยังอยู่ในระบบ"""
    book = CounterBook.load()
    if not book.evidence:
        pytest.skip("ยังไม่มีความรู้")
    rows = quality_table(book)
    bad = [r for r in rows if r.verdict == "disagree"]
    assert bad, "ตอนนี้ควรมีข้อที่ข้อมูลค้านอยู่จริง"
    assert all(r.rule_still_stands for r in bad)
    assert all(r.confidence is not Confidence.HIGH for r in bad), "แต่ต้องไม่ HIGH"


def test_the_quality_report_says_disagree_is_not_invalid():
    book = CounterBook.load()
    if not book.evidence:
        pytest.skip("ยังไม่มีความรู้")
    text = quality_report(book)
    assert "disagree ไม่ได้แปลว่า rule ใช้ไม่ได้" in text
