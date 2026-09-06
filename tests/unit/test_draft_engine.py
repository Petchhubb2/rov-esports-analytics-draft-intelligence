"""ทดสอบ stats, hero attribute และ composition engine

**หมายเหตุสำคัญ** ค่า attribute ของฮีโร่ในไฟล์นี้เป็นข้อมูลสมมติสำหรับทดสอบ
ตั้งชื่อขึ้นต้นด้วย demo_ เพื่อไม่ให้ปนกับฮีโร่จริง
ห้ามคัดลอกไปใส่ configs/draft/heroes.yaml
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rov.domain.enums import DamageType, HeroClass, LaneRole
from rov.draft.composition import (
    IncompleteDataError,
    _saturating_sum,
    _top_weighted,
    analyze,
    compare,
)
from rov.draft.heroes import Hero, HeroDB
from rov.draft.importer.heroinfo import build_alias_index, parse_hero_classes, resolve
from rov.draft.importer.parser import normalize_hero_id, parse_page
from rov.draft.stats import (
    SHRINKAGE_K,
    compute_matchups,
    compute_stats,
    compute_synergies,
    hero_priority_order,
)

FIXTURE = Path("tests/fixtures/liquipedia_rpl_sample.wikitext")


@pytest.fixture(scope="module")
def series():
    return parse_page(FIXTURE.read_text(encoding="utf-8"))


# ------------------------------------------------------- normalize hero id


def test_apostrophe_variants_merge():
    """บั๊กจริง: eland'orr กับ elandorr เป็นตัวเดียวกันแต่ถูกนับแยก"""
    assert normalize_hero_id("eland'orr") == normalize_hero_id("elandorr")
    assert normalize_hero_id("y'bneth") == normalize_hero_id("ybneth")


def test_spaces_become_underscore():
    assert normalize_hero_id("Bolt Baron") == "bolt_baron"


def test_case_is_normalized():
    assert normalize_hero_id("Sinestrea") == "sinestrea"


def test_different_heroes_stay_different():
    assert normalize_hero_id("marja") != normalize_hero_id("murad")


# ------------------------------------------------------------------- stats


def test_stats_count_only_complete_games(series):
    st = compute_stats(series)
    assert st.total_games > 0
    assert st.total_games <= sum(len(s.games) for s in series)


def test_pick_counts_are_consistent(series):
    """แต่ละเกมมี 10 pick พอดี ผลรวม pick จึงต้องเป็น 10 เท่าของจำนวนเกม"""
    st = compute_stats(series)
    assert sum(h.picks for h in st.heroes.values()) == st.total_games * 10


def test_wins_never_exceed_picks(series):
    st = compute_stats(series)
    for h in st.heroes.values():
        assert 0 <= h.wins <= h.picks


def test_shrinkage_pulls_small_samples_toward_prior():
    """ฮีโร่ที่เล่น 3 เกมชนะ 3 ต้องไม่ได้ 100%"""
    from rov.draft.stats import HeroStat

    h = HeroStat(hero_id="x", picks=3, wins=3)
    assert h.raw_win_rate == 1.0
    adj = h.adjusted_win_rate(0.5)
    assert adj < 0.6, f"shrinkage ไม่ทำงาน ได้ {adj}"
    assert adj > 0.5


def test_shrinkage_trusts_large_samples_more():
    from rov.draft.stats import HeroStat

    small = HeroStat(hero_id="a", picks=5, wins=4)
    large = HeroStat(hero_id="b", picks=200, wins=160)
    # อัตราชนะดิบเท่ากัน แต่ตัวที่เล่นเยอะต้องได้ค่าที่ใกล้ของจริงกว่า
    assert small.raw_win_rate == large.raw_win_rate == 0.8
    assert large.adjusted_win_rate(0.5) > small.adjusted_win_rate(0.5)


def test_confidence_grows_with_sample_size():
    from rov.draft.stats import HeroStat

    assert HeroStat("x", picks=0).confidence() == 0.0
    assert HeroStat("x", picks=SHRINKAGE_K).confidence() == pytest.approx(0.5)
    assert HeroStat("x", picks=1000).confidence() > 0.95


