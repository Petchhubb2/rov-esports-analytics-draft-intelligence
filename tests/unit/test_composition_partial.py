"""ทดสอบ partial_dimensions() — Q1 ของ PHASE B

`analyze()` บังคับ 5 ตัวพอดี แต่ระหว่างดราฟต์เรามี 0-4 ตัว
`partial_dimensions()` จึงเกิดขึ้นเพื่อใช้ฟังก์ชันรวมชุดเดิมกับทีมที่ยังไม่ครบ

**เทสต์ที่สำคัญที่สุดในไฟล์นี้คือ `test_matches_analyze_on_a_full_team`**
ถ้าสองทางให้ค่าไม่ตรงกัน คะแนนระหว่างดราฟต์จะคนละมาตรกับคะแนนตอนดราฟต์จบ
แล้วผู้ใช้จะเห็นตัวเลขกระโดดโดยไม่มีเหตุผล
"""

from __future__ import annotations

import pytest
from rov.draft.composition import _PARTIAL_DIMS, analyze, partial_dimensions
from rov.draft.heroes import REQUIRED_UTILITY, Damage, Hero, Scaling, Utility


def hero(hid: str, **u) -> Hero:
    """ฮีโร่ที่กรอกครบ ค่า utility ที่ไม่ระบุเป็น 50"""
    vals = {k: 50 for k in REQUIRED_UTILITY}
    vals.update(u)
    return Hero(
        id=hid,
        lane_roles=[u.pop("lane", "mid")] if "lane" in u else ["mid"],
        range="long",
        damage=Damage(type="magical"),
        scaling=Scaling(early=50, mid=50, late=50),
        utility=Utility(**vals),
        filled_kind="human",
        filled_by="test",
    )


def team5() -> list[Hero]:
    return [
        Hero(
            id=f"h{i}",
            lane_roles=[ln],
            range="melee" if i % 2 else "long",
            damage=Damage(type="physical" if i % 2 else "magical"),
            scaling=Scaling(early=40 + i, mid=50 + i, late=60 + i),
            utility=Utility(**{k: (10 + 7 * i + 3 * j) % 101
                               for j, k in enumerate(REQUIRED_UTILITY)}),
            filled_kind="human",
            filled_by="test",
        )
        for i, ln in enumerate(["ds", "jungle", "mid", "dragon", "support"])
    ]


# ------------------------------------------------------- ความสอดคล้องกับ analyze


def test_matches_analyze_on_a_full_team():
    """ทีมครบ 5 ตัว สองทางต้องให้ค่าตรงกันทุกมิติที่มีร่วมกัน

    นี่คือสัญญาว่าคะแนนระหว่างดราฟต์กับตอนดราฟต์จบใช้มาตรเดียวกัน
    """
    team = team5()
    rep = analyze(team)
    partial = partial_dimensions(team)
    assert partial is not None
    for key, dim in rep.dimensions.items():
        if key in partial:
            assert partial[key] == pytest.approx(dim.value, abs=1e-9), key


def test_covers_every_utility_backed_dimension_analyze_has():
    """มิติที่ analyze() คิดจาก utility ต้องมีใน partial ครบ

    ยกเว้น role_balance กับ damage_mix ที่จัดการแยก
    ถ้าวันหนึ่ง analyze() เพิ่มมิติแล้วลืมเพิ่มที่นี่ เทสต์นี้จะจับได้
    """
    rep = analyze(team5())
    from_utility = set(rep.dimensions) - {"role_balance", "damage_mix"}
    assert from_utility <= set(_PARTIAL_DIMS)


# ----------------------------------------------------------- ทีมที่ยังไม่ครบ


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
def test_works_with_any_team_size(n):
    out = partial_dimensions(team5()[:n])
    assert out is not None
    assert set(out) >= set(_PARTIAL_DIMS)


def test_empty_team_is_all_zero_not_unknown():
    """ทีมที่ยังไม่มีใครเลย ไม่มี frontline จริง ๆ — เป็น 0 ไม่ใช่ 'ไม่รู้'"""
    out = partial_dimensions([])
    assert out is not None
    assert all(v == 0.0 for v in out.values())


def test_values_stay_in_range():
    for n in range(6):
        out = partial_dimensions(team5()[:n])
        assert all(0.0 <= v <= 100.0 for v in out.values())


# ------------------------------------------------- ไม่เดาเมื่อข้อมูลไม่ครบ


def test_returns_none_when_any_hero_is_incomplete():
    """หลักเดียวกับ Hero.u() — ยอมบอกว่าไม่รู้ ดีกว่าคืนค่ากลาง"""
    team = team5()
    team.append(Hero(id="empty"))
    assert partial_dimensions(team) is None


def test_one_incomplete_hero_poisons_the_whole_team():
    assert partial_dimensions([Hero(id="empty")]) is None


# --------------------------------------------------- ฟังก์ชันรวมยังถูกต้อง


def test_adding_a_tank_raises_frontline():
    base = [hero("mage", frontline=10, waveclear=80)]
    before = partial_dimensions(base)
    after = partial_dimensions([*base, hero("tank", frontline=90, waveclear=20)])
    assert after["frontline"] > before["frontline"]


def test_adding_a_bad_waveclearer_drags_waveclear_down():
    """waveclear ใช้ min ถ่วง — ตัวที่แย่ที่สุดมีผลจริง"""
    base = [hero("a", waveclear=80), hero("b", waveclear=80)]
    before = partial_dimensions(base)
    after = partial_dimensions([*base, hero("c", waveclear=10)])
    assert after["waveclear"] < before["waveclear"]


def test_cc_saturates_rather_than_adding_up():
    one = partial_dimensions([hero("a", cc_hard=90)])["crowd_control"]
    two = partial_dimensions([hero("a", cc_hard=90), hero("b", cc_hard=90)])[
        "crowd_control"
    ]
    three = partial_dimensions(
        [hero("a", cc_hard=90), hero("b", cc_hard=90), hero("c", cc_hard=90)]
    )["crowd_control"]
    assert one < two < three < 100.0
    assert (three - two) < (two - one), "ผลตอบแทนต้องลดลง ไม่ใช่บวกเป็นเส้นตรง"


def test_one_strong_engage_counts_more_than_many_mediocre():
    strong = partial_dimensions([hero("a", engage=95), hero("b", engage=10)])
    spread = partial_dimensions([hero("a", engage=50), hero("b", engage=50)])
    assert strong["engage"] > spread["engage"]
