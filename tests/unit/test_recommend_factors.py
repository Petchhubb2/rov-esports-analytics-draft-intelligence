"""ทดสอบ factor ที่เปิดใช้ใน PHASE B — Q1-Q5

**สองสิ่งที่ไฟล์นี้ต้องพิสูจน์ และมันขัดกันเองโดยธรรมชาติ**

    1. น้ำหนัก 0 ต้องไม่เปลี่ยนอันดับเลย  (ไม่งั้นผิดสัญญาของ PHASE B)
    2. เปิดน้ำหนักแล้วต้องเปลี่ยนอันดับจริง (ไม่งั้นเป็น dead code ที่หลอกตัวเอง)

ถ้าขาดข้อ 2 เราจะมี factor ที่ดูเหมือนทำงานแต่จริง ๆ ไม่มีผล
ซึ่งเป็นสิ่งที่แย่กว่าไม่มี factor เลย เพราะมันสร้างความมั่นใจปลอม
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rov.draft.heroes import HeroDB
from rov.draft.recommend import EXTRA_WEIGHTS, recommend
from rov.draft.state import DraftFormat, DraftState
from rov.eval.draftbench import dict_to_pooled, load_fixture

FIXTURE = Path("tests/fixtures/recommend_regression.json")
HEROES = Path("configs/draft/heroes.yaml")


@pytest.fixture(scope="module")
def ctx():
    if not FIXTURE.exists():
        pytest.skip("ยังไม่มี fixture")
    fx = load_fixture(FIXTURE)
    pooled, lu = dict_to_pooled(fx["pool"])
    return fx, pooled, lu, DraftFormat.load()


@pytest.fixture(scope="module")
def db():
    if not HEROES.exists():
        pytest.skip("ยังไม่มี heroes.yaml")
    return HeroDB.load(HEROES)


# ลำดับที่เดินเพื่อเข้าสถานะกลางดราฟต์
#
# ใช้ฮีโร่ที่**กรอก attribute แล้วทุกตัว**โดยเจตนา ไม่ใช่ดราฟต์จริงจาก fixture
# เพราะตอนนี้กรอกไปแค่ 30/119 ตัว ดราฟต์จริงส่วนใหญ่จึงมีตัวที่
# ยังไม่ได้กรอกปนอยู่ ทำให้ partial_dimensions() คืน None ตามหลักที่ถูกแล้ว
#
# ถ้าผูกเทสต์ไว้กับดราฟต์จริง เทสต์จะพังเมื่อกรอกฮีโร่เพิ่ม ซึ่งเป็นการลงโทษการทำงานที่ถูก
# ความครอบคลุมจริงบนดราฟต์จริงวัดไว้ใน docs/21-phase-b-report.md แทน
_ASSESSED_ORDER = [
    "murad", "keera", "florentino", "omen",      # ban 4 ตัว
    "marja",                                      # blue pick 1
    "qi", "tachi",                                # red pick 1, 2
]


def mid_draft(ctx, n_moves: int = 7) -> DraftState:
    """เดินดราฟต์มาถึงกลางทาง ให้ทั้งสองฝั่งเปิดตัวไปแล้ว"""
    _fx, pooled, _lu, fmt = ctx
    st = DraftState(fmt=fmt, pool=set(pooled.stats.heroes))
    for h in _ASSESSED_ORDER[:n_moves]:
        if h in st.legal_moves():
            st.apply(h)
    return st


def run(ctx, db_, st, **kw):
    fx, pooled, lu, _ = ctx
    return recommend(
        st, pooled, limit=8, lane_usage=lu, lanes=fx["lanes"], hero_db=db_, **kw
    )


# ------------------------------------------------ น้ำหนักเริ่มต้นต้องเป็น 0


def test_every_phase_b_factor_starts_at_zero():
    """กันไม่ให้ใครเผลอเปิดน้ำหนักโดยไม่ผ่าน benchmark"""
    assert EXTRA_WEIGHTS, "ต้องมี factor ของ PHASE B อย่างน้อยหนึ่งตัว"
    for key, weight in EXTRA_WEIGHTS.items():
        assert weight == 0.0, f"{key} ถูกเปิดน้ำหนักแล้ว ({weight}) — ต้องผ่าน PHASE I ก่อน"


def test_passing_hero_db_does_not_change_ranking(ctx, db):
    """Q1 — เพิ่ม component ที่น้ำหนัก 0 ต้องไม่ขยับอะไรเลย"""
    st = mid_draft(ctx)
    without = run(ctx, None, st)
    with_db = run(ctx, db, st)
    assert [s.hero_id for s in without] == [s.hero_id for s in with_db]
    for a, b in zip(without, with_db, strict=True):
        assert a.total == pytest.approx(b.total, abs=1e-12)


# ----------------------------------------- แต่ต้องพิสูจน์ว่าไม่ใช่ dead code


def test_opening_the_composition_weight_changes_the_ranking(ctx, db):
    """Q1 — ถ้าเปิดน้ำหนักแล้วอันดับไม่ขยับเลย แปลว่า factor นี้ไม่ได้ต่อจริง"""
    st = mid_draft(ctx)
    base = [s.hero_id for s in run(ctx, db, st)]
    opened = [s.hero_id for s in run(ctx, db, st, extra_weights={"composition": 0.8})]
    assert base != opened, "เปิดน้ำหนักแล้วอันดับไม่เปลี่ยน — factor ไม่ได้ถูกใช้จริง"


def test_composition_component_is_actually_computed(ctx, db):
    st = mid_draft(ctx)
    sugs = run(ctx, db, st)
    withcomp = [s for s in sugs if "composition" in s.components]
    assert withcomp, "ไม่มี candidate ไหนได้ composition เลย"
    for s in withcomp:
        c = s.components["composition"]
        assert 0.0 <= c.scaled <= 100.0
        assert c.detail.strip()


# ------------------------------------------------- ไม่รู้ ต้องไม่แปลว่ากลาง ๆ


def test_heroes_without_attributes_get_no_composition_component(ctx, db):
    """ตัวที่ยังไม่กรอก attribute ต้อง **ไม่มี** component ไม่ใช่ได้ค่า 50

    ถ้าใส่ 50 ให้ ผู้ใช้จะแยกไม่ออกระหว่าง "คอมพ์กลาง ๆ" กับ "ยังไม่รู้"
    """
    st = mid_draft(ctx)
    sugs = run(ctx, db, st)
    done = {h.id for h in db.complete_heroes}
    for s in sugs:
        if s.hero_id not in done:
            assert "composition" not in s.components, s.hero_id


def test_no_composition_component_without_hero_db(ctx):
    st = mid_draft(ctx)
    for s in run(ctx, None, st):
        assert "composition" not in s.components


# ------------------------------------------------- fills_gaps / creates_gaps


def test_gaps_are_reported_both_ways(ctx, db):
    """pick ที่ดีในมิติหนึ่งมักสร้างจุดอ่อนในอีกมิติ ระบบต้องบอกทั้งสองด้าน

    (docs/06-draft-engine.md §7 — creates_gaps สำคัญพอกับ fills_gaps)
    """
    st = mid_draft(ctx)
    sugs = run(ctx, db, st)
    assert any(s.fills_gaps for s in sugs), "ไม่มี candidate ไหนเติมช่องว่างเลย"
    assert any(s.creates_gaps for s in sugs), "ไม่มี candidate ไหนสร้างจุดอ่อนเลย"


def test_gap_entries_are_meaningful(ctx, db):
    st = mid_draft(ctx)
    for s in run(ctx, db, st):
        for dim, delta in s.fills_gaps:
            assert isinstance(dim, str) and delta > 0
        for dim, delta in s.creates_gaps:
            assert isinstance(dim, str) and delta < 0


def test_a_tank_fills_frontline(ctx, db):
    """ตรวจกับฮีโร่จริง — Y'bneth ต้องยก frontline ขึ้นเมื่อทีมยังไม่มีแท็งก์"""
    if db.get("ybneth") is None or not db.require("ybneth").complete:
        pytest.skip("ybneth ยังไม่ได้กรอก attribute")
    fx, pooled, lu, fmt = ctx
    st = DraftState(fmt=fmt, pool=set(pooled.stats.heroes))
    # เดินจนถึงตา pick ของฝั่งน้ำเงิน โดยให้ทีมมีแต่ตัวบาง
    for h in ["murad", "keera", "florentino", "omen", "marja", "qi", "tachi"]:
        if h in st.legal_moves():
            st.apply(h)
    sugs = run(ctx, db, st)
    yb = next((s for s in sugs if s.hero_id == "ybneth"), None)
    if yb is None:
        pytest.skip("ybneth ไม่ติด 8 อันดับแรกในตานี้")
    assert any(dim == "frontline" and d > 0 for dim, d in yb.fills_gaps)