def test_priority_order_is_by_presence(series):
    st = compute_stats(series)
    order = hero_priority_order(st)
    presences = [p for _, p, _ in order]
    assert presences == sorted(presences, reverse=True)


def test_matchups_are_symmetric_in_games(series):
    """ถ้า A เจอ B n ครั้ง แล้ว B ก็ต้องเจอ A n ครั้ง"""
    mu = compute_matchups(series)
    for (a, b), m in mu.items():
        rev = mu.get((b, a))
        assert rev is not None
        assert rev.games == m.games
        assert rev.wins == m.games - m.wins


def test_counter_score_is_zero_without_data():
    from rov.draft.stats import MatchupStat

    assert MatchupStat("a", "b").counter_score(0.5) == 0.0


def test_synergy_pairs_stored_one_direction(series):
    syn = compute_synergies(series)
    for a, b in syn:
        assert a < b, "ต้องเก็บทิศทางเดียวเพื่อไม่ให้นับซ้ำ"


# -------------------------------------------------------------- hero schema


def _demo(hid: str, **over) -> Hero:
    """ฮีโร่สมมติสำหรับทดสอบ — ค่าทั้งหมดตั้งขึ้น ไม่ใช่ข้อมูลจริง"""
    base = dict(
        id=hid,
        hero_class=[HeroClass.WARRIOR],
        lane_roles=[LaneRole.DS],
        range="melee",
        damage={"type": DamageType.PHYSICAL, "profile": "sustained", "target": "single"},
        scaling={"early": 60, "mid": 60, "late": 60},
        utility=dict.fromkeys(
            ["engage", "disengage", "peel", "cc_hard", "cc_soft", "mobility",
             "poke", "sustain", "frontline", "objective", "waveclear", "splitpush"], 50),
    )
    for k, v in over.items():
        if k in ("utility", "scaling", "damage") and isinstance(v, dict):
            base[k] = {**base[k], **v}  # type: ignore[dict-item]
        else:
            base[k] = v
    return Hero.model_validate(base)


def test_empty_hero_is_incomplete():
    h = Hero(id="demo_x")
    assert not h.complete
    assert "lane_roles" in h.missing_fields()
    assert "utility.engage" in h.missing_fields()


def test_filled_hero_is_complete():
    assert _demo("demo_a").complete


def test_rating_out_of_range_is_rejected():
    with pytest.raises(ValueError, match="0-100"):
        _demo("demo_a", utility={"engage": 150})


def test_reading_unfilled_attribute_raises_not_guesses():
    """หัวใจของการไม่แต่งข้อมูล — ต้องพัง ไม่ใช่คืนค่ากลาง"""
    h = Hero(id="demo_x")
    with pytest.raises(ValueError, match="ไม่เดาค่าให้"):
        h.u("engage")


def test_db_completeness_and_todo():
    db = HeroDB(heroes=[_demo("demo_a"), Hero(id="demo_b"), Hero(id="demo_c")])
    cs = db.completeness()
    assert cs == {"total": 3, "complete": 1, "incomplete": 2, "fraction": pytest.approx(1 / 3)}
    todo = db.todo(priority=["demo_c", "demo_b"])
    assert [h.id for h in todo] == ["demo_c", "demo_b"]


def test_db_round_trip(tmp_path):
    db = HeroDB(patch="1.63", heroes=[_demo("demo_a"), Hero(id="demo_b")])
    p = tmp_path / "h.yaml"
    db.save(p)
    back = HeroDB.load(p)
    assert back.patch == "1.63"
    assert back.require("demo_a").complete
    assert not back.require("demo_b").complete


# -------------------------------------------------------------- composition


def test_refuses_to_score_incomplete_heroes():
    """ต้องปฏิเสธ ไม่ใช่เดาค่าแล้วให้คะแนนที่ดูน่าเชื่อ"""
    team = [_demo(f"demo_{i}") for i in range(4)] + [Hero(id="demo_empty")]
    with pytest.raises(IncompleteDataError, match="attribute ยังไม่ครบ"):
        analyze(team)


def test_error_names_the_missing_hero_and_fields():
    team = [_demo(f"demo_{i}") for i in range(4)] + [Hero(id="demo_empty")]
    with pytest.raises(IncompleteDataError) as e:
        analyze(team)
    assert "demo_empty" in str(e.value)
    assert "lane_roles" in str(e.value)


