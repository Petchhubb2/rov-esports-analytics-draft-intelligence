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
    # ข้ามเฟสแบนไปให้ถึงตา pick แรกของ blue
    while st.current.action is DraftAction.BAN:
        st.apply(f"z{st.turn_index}" if f"z{st.turn_index}" in st.pool else st.legal_moves().pop())
    assert st.current.team_enum is Team.BLUE
    assert "h5" not in st.legal_moves()
    with pytest.raises(IllegalMove, match="Global Ban-Pick"):
        st.apply("h5")


def test_opponent_previous_picks_are_still_allowed(fmt):
    """soft fearless — หยิบตัวที่ฝ่ายตรงข้ามเคยใช้ได้"""
    st = new_state(fmt, series_used={Team.RED: {"h5"}})
    while st.current.action is DraftAction.BAN:
        st.apply(st.legal_moves().pop())
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
    while st.current.action is DraftAction.BAN:
        st.apply(st.legal_moves().pop())
    assert "h5" in st.legal_moves()


def test_both_teams_scope(fmt):
    f2 = fmt.model_copy(deep=True)
    f2.global_ban_pick.scope = "both_teams"
    st = DraftState(fmt=f2, pool=set(POOL), series_used={Team.RED: {"h5"}})
    while st.current.action is DraftAction.BAN:
        st.apply(st.legal_moves().pop())
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
    p = _pooled()
    st = DraftState(fmt=fmt, pool=set(p.stats.heroes))
    s = recommend(st, p, limit=1, min_games=5)[0]
    assert set(s.components) == {"meta", "winrate", "counter", "synergy"}
    for c in s.components.values():
        assert 0 <= c.scaled <= 100
        assert c.detail, "ทุกองค์ประกอบต้องอธิบายที่มาได้"


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
