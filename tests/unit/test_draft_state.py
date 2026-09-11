"""ทดสอบ Draft state machine และคำแนะนำ"""

from __future__ import annotations

import pytest
from rov.domain.enums import DraftAction, Team
from rov.draft.importer.parser import GameDraft, SeriesDraft
from rov.draft.meta import Region, pool
from rov.draft.recommend import recommend, weights_for
from rov.draft.state import DraftFormat, DraftState, IllegalMove

FORMAT_FILE = "configs/draft/format.yaml"
POOL = {f"h{i}" for i in range(1, 41)}


@pytest.fixture(scope="module")
def fmt() -> DraftFormat:
    return DraftFormat.load(FORMAT_FILE)


def new_state(fmt: DraftFormat, **kw) -> DraftState:
    return DraftState(fmt=fmt, pool=set(POOL), **kw)


def skip_bans(st: DraftState, keep: str) -> None:
    """ข้ามเฟสแบนไปให้ถึงเฟส pick โดยไม่แบนตัวที่กำลังทดสอบ

    เดิมใช้ `st.legal_moves().pop()` ซึ่งหยิบสมาชิก**ตามลำดับ hash ของ set**
    ซึ่งเปลี่ยนทุก process ตาม PYTHONHASHSEED บางรอบมันเผลอแบนตัวที่
    เทสต์กำลังจะทดสอบพอดี แล้วเทสต์ fail แบบสุ่ม ๆ ประมาณ 1 ใน 6 รอบ

    พบตอน PHASE B — ไม่ได้เกิดจากการแก้ engine แต่มีมาก่อนหน้านั้น
    เทสต์ที่ผ่านบ้างไม่ผ่าบ้าง แย่กว่าไม่มีเทสต์ เพราะมันสอนให้คนเลิกเชื่อผลเทสต์
    """
    while st.current is not None and st.current.action is DraftAction.BAN:
        choices = sorted(st.legal_moves() - {keep})
        assert choices, "ไม่เหลือตัวให้แบน"
        st.apply(choices[0])


# ------------------------------------------------------------------ format


def test_format_matches_confirmed_counts(fmt):
    """ยืนยันจากข้อมูลจริง 861 เกม: แบน 4 เลือก 5 ต่อทีม"""
    assert fmt.bans_per_team == 4
    assert fmt.picks_per_team == 5
    assert fmt.total_turns == 18


def test_format_is_marked_unverified(fmt):
    """ลำดับ ban/pick ยังหา rulebook ไม่พบ ต้องไม่อ้างว่ายืนยันแล้ว"""
    assert fmt.verified is False


def test_format_rejects_mismatched_sequence():
    with pytest.raises(ValueError, match="bans_per_team"):
        DraftFormat.model_validate(
            {
                "id": "bad",
                "bans_per_team": 2,
                "picks_per_team": 1,
                "sequence": [
                    {"phase": 1, "team": "blue", "action": "BAN"},
                    {"phase": 1, "team": "red", "action": "BAN"},
                    {"phase": 1, "team": "blue", "action": "PICK"},
                    {"phase": 1, "team": "red", "action": "PICK"},
                ],
            }
        )


def test_both_teams_get_equal_turns(fmt):
    for action in (DraftAction.BAN, DraftAction.PICK):
        blue = sum(1 for t in fmt.sequence if t.team == "blue" and t.action is action)
        red = sum(1 for t in fmt.sequence if t.team == "red" and t.action is action)
        assert blue == red


# ------------------------------------------------------------------- state


def test_turn_order_follows_format(fmt):
    st = new_state(fmt)
    assert st.current == fmt.sequence[0]
    st.apply("h1")
    assert st.current == fmt.sequence[1]


def test_hero_cannot_be_taken_twice(fmt):
    st = new_state(fmt)
    st.apply("h1")
    with pytest.raises(IllegalMove, match="ถูกแบนไปแล้ว"):
        st.apply("h1")


def test_unknown_hero_is_rejected(fmt):
    st = new_state(fmt)
    with pytest.raises(IllegalMove, match="ไม่รู้จัก"):
        st.apply("ไม่มีตัวนี้")


def test_undo_restores_previous_turn(fmt):
    st = new_state(fmt)
    st.apply("h1")
    st.apply("h2")
    mv = st.undo()
    assert mv.hero_id == "h2"
    assert st.turn_index == 1
    assert "h2" in st.legal_moves()