def test_team_must_have_five():
    with pytest.raises(ValueError, match="ต้องมี 5"):
        analyze([_demo("demo_a")])


def test_full_role_coverage_scores_100():
    team = [_demo(f"demo_{r.value}", lane_roles=[r]) for r in LaneRole]
    rep = analyze(team)
    assert rep.value("role_balance") == 100.0


def test_missing_lane_is_reported():
    team = [_demo(f"demo_{i}", lane_roles=[LaneRole.DS]) for i in range(5)]
    rep = analyze(team)
    assert rep.value("role_balance") < 50
    assert "ขาด" in rep.dimensions["role_balance"].detail


def test_flexible_heroes_are_assigned_to_fill_gaps():
    """ฮีโร่ที่เล่นได้หลายเลนต้องถูกจัดไปเลนที่ขาด

    การนับแบบง่ายจะพลาดกรณีนี้ จึงต้องใช้การจับคู่แบบ matching
    """
    team = [
        _demo("demo_1", lane_roles=[LaneRole.DS, LaneRole.JUNGLE]),
        _demo("demo_2", lane_roles=[LaneRole.DS, LaneRole.MID]),
        _demo("demo_3", lane_roles=[LaneRole.DS, LaneRole.DRAGON]),
        _demo("demo_4", lane_roles=[LaneRole.DS, LaneRole.SUPPORT]),
        _demo("demo_5", lane_roles=[LaneRole.DS]),
    ]
    assert analyze(team).value("role_balance") == 100.0


def test_all_physical_damage_scores_zero_mix():
    team = [_demo(f"demo_{i}", damage={"type": DamageType.PHYSICAL}) for i in range(5)]
    assert analyze(team).value("damage_mix") == 0.0


def test_balanced_damage_scores_high():
    team = [
        _demo("demo_1", damage={"type": DamageType.PHYSICAL}),
        _demo("demo_2", damage={"type": DamageType.PHYSICAL}),
        _demo("demo_3", damage={"type": DamageType.PHYSICAL}),
        _demo("demo_4", damage={"type": DamageType.MAGICAL}),
        _demo("demo_5", damage={"type": DamageType.MAGICAL}),
    ]
    assert analyze(team).value("damage_mix") > 75


def test_one_strong_engage_beats_five_mediocre():
    """มิติที่ 'มีหนึ่งคนก็พอ' ต้องไม่ใช้ค่าเฉลี่ย"""
    one_star = [_demo("demo_star", utility={"engage": 95})] + [
        _demo(f"demo_{i}", utility={"engage": 10}) for i in range(4)
    ]
    all_mid = [_demo(f"demo_{i}", utility={"engage": 40}) for i in range(5)]
    assert analyze(one_star).value("engage") > analyze(all_mid).value("engage")


def test_waveclear_is_dragged_down_by_weakest():
    """มิติที่ 'จุดอ่อนที่สุดกำหนด' ต้องไม่ใช้ค่าเฉลี่ยล้วน"""
    even = [_demo(f"demo_{i}", utility={"waveclear": 60}) for i in range(5)]
    uneven = [_demo("demo_bad", utility={"waveclear": 0})] + [
        _demo(f"demo_{i}", utility={"waveclear": 75}) for i in range(4)
    ]
    assert analyze(uneven).value("waveclear") < analyze(even).value("waveclear")


def test_cc_saturates():
    """CC สะสมได้แต่ผลตอบแทนลดลง คนที่ห้าต้องเพิ่มน้อยกว่าคนที่สอง"""
    def cc(n: int) -> float:
        team = [_demo(f"demo_{i}", utility={"cc_hard": 80 if i < n else 0}) for i in range(5)]
        return analyze(team).value("crowd_control")

    gain_2nd = cc(2) - cc(1)
    gain_5th = cc(5) - cc(4)
    assert gain_5th < gain_2nd


def test_power_curve_reflects_scaling():
    team = [_demo(f"demo_{i}", scaling={"early": 80, "mid": 50, "late": 20}) for i in range(5)]
    pc = analyze(team).power_curve
    assert pc["early"] == 80 and pc["late"] == 20


