"""แยกโจทย์ ban ออกจาก pick — PHASE M0.75 · STEP 8

**คุณสมบัติที่สำคัญที่สุดในไฟล์นี้**

    เปลี่ยนบริบทของ ban ต้องไม่เปลี่ยนคะแนน pick

ถ้าคุณสมบัตินี้หลุด แปลว่าสองโจทย์ยังพันกันอยู่ และการแก้ ban ครั้งต่อไป
จะทำให้ pick เพี้ยนโดยไม่มีใครสังเกต
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rov.domain.enums import DraftAction
from rov.draft.recommend import (
    BAN_META_SHARE,
    PICK_META_SHARE,
    ban_weights_for,
    recommend,
    report,
    weights_for,
)
from rov.draft.state import DraftFormat, DraftState
from rov.eval.draftbench import (
    dict_to_lane_matchups,
    dict_to_pooled,
    draft_move_order,
    load_fixture,
)

FIXTURE = Path("tests/fixtures/recommend_regression.json")


@pytest.fixture(scope="module")
def ctx():
    if not FIXTURE.exists():
        pytest.skip("ยังไม่มี fixture")
    fx = load_fixture(FIXTURE)
    pooled, lu = dict_to_pooled(fx["pool"])
    return fx, pooled, lu, dict_to_lane_matchups(fx["pool"]), DraftFormat.load()


def rec(ctx, st, **kw):
    fx, pooled, lu, lmu, _ = ctx
    return recommend(
        st, pooled, limit=12, lane_usage=lu, lanes=fx["lanes"],
        lane_matchups=lmu, **kw
    )


def walk_to(ctx, n_moves: int) -> DraftState:
    """เดินดราฟต์จริงจาก fixture ไป n ตา"""
    fx, pooled, _lu, _lmu, fmt = ctx
    st = DraftState(fmt=fmt, pool=set(pooled.stats.heroes))
    for h in draft_move_order(fx["drafts"][0], fmt.sequence)[:n_moves]:
        if h in st.legal_moves():
            st.apply(h)
    return st


def first_turn_of(ctx, action: DraftAction, phase: int) -> DraftState:
    fx, pooled, _lu, _lmu, fmt = ctx
    for i in range(len(fmt.sequence)):
        st = walk_to(ctx, i)
        t = st.current
        if t is not None and t.action is action and t.phase == phase:
            return st
    pytest.skip(f"ไม่มีตา {action} เฟส {phase}")


# ───────────────────────────────────────────────── โปรไฟล์น้ำหนักแยกกัน


def test_ban_and_pick_use_different_meta_shares():
    assert BAN_META_SHARE > PICK_META_SHARE, (
        "ban ต้องให้น้ำหนัก meta มากกว่า pick — meta ประมาณ P(ศัตรูได้ตัวนี้) "
        "ซึ่งเป็นตัวคูณของทุกอย่าง ดู docs/24 §1"
    )


@pytest.mark.parametrize("ne,na", [(0, 0), (1, 0), (2, 1), (3, 3), (5, 5)])
def test_ban_and_pick_weights_sum_to_the_same_total(ne, na):
    """ผลรวมต้องเท่ากัน ไม่งั้นคะแนนสองโจทย์อยู่คนละสเกลและเทียบกันไม่ได้"""
    p, b = weights_for(ne, na), ban_weights_for(ne, na)
    assert sum(p.values()) == pytest.approx(sum(b.values()), abs=1e-12)


@pytest.mark.parametrize("ne,na", [(0, 0), (1, 0), (3, 3), (5, 5)])
def test_ban_keeps_the_counter_and_synergy_ramp_untouched(ne, na):
    """การไหลตามข้อมูลที่เปิดมาใช้ได้กับทั้งสองโจทย์ จึงต้องเหมือนกันเป๊ะ"""
    p, b = weights_for(ne, na), ban_weights_for(ne, na)
    assert p["counter"] == b["counter"]
    assert p["synergy"] == b["synergy"]


@pytest.mark.parametrize("ne,na", [(0, 0), (1, 0), (3, 3), (5, 5)])
def test_ban_weights_meta_beats_winrate(ne, na):
    b = ban_weights_for(ne, na)
    assert b["meta"] > b["winrate"]


def test_pick_weights_are_untouched_by_phase_m075():
    """ค่าเดิมทุกตัว — ถ้าข้อนี้พัง แปลว่า pick behavior เปลี่ยนไปแล้ว"""
    w = weights_for(0, 0)
    assert w["meta"] == pytest.approx(0.3915, abs=1e-9)
    assert w["winrate"] == pytest.approx(0.4785, abs=1e-9)
    assert w["counter"] == pytest.approx(0.08, abs=1e-9)
    assert w["synergy"] == pytest.approx(0.05, abs=1e-9)


# ─────────────────────────────── คุณสมบัติหลัก · ban ต้องไม่กระทบ pick


def test_changing_ban_weights_never_changes_pick_scores(ctx):
    """★ คุณสมบัติหลักของ M0.75

    ดัน BAN_META_SHARE ไปสุดขั้วทั้งสองทาง แล้วคะแนนของทุกตา pick
    ต้องไม่ขยับแม้แต่หลักทศนิยมที่ 12
    """
    import rov.draft.recommend as mod

    fx, pooled, _lu, _lmu, fmt = ctx
    pick_states = []
    st = DraftState(fmt=fmt, pool=set(pooled.stats.heroes))
    for h in draft_move_order(fx["drafts"][0], fmt.sequence):
        t = st.current
        if t is None:
            break
        if t.action is DraftAction.PICK:
            pick_states.append(walk_to(ctx, len(st.moves)))
        if h not in st.legal_moves():
            break
        st.apply(h)
    assert pick_states, "ไม่มีตา pick ให้ทดสอบ"

    before = [[(s.hero_id, s.total) for s in rec(ctx, p)] for p in pick_states]
    original = mod.BAN_META_SHARE
    try:
        for extreme in (0.0, 1.0):
            mod.BAN_META_SHARE = extreme
            after = [[(s.hero_id, s.total) for s in rec(ctx, p)] for p in pick_states]
            assert after == before, (
                f"คะแนน pick เปลี่ยนเมื่อ BAN_META_SHARE = {extreme} "
                "— สองโจทย์ยังพันกันอยู่"
            )
    finally:
        mod.BAN_META_SHARE = original


def test_ban_turns_do_react_to_the_ban_profile(ctx):
    """คู่ตรงข้ามของเทสต์ข้างบน — ถ้าไม่ขยับเลย แปลว่าโปรไฟล์ไม่ได้ถูกใช้"""
    import rov.draft.recommend as mod

    st = first_turn_of(ctx, DraftAction.BAN, 1)
    before = [s.hero_id for s in rec(ctx, st)]
    original = mod.BAN_META_SHARE
    try:
        mod.BAN_META_SHARE = 0.05
        after = [s.hero_id for s in rec(ctx, st)]
    finally:
        mod.BAN_META_SHARE = original
    assert before != after, "เปลี่ยนโปรไฟล์ ban แล้วอันดับไม่ขยับ"


# ──────────────────────────────────────────────── objective ติดป้ายถูก


@pytest.mark.parametrize("phase", [1, 2])
def test_ban_turns_are_labelled_ban(ctx, phase):
    st = first_turn_of(ctx, DraftAction.BAN, phase)
    sugs = rec(ctx, st)
    assert sugs and all(s.objective == "ban" for s in sugs)


@pytest.mark.parametrize("phase", [1, 2])
def test_pick_turns_are_labelled_pick(ctx, phase):
    st = first_turn_of(ctx, DraftAction.PICK, phase)
    sugs = rec(ctx, st)
    assert sugs and all(s.objective == "pick" for s in sugs)


def test_report_explains_which_objective_it_used(ctx):
    """STEP 7 ข้อ 5 — ต้องอธิบายได้ว่าคะแนน ban ต่างจาก pick อย่างไร"""
    fx, pooled, _lu, _lmu, _fmt = ctx
    ban = first_turn_of(ctx, DraftAction.BAN, 1)
    pick = first_turn_of(ctx, DraftAction.PICK, 1)
    ban_text = report(rec(ctx, ban), ban)
    pick_text = report(rec(ctx, pick), pick)
    assert "โจทย์: แบน" in ban_text
    assert "ไม่ใช่การหาตัวที่เข้ากับทีมเรา" in ban_text
    assert "โจทย์: เลือก" in pick_text


# ──────────────────────────────── บริบทตามเฟส · ฝั่ง · ข้อมูลที่เปิดแล้ว


def test_phase1_ban_has_no_revealed_roles(ctx):
    """เฟสแบนแรก ศัตรูยังไม่เปิดตัวเลย — role_fit ต้องเป็นกลาง 1.0 ทุกตัว

    ยืนยันข้อสรุปของ docs/23 §4 ว่า role_fit ไม่ใช่สาเหตุของปัญหา
    """
    st = first_turn_of(ctx, DraftAction.BAN, 1)
    turn = st.current
    assert st.picks(turn.team_enum.opponent) == []
    for s in rec(ctx, st):
        assert s.role_fit == pytest.approx(1.0)


def test_phase2_ban_uses_partially_revealed_roles(ctx):
    """เฟสแบนที่สอง ศัตรูเปิดไปแล้ว — role_fit ต้องเริ่มแยกตัวได้"""
    st = first_turn_of(ctx, DraftAction.BAN, 2)
    turn = st.current
    assert st.picks(turn.team_enum.opponent), "เฟส 2 ศัตรูต้องเปิดตัวไปแล้ว"
    fits = {round(s.role_fit, 3) for s in rec(ctx, st)}
    assert fits, "ไม่มีผลลัพธ์"


@pytest.mark.parametrize("side", ["blue", "red"])
def test_both_sides_get_ban_recommendations(ctx, side):
    """ทั้งสองฝั่งต้องได้คำแนะนำแบน และมองจากมุมศัตรูของตัวเอง"""
    fx, pooled, _lu, _lmu, fmt = ctx
    for i in range(len(fmt.sequence)):
        st = walk_to(ctx, i)
        t = st.current
        if t is not None and t.action is DraftAction.BAN and t.team == side:
            sugs = rec(ctx, st)
            assert sugs and all(s.objective == "ban" for s in sugs)
            return
    pytest.skip(f"ไม่มีตาแบนของฝั่ง {side}")


def test_ban_pool_excludes_heroes_the_enemy_cannot_use(ctx):
    """Global Ban-Pick — ไม่เสียตาแบนกับตัวที่ศัตรูหยิบไม่ได้อยู่แล้ว"""
    from rov.domain.enums import Team

    fx, pooled, lu, lmu, fmt = ctx
    st = DraftState(
        fmt=fmt,
        pool=set(pooled.stats.heroes),
        series_used={Team.RED: {"rouie"}},
    )
    assert st.current.action is DraftAction.BAN and st.current.team == "blue"
    ids = [s.hero_id for s in rec(ctx, st)]
    assert "rouie" not in ids, "แบนตัวที่ศัตรูใช้ไม่ได้อยู่แล้ว = เสียตาเปล่า"


# ───────────────────────────────────────────── คะแนนต้องอธิบายตัวเองได้


def test_every_ban_component_explains_itself(ctx):
    st = first_turn_of(ctx, DraftAction.BAN, 1)
    for s in rec(ctx, st):
        for c in s.components.values():
            assert c.detail.strip(), f"{s.hero_id}.{c.key} ไม่บอกที่มา"


def test_phase1_ban_counter_and_synergy_say_they_have_no_data(ctx):
    """เฟส 1 ยังไม่มีใครเปิดตัว — ต้องบอกตรง ๆ ไม่ใช่เงียบแล้วให้ 50"""
    st = first_turn_of(ctx, DraftAction.BAN, 1)
    s = rec(ctx, st)[0]
    assert "ยังไม่ได้เลือก" in s.components["counter"].detail
    assert "ยังไม่ได้เลือก" in s.components["synergy"].detail