def test_undo_on_empty_returns_none(fmt):
    assert new_state(fmt).undo() is None


def test_reset_clears_everything(fmt):
    st = new_state(fmt)
    for h in ("h1", "h2", "h3"):
        st.apply(h)
    st.reset()
    assert st.turn_index == 0
    assert st.all_taken == set()


def test_draft_completes_after_all_turns(fmt):
    st = new_state(fmt)
    for i in range(1, fmt.total_turns + 1):
        st.apply(f"h{i}")
    assert st.complete
    assert st.current is None
    assert st.legal_moves() == set()
    with pytest.raises(IllegalMove, match="จบแล้ว"):
        st.apply("h30")


def test_picks_and_bans_are_separated(fmt):
    st = new_state(fmt)
    for i in range(1, fmt.total_turns + 1):
        st.apply(f"h{i}")
    assert len(st.picks(Team.BLUE)) == fmt.picks_per_team
    assert len(st.picks(Team.RED)) == fmt.picks_per_team
    assert len(st.bans(Team.BLUE)) == fmt.bans_per_team
    assert len(st.bans(Team.RED)) == fmt.bans_per_team
    assert not set(st.picks(Team.BLUE)) & set(st.picks(Team.RED))


# --------------------------------------------------- Global Ban-Pick


def test_own_previous_picks_are_locked(fmt):
    """กติกาที่ยืนยันแล้ว: ห้ามใช้ตัวที่ทีมตัวเองเคยเลือกในซีรีส์"""
    st = new_state(fmt, series_used={Team.BLUE: {"h5"}})
    skip_bans(st, keep="h5")
    assert st.current.team_enum is Team.BLUE
    assert "h5" not in st.legal_moves()
    with pytest.raises(IllegalMove, match="Global Ban-Pick"):
        st.apply("h5")


def test_opponent_previous_picks_are_still_allowed(fmt):
    """soft fearless — หยิบตัวที่ฝ่ายตรงข้ามเคยใช้ได้"""
    st = new_state(fmt, series_used={Team.RED: {"h5"}})
    skip_bans(st, keep="h5")
    assert st.current.team_enum is Team.BLUE
    assert "h5" in st.legal_moves()


def test_bans_are_not_restricted_by_series(fmt):
    """applies_to_bans = false — แบนตัวที่ตัวเองเคยใช้ได้"""
    st = new_state(fmt, series_used={Team.BLUE: {"h5"}})
    assert st.current.action is DraftAction.BAN
    assert st.current.team_enum is Team.BLUE
    assert "h5" in st.legal_moves()


def test_final_game_resets_the_rule(fmt):
    """Bo7 เกมที่ 7 กลับเป็น Normal Ban-Pick"""
    st = new_state(fmt, series_used={Team.BLUE: {"h5"}}, is_final_game=True)
    skip_bans(st, keep="h5")
    assert "h5" in st.legal_moves()


def test_both_teams_scope(fmt):
    f2 = fmt.model_copy(deep=True)
    f2.global_ban_pick.scope = "both_teams"
    st = DraftState(fmt=f2, pool=set(POOL), series_used={Team.RED: {"h5"}})
    skip_bans(st, keep="h5")
    assert "h5" not in st.legal_moves()


# ------------------------------------------------------------------ output


def test_board_and_history_render(fmt):
    st = new_state(fmt, blue_name="SLX", red_name="DCG")
    st.apply("h1")
    st.apply("h2")
    assert "SLX" in st.board()
    assert "h1" in st.board()
    assert "h1" in st.history()
    assert "SLX" in st.prompt()


def test_empty_history_message(fmt):
    assert "ยังไม่มี" in new_state(fmt).history()


# ------------------------------------------------------------- recommend


def _pooled():
    """ข้อมูลสมมติ — a1 ชนะบ่อย a9 แพ้บ่อย"""
    games = []
    for i in range(1, 61):
        blue = ["a1", "a2", "a3", "a4", "a5"]
        red = ["a6", "a7", "a8", "a9", "a10"]
        games.append(
            GameDraft(
                game_index=i, blue_team="A", red_team="B", winner_team="A",
                blue_picks=blue, red_picks=red,
                blue_bans=[], red_bans=[], length_sec=900.0,
            )
        )
    s = SeriesDraft(team1="A", team2="B", best_of=1, date=None, games=games)
    return pool([Region("X", "x", [s])])