def test_gaps_and_strengths_are_flagged():
    team = [_demo(f"demo_{i}", utility={"peel": 0, "objective": 95}) for i in range(5)]
    rep = analyze(team)
    assert "Peel" in rep.gaps
    assert "Objective" in rep.strengths


def test_compare_identifies_advantage_phase():
    early = [_demo(f"demo_{i}", scaling={"early": 90, "mid": 50, "late": 20}) for i in range(5)]
    late = [_demo(f"demo_{i}", scaling={"early": 20, "mid": 50, "late": 90}) for i in range(5)]
    text = compare(analyze(early), analyze(late))
    assert "early" in text
    assert "จบเกมให้เร็ว" in text


def test_report_is_printable():
    text = analyze([_demo(f"demo_{i}") for i in range(5)]).report()
    assert "Composition" in text
    assert "Power curve" in text


# ------------------------------------------------------- ฟังก์ชันรวมค่า


def test_top_weighted_prefers_the_best():
    assert _top_weighted([100, 0, 0, 0, 0]) > _top_weighted([40, 40, 40, 40, 40])


def test_saturating_sum_is_monotonic_and_bounded():
    prev = -1.0
    for n in range(6):
        v = _saturating_sum([80] * n, 180.0)
        assert v >= prev
        assert 0 <= v <= 100
        prev = v


# ------------------------------------------------------------- hero classes


PORTAL_SAMPLE = """
<section begin="Included Assasin" />
<gallery mode=packed>
File:Airi.jpg |link=Airi|[[Airi]]
File:Zata.jpg |link=Zata|[[Zata]]
</gallery>
<section begin="included Mage" />
<gallery mode=packed>
File:Zata.jpg |link=Zata|[[Zata]]
File:Marja.jpg |link=Marja|[[Marja]]
</gallery>
<section begin="All Champions" />
<gallery mode=packed>
File:Airi.jpg |link=Airi|[[Airi]]
File:Zata.jpg |link=Zata|[[Zata]]
File:Marja.jpg |link=Marja|[[Marja]]
File:Riktor.jpg |link=Riktor|[[Riktor]]
</gallery>
<section begin="Removed" />
<gallery mode=packed>
File:Batman.jpg |link=Batman|[[Batman]]
</gallery>
"""


def test_all_champions_gallery_does_not_leak_into_last_class():
    """บั๊กจริง: การนับด้วย <big> ทำให้ Tank ได้ฮีโร่ 132 จาก 133 ตัว"""
    info, removed = parse_hero_classes(PORTAL_SAMPLE)
    assert info["riktor"]["hero_class"] == [], "riktor อยู่แค่ใน All Champions"
    assert info["marja"]["hero_class"] == [HeroClass.MAGE]


def test_dual_class_hero_gets_both():
    info, _ = parse_hero_classes(PORTAL_SAMPLE)
    assert set(info["zata"]["hero_class"]) == {HeroClass.ASSASSIN, HeroClass.MAGE}


def test_removed_heroes_are_separated():
    info, removed = parse_hero_classes(PORTAL_SAMPLE)
    assert "batman" in removed
    assert "batman" not in info


def test_alias_resolves_disambiguation_and_long_names():
    info = {
        "max_(arena_of_valor_hero)": {"name_en": "Max", "hero_class": []},
        "ming_shiyin": {"name_en": "Ming Shiyin", "hero_class": []},
        "lu_bu": {"name_en": "Lu Bu", "hero_class": []},
    }
    idx = build_alias_index(info)
    assert resolve("max", idx) == "max_(arena_of_valor_hero)"
    assert resolve("ming", idx) == "ming_shiyin"
    assert resolve("lubu", idx) == "lu_bu"


def test_ambiguous_alias_is_dropped_not_guessed():
    """ชื่อพ้องที่ชี้ไปสองตัวต้องถูกทิ้ง ดีกว่าจับคู่ผิดเงียบ ๆ"""
    info = {
        "ming_shiyin": {"name_en": "Ming Shiyin", "hero_class": []},
        "ming_zhao": {"name_en": "Ming Zhao", "hero_class": []},
    }
    idx = build_alias_index(info)
    assert resolve("ming", idx) is None
