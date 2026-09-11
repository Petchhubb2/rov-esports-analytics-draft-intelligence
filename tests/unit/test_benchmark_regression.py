"""Benchmark regression — PHASE M0.5 ข้อ 7

**ต่างจาก `test_recommend_regression.py` อย่างไร**

    test_recommend_regression   ล็อก "คำแนะนำของแต่ละตา" ว่าต้องเหมือนเดิม
    ไฟล์นี้                      ล็อก "ข้อสรุปของ benchmark" ว่าต้องไม่พลิก

อันแรกจับการเปลี่ยนแปลงเล็กที่สุด อันนี้จับการเปลี่ยนแปลงที่มีความหมาย —
ถ้าวันหนึ่ง engine ชนะ baseline ขึ้นมา เรา**อยากรู้** ไม่ใช่ปล่อยผ่าน
และถ้ามันแย่ลงกว่าเดิม เราต้องรู้ทันทีเช่นกัน

ใช้ข้อมูลจาก `tests/fixtures/recommend_regression.json` ซึ่งฝังสถิติจริง
จึงรันได้โดยไม่ต้องมี `data/cache/`
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rov.draft.recommend import recommend
from rov.draft.state import DraftFormat, DraftState
from rov.eval.baselines import (
    EngineRanker,
    PresenceBaseline,
    RoleAwarePresenceBaseline,
    TurnContext,
    WinRateBaseline,
)
from rov.eval.draftbench import (
    dict_to_lane_matchups,
    dict_to_pooled,
    draft_move_order,
    load_fixture,
)
from rov.eval.rankmetrics import RankStats, wilson_interval

FIXTURE = Path("tests/fixtures/recommend_regression.json")


@pytest.fixture(scope="module")
def replayed():
    """เดินดราฟต์ใน fixture แล้วเก็บอันดับของตัวที่เลือกจริงของทุก ranker

    fixture นี้ไม่ได้แยก train/eval (มันคือ snapshot ของ engine)
    จึงใช้ตรวจ **ความสัมพันธ์ระหว่าง ranker** ได้ แต่ห้ามอ้างเป็นผล benchmark
    ตัวเลข benchmark จริงอยู่ใน docs/22 ซึ่งวัดบน split ที่แยกตามเวลา
    """
    if not FIXTURE.exists():
        pytest.skip("ยังไม่มี fixture")
    fx = load_fixture(FIXTURE)
    pooled, lu = dict_to_pooled(fx["pool"])
    lmu = dict_to_lane_matchups(fx["pool"])
    fmt = DraftFormat.load()

    rankers = [
        EngineRanker(recommend),
        PresenceBaseline(),
        WinRateBaseline(),
        RoleAwarePresenceBaseline(),
    ]
    stats = {r.name: RankStats(name=r.name) for r in rankers}
    by_action = {"BAN": {r.name: RankStats(name=r.name) for r in rankers},
                 "PICK": {r.name: RankStats(name=r.name) for r in rankers}}

    for d in fx["drafts"]:
        st = DraftState(fmt=fmt, pool=set(pooled.stats.heroes))
        for actual in draft_move_order(d, fmt.sequence):
            turn = st.current
            if turn is None:
                break
            ctx = TurnContext(
                state=st, pooled=pooled, lane_usage=lu, lanes=fx["lanes"],
                lane_matchups=lmu, hero_db=None, min_games=5,
            )
            if actual in set(ctx.candidates()):
                action = str(turn.action)
                for r in rankers:
                    lst = r.rank(ctx)
                    rank = lst.index(actual) + 1 if actual in lst else None
                    stats[r.name].add(rank)
                    by_action[action][r.name].add(rank)
            if actual not in st.legal_moves():
                break
            st.apply(actual)
    return stats, by_action


# ----------------------------------------------- ความสัมพันธ์ที่ต้องคงอยู่


def test_every_ranker_is_scored_on_the_same_turns(replayed):
    stats, _ = replayed
    ns = {s.n_turns for s in stats.values()}
    assert len(ns) == 1, f"ตัวหารไม่ตรงกัน: {ns}"


def test_sample_is_big_enough_to_say_anything(replayed):
    stats, _ = replayed
    n = next(iter(stats.values())).n_ranked
    assert n >= 100, f"ตัวอย่างเล็กเกินไป ({n}) — ข้อสรุปด้านล่างเชื่อไม่ได้"


def test_win_rate_baseline_is_the_weakest(replayed):
    """Baseline B ต้องแย่ที่สุดเสมอ

    ไม่ใช่เพราะ win rate ไร้ค่า แต่เพราะ win rate ระดับอาชีพเกาะ 50%
    จนเรียงลำดับแล้วแทบเป็นการสุ่ม ถ้าวันหนึ่ง B ขึ้นมาชนะใคร
    แปลว่ามีอะไรผิดปกติกับข้อมูลหรือกับ ranker ตัวนั้น
    """
    stats, _ = replayed
    b = stats["B · win rate"].top1_acc or 0.0
    others = [
        (n, s.top1_acc or 0.0) for n, s in stats.items() if n != "B · win rate"
    ]
    for name, acc in others:
        assert b <= acc, f"B ชนะ {name} ({b:.3f} > {acc:.3f}) — ผิดปกติ"


def test_engine_still_beats_baselines_on_picks(replayed):
    """ข้อค้นพบหลักของ PHASE M0.5 — engine เก่งกว่า baseline ตอน pick

    ถ้าข้อนี้พัง แปลว่าการแก้ engine ทำให้จุดแข็งเดียวที่วัดได้หายไป
    ซึ่งต้องหยุดแล้วดูก่อนว่าตั้งใจหรือเปล่า
    """
    _, by_action = replayed
    picks = by_action["PICK"]
    if next(iter(picks.values())).n_ranked < 30:
        pytest.skip("ตา pick ใน fixture น้อยเกินไป")
    engine = picks["current engine"].top1_acc or 0.0
    presence = picks["A · presence"].top1_acc or 0.0
    assert engine >= presence, (
        f"engine แพ้ baseline A ตอน pick แล้ว ({engine:.3f} < {presence:.3f}) "
        "— จุดแข็งเดียวที่วัดได้หายไป"
    )


def test_engine_still_loses_to_presence_on_bans(replayed):
    """จุดอ่อนที่รู้อยู่ — ล็อกไว้เพื่อให้รู้ทันทีเมื่อมันถูกแก้

    ถ้าเทสต์นี้ fail แปลว่า ban ดีขึ้นแล้ว ซึ่งเป็น**ข่าวดี** —
    ให้ลบเทสต์นี้ทิ้งพร้อมอัปเดต docs/22 ไม่ใช่แก้โค้ดให้กลับไปแย่เหมือนเดิม
    """
    _, by_action = replayed
    bans = by_action["BAN"]
    if next(iter(bans.values())).n_ranked < 30:
        pytest.skip("ตา ban ใน fixture น้อยเกินไป")
    engine = bans["current engine"].top1_acc or 0.0
    presence = bans["A · presence"].top1_acc or 0.0
    assert engine <= presence, (
        f"engine ชนะ baseline ตอน ban แล้ว ({engine:.3f} > {presence:.3f}) — "
        "ข่าวดี ให้ลบเทสต์นี้และอัปเดต docs/22-benchmark-foundation.md"
    )


def test_ranking_covers_every_candidate(replayed):
    """coverage ต้องเป็น 1.0 — ทุก ranker ต้องจัดอันดับให้ครบทุกตัว

    ถ้าต่ำกว่านั้น แปลว่า ranker ตัดตัวทิ้งเงียบ ๆ ซึ่งทำให้ mean rank
    ดูดีเกินจริง เพราะตัวที่มันตัดทิ้งคือตัวที่มันจัดอันดับได้แย่
    """
    stats, _ = replayed
    for name, s in stats.items():
        assert s.coverage == pytest.approx(1.0), f"{name} coverage = {s.coverage}"


# ------------------------------------------------------- ตัวชี้วัดคำนวณถูก


def test_mrr_is_bounded_and_consistent_with_top1(replayed):
    stats, _ = replayed
    for name, s in stats.items():
        assert 0.0 <= (s.mrr or 0.0) <= 1.0, name
        # ทุกตาที่ top-1 ถูก ให้ 1/1 = 1 ดังนั้น MRR >= top1_acc เสมอ
        assert (s.mrr or 0.0) >= (s.top1_acc or 0.0) - 1e-9, name


def test_mean_rank_is_at_least_one(replayed):
    stats, _ = replayed
    for name, s in stats.items():
        assert (s.mean_rank or 1.0) >= 1.0, name


def test_top_k_is_monotone(replayed):
    stats, _ = replayed
    for name, s in stats.items():
        assert (s.top1_acc or 0) <= (s.top3_acc or 0) <= (s.top5_acc or 0), name


def test_wilson_interval_contains_the_point_estimate():
    lo, hi = wilson_interval(27, 476)
    assert lo < 27 / 476 < hi
    assert 0.0 <= lo and hi <= 1.0


def test_wilson_interval_is_wider_for_small_samples():
    narrow = wilson_interval(50, 1000)
    wide = wilson_interval(5, 100)
    assert (wide[1] - wide[0]) > (narrow[1] - narrow[0])