def test_recommendation_prefers_higher_winrate(fmt):
    p = _pooled()
    st = DraftState(fmt=fmt, pool=set(p.stats.heroes))
    sugs = recommend(st, p, limit=10, min_games=5)
    ids = [s.hero_id for s in sugs]
    assert ids, "ต้องมีคำแนะนำ"
    # ฮีโร่ฝั่งที่ชนะตลอดต้องมาก่อนฝั่งที่แพ้ตลอด
    assert ids.index("a1") < ids.index("a9")


def test_recommendation_only_suggests_legal_heroes(fmt):
    p = _pooled()
    st = DraftState(fmt=fmt, pool=set(p.stats.heroes))
    st.apply("a1")
    assert all(s.hero_id != "a1" for s in recommend(st, p, limit=20, min_games=1))


def test_recommendation_respects_min_games(fmt):
    p = _pooled()
    st = DraftState(fmt=fmt, pool=set(p.stats.heroes) | {"ไม่เคยเล่น"})
    assert all(s.hero_id != "ไม่เคยเล่น" for s in recommend(st, p, min_games=5))


def test_components_explain_themselves(fmt):
    """ทุก component ต้องบอกที่มาได้ ไม่ว่าจะเป็นตัวหลักหรือตัวที่เพิ่มใน PHASE B

    เดิมเทสต์นี้ล็อกว่าต้องมีสี่ตัวพอดี ซึ่งทำให้เพิ่ม factor ใหม่ไม่ได้เลย
    ตอนนี้เปลี่ยนเป็นล็อกสองอย่างที่สำคัญกว่า:
      1. สี่ตัวหลักต้องมีเสมอ (ไม่หายไปเพราะ refactor)
      2. ทุกตัวที่มี ต้องอธิบายตัวเองได้ (ไม่มีคะแนนลึกลับ)
    """
    p = _pooled()
    st = DraftState(fmt=fmt, pool=set(p.stats.heroes))
    s = recommend(st, p, limit=1, min_games=5)[0]
    assert {"meta", "winrate", "counter", "synergy"} <= set(s.components)
    for c in s.components.values():
        assert 0 <= c.scaled <= 100
        assert c.detail, f"{c.key} ไม่บอกที่มา — ห้ามมีคะแนนที่ตรวจสอบไม่ได้"


def test_no_component_appears_without_a_weight_entry(fmt):
    """กันไม่ให้มี component ที่ไม่มีน้ำหนักรองรับ

    base = Σ w_all.get(k, 0) * scaled[k] ใช้ .get() จึงไม่ระเบิดถ้าลืมใส่น้ำหนัก
    แต่จะกลายเป็น factor ที่ไม่มีวันถูกใช้และไม่มีใครรู้ เทสต์นี้จับตรงนั้น
    """
    from rov.draft.recommend import EXTRA_WEIGHTS, weights_for

    p = _pooled()
    st = DraftState(fmt=fmt, pool=set(p.stats.heroes))
    s = recommend(st, p, limit=1, min_games=5)[0]
    known = set(weights_for(0, 0)) | set(EXTRA_WEIGHTS)
    assert set(s.components) <= known, (
        f"component ที่ไม่มีน้ำหนักรองรับ: {set(s.components) - known}"
    )


def test_counter_is_neutral_before_enemy_picks(fmt):
    p = _pooled()
    st = DraftState(fmt=fmt, pool=set(p.stats.heroes))
    s = recommend(st, p, limit=1, min_games=5)[0]
    assert "ยังไม่ได้เลือก" in s.components["counter"].detail


def test_no_recommendation_when_draft_complete(fmt):
    p = _pooled()
    st = DraftState(fmt=fmt, pool=set(p.stats.heroes))
    for h in sorted(p.stats.heroes):
        if st.complete:
            break
        st.apply(h)
    assert recommend(st, p) == []


# --------------------------------------------- น้ำหนักที่ขยับตามบริบท


def test_weights_always_sum_to_one():
    for ne in range(6):
        for na in range(5):
            w = weights_for(ne, na)
            assert abs(sum(w.values()) - 1.0) < 1e-9, (ne, na, w)


def test_with_no_picks_the_averages_carry_the_score():
    """ยังไม่มีใครเปิดตัว ก็ไม่มีบริบท ต้องพึ่ง meta กับ win rate เป็นหลัก"""
    w = weights_for(0, 0)
    assert w["meta"] + w["winrate"] > 0.85
    assert w["counter"] < 0.10 and w["synergy"] < 0.10


