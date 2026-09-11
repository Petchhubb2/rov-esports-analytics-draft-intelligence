"""Regression test ของ Draft Engine — ล็อกพฤติกรรมก่อน PHASE B

`tests/fixtures/recommend_regression.json` เก็บคำแนะนำของ 216 ตา
จากดราฟต์จริง 12 เกม พร้อมข้อมูลสถิติที่ใช้คำนวณครบในไฟล์เดียว
จึงรันได้โดยไม่ต้องมี data/cache/ (ซึ่งอยู่ใน .gitignore)

**หน้าที่ของไฟล์นี้คือทำให้ PHASE B พิสูจน์คำสัญญาได้**
"ทุก factor ใหม่เริ่มที่น้ำหนัก 0 และ weight=0 ต้องไม่เปลี่ยนอันดับ"

ถ้าเทสต์นี้ fail มีสองความเป็นไปได้เท่านั้น
    1. เปลี่ยน behavior โดยไม่ตั้งใจ -> ต้องแก้โค้ด
    2. ตั้งใจเปลี่ยน และตรวจแล้วว่าถูก -> ต้องสร้าง fixture ใหม่พร้อมอธิบายใน commit

**ห้ามสร้าง fixture ใหม่เพื่อให้เทสต์ผ่านโดยไม่ดูว่าอะไรเปลี่ยน**
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rov.draft.recommend import recommend
from rov.draft.state import DraftFormat
from rov.eval.draftbench import compare, dict_to_pooled, load_fixture, replay_all

FIXTURE = Path("tests/fixtures/recommend_regression.json")


@pytest.fixture(scope="module")
def fx() -> dict:
    if not FIXTURE.exists():
        pytest.skip("ยังไม่มี fixture — รัน scripts/make_recommend_fixture.py --write")
    return load_fixture(FIXTURE)


@pytest.fixture(scope="module")
def fmt() -> DraftFormat:
    return DraftFormat.load()


@pytest.fixture(scope="module")
def replayed(fx, fmt) -> dict:
    return replay_all(fx, fmt, recommend, top_k=fx["top_k"])


# ------------------------------------------------------- fixture สมเหตุสมผล


def test_fixture_has_real_drafts(fx):
    assert len(fx["drafts"]) >= 10
    for d in fx["drafts"]:
        assert len(d["blue_picks"]) == 5 and len(d["red_picks"]) == 5
        assert len(d["blue_bans"]) == 4 and len(d["red_bans"]) == 4
        assert d["winner"] in (d["blue_team"], d["red_team"])


def test_fixture_pool_round_trips(fx):
    """สร้าง PooledStats กลับจาก fixture แล้วต้องได้ค่าเดิม"""
    pooled, lu = dict_to_pooled(fx["pool"])
    assert pooled.stats.total_games == fx["pool"]["total_games"]
    assert len(pooled.stats.heroes) == len(fx["pool"]["heroes"])
    assert len(pooled.matchups) == len(fx["pool"]["matchups"])
    assert len(pooled.synergies) == len(fx["pool"]["synergies"])
    assert len(lu) == len(fx["pool"]["lane_usage"])


def test_fixture_covers_every_phase(fx):
    """ต้องมีตาจากทุกเฟส ไม่ใช่แค่ตาแรก ๆ"""
    turns = {int(k.split("#")[1]) for k in fx["expected"]}
    assert 0 in turns, "ต้องมีตาแรก (ban แรก ยังไม่มีใครเปิดตัว)"
    assert any(t in turns for t in range(4, 10)), "ต้องมีตาในเฟส pick 1"
    assert any(t in turns for t in range(10, 14)), "ต้องมีตาในเฟส ban 2"
    assert max(turns) >= 16, "ต้องมีตาท้าย ๆ ที่ข้อมูลเปิดมาเกือบครบ"


# ------------------------------------------------------------ regression จริง


def test_recommendations_match_the_locked_snapshot(fx, replayed):
    """หัวใจของ PHASE B — คำแนะนำทุกตาต้องเหมือน snapshot เป๊ะ ๆ"""
    expected = {k: [tuple(r) for r in v] for k, v in fx["expected"].items()}
    diff = compare(expected, replayed)
    assert diff.identical, diff.report()


def test_top1_is_stable(fx, replayed):
    """แยกออกมาเป็นเทสต์ของตัวเอง เพราะอันดับ 1 คือสิ่งที่ผู้ใช้เห็นก่อน"""
    changed = [
        k
        for k, v in fx["expected"].items()
        if v and replayed.get(k) and v[0][0] != replayed[k][0][0]
    ]
    assert not changed, f"อันดับ 1 เปลี่ยนใน {len(changed)} ตา: {changed[:5]}"


# --------------------------------------------------- คุณสมบัติที่ต้องคงอยู่


def test_every_turn_produces_a_recommendation(replayed):
    empty = [k for k, v in replayed.items() if not v]
    assert not empty, f"มี {len(empty)} ตาที่ไม่มีคำแนะนำ: {empty[:5]}"


def test_recommendations_are_sorted_by_total(replayed):
    for key, rows in replayed.items():
        totals = [t for _, t in rows]
        assert totals == sorted(totals, reverse=True), key


def test_no_duplicate_heroes_within_a_turn(replayed):
    for key, rows in replayed.items():
        ids = [h for h, _ in rows]
        assert len(ids) == len(set(ids)), key


def test_scores_stay_in_range(replayed):
    """total มาจากผลรวมของ component 0-100 คูณตัวคูณ role_fit <= 1"""
    for key, rows in replayed.items():
        for hero, total in rows:
            assert 0.0 <= total <= 100.0, f"{key} {hero} = {total}"


# --------------------------------------------------------- เครื่องมือเทียบ


def test_compare_detects_a_reordering():
    before = {"a#0": [("x", 90.0), ("y", 80.0)]}
    after = {"a#0": [("y", 80.0), ("x", 90.0)]}
    d = compare(before, after)
    assert not d.identical
    assert d.top1_changed == ["a#0"]
    assert d.order_changed == ["a#0"]


def test_compare_detects_score_drift_without_reordering():
    before = {"a#0": [("x", 90.0), ("y", 80.0)]}
    after = {"a#0": [("x", 90.5), ("y", 80.0)]}
    d = compare(before, after)
    assert not d.identical
    assert d.score_changed == ["a#0"]
    assert not d.order_changed


def test_compare_accepts_float_noise():
    before = {"a#0": [("x", 90.0)]}
    after = {"a#0": [("x", 90.0 + 1e-12)]}
    assert compare(before, after).identical
