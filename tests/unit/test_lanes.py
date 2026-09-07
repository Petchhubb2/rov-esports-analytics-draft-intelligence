"""matchup แยกตามเลน — และตัวจับว่าสมมติฐาน "ช่อง = เลน" ยังจริงอยู่ไหม

การแยกเลนทั้งหมดตั้งอยู่บนข้อสังเกตเดียว: ช่อง t1h1..t1h5 ของ Liquipedia
เรียงตาม roster ของทีม ไม่ใช่ลำดับการเลือก ถ้าข้อนี้ผิดเมื่อไร
ตัวเลข context=LANE ทั้งหมดจะผิดตามแบบเงียบ ๆ

เทสต์ในไฟล์นี้จึงมีสองชั้น
  1. ชั้นตรรกะ — ใช้ข้อมูลปลอมที่คุมได้ ตรวจว่าจับคู่ถูกช่อง นับชนะถูกฝั่ง
  2. ชั้นข้อมูลจริง — ถ้ามี cache อยู่ ตรวจว่าสัดส่วนคลาสยังกระจุกตามเลน
     ชั้นนี้ข้ามเองถ้าไม่มี cache เพื่อให้ CI ที่ไม่มีข้อมูลยังรันได้
"""

from __future__ import annotations

import pytest
from rov.domain.enums import LaneRole
from rov.draft.importer.parser import GameDraft, SeriesDraft
from rov.draft.lanes import (
    SLOT_LANES,
    compute_lane_matchups,
    lane_usage,
    main_lane,
    slot_evidence,
)


def _game(blue: list[str], red: list[str], winner: str) -> GameDraft:
    return GameDraft(
        game_index=1,
        blue_team="B",
        red_team="R",
        winner_team=winner,
        blue_picks=blue,
        red_picks=red,
        blue_bans=[],
        red_bans=[],
    )


def _series(games: list[GameDraft]) -> list[SeriesDraft]:
    return [SeriesDraft(team1="B", team2="R", best_of=1, date=None, games=games)]


BLUE = ["b_ds", "b_jgl", "b_mid", "b_adl", "b_sup"]
RED = ["r_ds", "r_jgl", "r_mid", "r_adl", "r_sup"]


# ------------------------------------------------------------------ ตรรกะ


def test_slot_order_is_the_documented_lane_order():
    assert SLOT_LANES == (
        LaneRole.DS,
        LaneRole.JUNGLE,
        LaneRole.MID,
        LaneRole.DRAGON,
        LaneRole.SUPPORT,
    )


def test_pairs_only_heroes_in_the_same_slot():
    mu = compute_lane_matchups(_series([_game(BLUE, RED, "B")]))
    # ช่องเดียวกันเท่านั้นที่ถูกจับคู่
    assert (LaneRole.DS, "b_ds", "r_ds") in mu
    assert (LaneRole.DRAGON, "b_adl", "r_adl") in mu
    # ข้ามเลนต้องไม่มี — นี่คือทั้งหมดที่ผู้ใช้ขอ
    assert (LaneRole.DS, "b_ds", "r_adl") not in mu
    assert (LaneRole.DRAGON, "b_adl", "r_jgl") not in mu
    assert len(mu) == 2 * len(SLOT_LANES)


def test_wins_are_counted_for_the_right_side():
    mu = compute_lane_matchups(_series([_game(BLUE, RED, "B")]))
    win = mu[(LaneRole.MID, "b_mid", "r_mid")]
    lose = mu[(LaneRole.MID, "r_mid", "b_mid")]
    assert (win.games, win.wins) == (1, 1)
    assert (lose.games, lose.wins) == (1, 0)
    assert lose.losses == 1


def test_incomplete_games_are_skipped():
    """ช่องขาดแล้ว parser เลื่อนช่องชิดกัน เลนจะเพี้ยน ต้องตัดทิ้ง"""
    short = _game(BLUE[:4], RED, "B")
    no_winner = _game(BLUE, RED, None)
    assert compute_lane_matchups(_series([short, no_winner])) == {}


def test_lane_usage_counts_each_slot():
    usage = lane_usage(_series([_game(BLUE, RED, "B")] * 3))
    assert usage["b_adl"][LaneRole.DRAGON] == 3
    assert usage["b_adl"][LaneRole.MID] == 0
    assert main_lane(usage["b_sup"]) == (LaneRole.SUPPORT, 1.0)


def test_main_lane_reports_the_share_for_flex_heroes():
    """ตัว flex ต้องไม่ถูกยัดให้เลนเดียว ต้องบอกสัดส่วนตามจริง"""
    games = [_game(["flex", "b_jgl", "b_mid", "b_adl", "b_sup"], RED, "B")] * 3
    games += [_game(["b_ds", "flex", "b_mid", "b_adl", "b_sup"], RED, "B")]
    usage = lane_usage(_series(games))
    lane, share = main_lane(usage["flex"])
    assert lane is LaneRole.DS
    assert share == pytest.approx(0.75)
    assert usage["flex"][LaneRole.JUNGLE] == 1


def test_main_lane_of_hero_never_seen_is_none():
    from collections import Counter

    assert main_lane(Counter()) is None


def test_counter_score_shrinks_toward_zero_with_few_games():
    mu = compute_lane_matchups(_series([_game(BLUE, RED, "B")] * 3))
    m = mu[(LaneRole.MID, "b_mid", "r_mid")]
    assert m.raw_win_rate == 1.0
    # ชนะ 3 จาก 3 แต่ยังต้องได้คะแนนน้อย เพราะข้อมูลไม่พอ
    assert 0 < m.counter_score(0.5) < 5.0


# -------------------------------------------------------------- ข้อมูลจริง


def _real_series():
    try:
        from rov.cli.main import _regions
    except Exception:
        return None
    try:
        regions = _regions()
    except Exception:
        return None
    series = [s for r in regions for s in r.series]
    return series or None


def test_slot_hypothesis_still_holds_on_real_data():
    """ถ้า Liquipedia เปลี่ยนวิธีเก็บ เทสต์นี้จะพังก่อนที่ตัวเลขจะหลอกเรา"""
    series = _real_series()
    if series is None:
        pytest.skip("ไม่มี cache Liquipedia ในเครื่องนี้")

    from rov.draft.heroes import HeroDB

    db = HeroDB.load("configs/draft/heroes.yaml")
    classes = {h.id: [c.value for c in h.hero_class] for h in db.heroes if h.hero_class}

    ev = slot_evidence(series, classes)
    share = ev["class_share_by_lane"]
    assert ev["teams"] > 500, "ข้อมูลน้อยเกินกว่าจะสรุป"
    # ตัวชี้ขาด — ช่อง ADL ต้องเป็น marksman ท่วมท้น
    assert share["dragon"]["marksman"] > 0.85, share["dragon"]
    assert share["mid"]["mage"] > 0.50, share["mid"]
    # ช่องอื่นต้องไม่ใช่ marksman
    for lane in ("ds", "jungle", "support"):
        assert share[lane].get("marksman", 0.0) < 0.20, (lane, share[lane])
    assert ev["passes"] is True