def test_weight_moves_to_counter_as_the_enemy_opens_up():
    """นี่คือหัวใจของการแก้ — เปิดตัวมากขึ้น ต้องเชื่อบริบทมากกว่าค่าเฉลี่ยรวม"""
    seq = [weights_for(n, 0)["counter"] for n in range(6)]
    assert seq == sorted(seq), "counter ต้องไม่ลดลงเมื่อศัตรูเปิดตัวเพิ่ม"
    assert seq[-1] > seq[0] * 3, "ตอนเปิดครบต้องหนักกว่าตอนยังไม่เปิดหลายเท่า"
    # ไต่แบบอิ่มตัว ตัวแรกต้องให้ข้อมูลมากกว่าตัวที่ห้า
    assert seq[1] - seq[0] > seq[5] - seq[4]


def test_weight_moves_to_synergy_as_our_team_fills_up():
    seq = [weights_for(0, n)["synergy"] for n in range(5)]
    assert seq == sorted(seq)
    assert seq[-1] > seq[0] * 3


def test_winrate_loses_ground_once_the_draft_is_known():
    """เคสที่ผู้ใช้ติดมา — วินเรทสูงต้องไม่ครองอันดับตลอดไป"""
    early = weights_for(0, 0)
    late = weights_for(5, 4)
    assert late["winrate"] < early["winrate"] / 2
    assert late["counter"] > late["winrate"]


# ------------------------------------- ตำแหน่งที่อีกฝั่งยังไม่เปิด


LU = {
    "b_ds": {"ds": 100},
    "b_jgl": {"jungle": 100},
    "b_mid": {"mid": 100},
    "b_adl": {"dragon": 100},
    "b_sup": {"support": 100},
    "flex": {"ds": 60, "jungle": 40},
    "half": {"ds": 50, "mid": 50},
}
LN = ["ds", "jungle", "mid", "dragon", "support"]


def test_a_filled_lane_is_no_longer_needed():
    from rov.draft.recommend import needed_lanes

    assert needed_lanes([], LU, LN) == set(LN)
    assert needed_lanes(["b_mid"], LU, LN) == {"ds", "jungle", "dragon", "support"}
    assert needed_lanes(["b_mid", "b_sup", "b_adl"], LU, LN) == {"ds", "jungle"}


def test_a_flex_hero_only_closes_the_lane_it_mostly_plays():
    """ตัวที่เล่นสองเลนครึ่ง ๆ ไม่ควรไปปิดเลนที่มันอาจไม่ได้ลง"""
    from rov.draft.recommend import needed_lanes

    # flex ลง ds 60% ถือว่าปิด ds
    assert "ds" not in needed_lanes(["flex"], LU, LN)
    assert "jungle" in needed_lanes(["flex"], LU, LN)
    # half ลงคนละ 50% ไม่ถึงเกณฑ์ ไม่ปิดเลนไหนเลย
    assert needed_lanes(["half"], LU, LN) == set(LN)


def test_role_fit_zero_when_the_lane_is_already_taken():
    """หัวใจของการแก้ — เขามีเมจแล้ว การแบนเมจอีกตัวไม่ได้ตัดอะไร"""
    from rov.draft.recommend import needed_lanes, role_fit

    need = needed_lanes(["b_mid", "b_sup", "b_adl"], LU, LN)   # เหลือ ds กับ jungle
    assert role_fit("b_mid", need, LU, LN) == 0.0
    assert role_fit("b_sup", need, LU, LN) == 0.0
    assert role_fit("b_ds", need, LU, LN) == 1.0
    assert role_fit("b_jgl", need, LU, LN) == 1.0


def test_role_fit_is_neutral_when_we_know_nothing():
    from rov.draft.recommend import role_fit

    # ไม่มีข้อมูลเลนของฮีโร่ตัวนี้
    assert role_fit("unknown", {"ds"}, LU, LN) == 1.0
    # ต้นดราฟต์ ยังต้องการทุกเลน
    assert role_fit("b_mid", set(LN), LU, LN) == 1.0
    assert role_fit("b_mid", set(), LU, LN) == 1.0


def test_role_fit_is_partial_for_flex_heroes():
    from rov.draft.recommend import role_fit

    # flex ลง ds 60 jungle 40 ถ้าเหลือแต่ jungle ก็ได้ 0.4
    assert role_fit("flex", {"jungle"}, LU, LN) == pytest.approx(0.4)
