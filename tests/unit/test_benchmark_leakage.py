"""พิสูจน์ว่า benchmark ไม่มี leakage — PHASE M0.5 ข้อ 5

**ทำไมต้องพิสูจน์ด้วยการทดลอง ไม่ใช่แค่อ่านโค้ด**

leakage ไม่ทำให้อะไรพัง มันแค่ทำให้คะแนนดูดีขึ้น ซึ่งเป็นทิศทางที่
ไม่มีใครอยากตรวจสอบ วิธีเดียวที่เชื่อถือได้คือสร้างสถานการณ์ที่
ถ้ามีรั่วจะเห็นชัด แล้วยืนยันว่าไม่เห็น

สองข้อที่ PHASE M0.5 สั่งให้ยืนยัน
    1. แมตช์ใน evaluation ห้ามถูกใช้สร้าง feature ก่อนเวลาของมัน
    2. แมตช์อนาคตห้ามไหลย้อนเข้ามาเป็นสถิติย้อนหลัง
"""

from __future__ import annotations

from datetime import date

import pytest
from rov.draft.importer.parser import GameDraft, SeriesDraft
from rov.draft.meta import Region, pool
from rov.draft.state import DraftFormat
from rov.eval.baselines import PresenceBaseline, default_rankers
from rov.eval.benchmark import LeakageError, compare_rankers, split_by_time

# ฮีโร่ที่โผล่เฉพาะใน eval — ถ้ามันมีสถิติตอนประเมิน แปลว่ารั่ว
FUTURE_ONLY = "ghost_from_the_future"

OLD_A = ["marja", "tachi", "lorion", "capheny", "toro"]
OLD_B = ["qi", "billow", "annette", "hayate", "ybneth"]
NEW_A = [FUTURE_ONLY, "tachi", "lorion", "capheny", "toro"]


def game(idx: int, blue_picks: list[str], red_picks: list[str]) -> GameDraft:
    return GameDraft(
        game_index=idx,
        blue_team="blue_team",
        red_team="red_team",
        winner_team="blue_team",
        blue_picks=list(blue_picks),
        red_picks=list(red_picks),
        blue_bans=["b1", "b2", "b3", "b4"],
        red_bans=["r1", "r2", "r3", "r4"],
        length_sec=900.0,
    )


def series(date_str: str, blue_picks: list[str], n: int = 3) -> SeriesDraft:
    return SeriesDraft(
        team1="blue_team",
        team2="red_team",
        best_of=n,
        date=date_str,
        games=[game(i, blue_picks, OLD_B) for i in range(1, n + 1)],
    )


@pytest.fixture
def split():
    """train = แมตช์เก่า · eval = แมตช์ใหม่ที่มีฮีโร่ซึ่งไม่เคยโผล่มาก่อน"""
    train = [series("January 10, 2026", OLD_A), series("February 10, 2026", OLD_A)]
    ev = [series("August 10, 2026", NEW_A), series("August 20, 2026", NEW_A)]
    return train, ev


# ─────────────────────────────────────────────────── 1 · อนาคตห้ามไหลย้อน


def test_future_hero_has_no_history_in_the_training_pool(split):
    """ฮีโร่ที่โผล่เฉพาะใน eval ต้องไม่มีสถิติเลยในชุดที่ใช้ประเมิน

    นี่คือการทดสอบที่ตรงที่สุด — ถ้า `pool()` เผลอรับ eval เข้าไป
    ฮีโร่ตัวนี้จะมี picks > 0 ทันที
    """
    train, ev = split
    pooled = pool([Region(key="t", label="train", series=train)])
    assert pooled.stats.get(FUTURE_ONLY).picks == 0
    assert FUTURE_ONLY not in pooled.stats.heroes or (
        pooled.stats.get(FUTURE_ONLY).presence == 0
    )


def test_pooling_train_and_eval_together_would_have_shown_the_leak(split):
    """ยืนยันว่าเทสต์ข้างบนไม่ใช่ผลบวกลวง

    ถ้ารวมสองชุดเข้าด้วยกัน ฮีโร่ตัวนั้น **ต้อง** มีสถิติ
    ถ้าข้อนี้ไม่ผ่าน แปลว่าเทสต์ข้างบนผ่านเพราะเหตุผลอื่น
    """
    train, ev = split
    both = pool([Region(key="x", label="both", series=train + ev)])
    assert both.stats.get(FUTURE_ONLY).picks > 0


def test_compare_rankers_never_sees_eval_statistics(split):
    """ระหว่างประเมิน ranker ต้องไม่เห็นฮีโร่จากอนาคตในกลุ่ม candidate เลย

    ตรวจที่ปลายทางจริง ไม่ใช่ที่ `pool()` — เพราะ `compare_rankers()`
    สร้าง pooled เองข้างใน ถ้าวันหนึ่งมีใครแก้ให้มันรับ eval เข้าไปด้วย
    เทสต์นี้จะจับได้
    """
    train, ev = split
    seen: list[str] = []

    class Spy:
        name = "spy"
        description = "บันทึกว่าเห็นอะไรบ้าง"
        limitations = "ใช้ในเทสต์เท่านั้น"

        def rank(self, ctx):
            cands = ctx.candidates()
            seen.extend(cands)
            return cands

    compare_rankers(train, ev, DraftFormat.load(), [Spy()], min_games=1)
    assert FUTURE_ONLY not in seen, "ฮีโร่จากอนาคตหลุดเข้ามาในกลุ่ม candidate"


# ─────────────────────────────────────── 2 · eval ห้ามถูกใช้สร้าง feature


def test_leakage_guard_rejects_overlapping_sets(split):
    train, ev = split
    with pytest.raises(LeakageError):
        compare_rankers(train + ev, ev, DraftFormat.load(), [PresenceBaseline()])


def test_leakage_guard_rejects_train_newer_than_eval(split):
    """train ที่ใหม่กว่า eval = engine เห็นอนาคตแล้ว แม้ซีรีส์จะไม่ซ้ำกัน"""
    train, ev = split
    with pytest.raises(LeakageError):
        compare_rankers(ev, train, DraftFormat.load(), [PresenceBaseline()])


def test_split_never_puts_the_same_series_on_both_sides():
    all_series = [
        series("January 10, 2026", OLD_A),
        series("August 10, 2026", NEW_A),
    ]
    train, ev = split_by_time(all_series, date(2026, 5, 1))
    assert len(train) + len(ev) == len(all_series)
    assert not ({id(s) for s in train} & {id(s) for s in ev})


def test_every_eval_series_is_newer_than_every_train_series(split):
    """คุณสมบัติที่ split ต้องรับประกัน ไม่ใช่แค่หวังว่าจะเป็น"""
    from rov.draft.scouting import parse_date

    train, ev = split
    newest_train = max(parse_date(s.date) for s in train)
    oldest_eval = min(parse_date(s.date) for s in ev)
    assert newest_train < oldest_eval


# ──────────────────────────────────── ความเป็นธรรมของการเทียบ ranker


def test_all_rankers_are_scored_on_exactly_the_same_turns(split):
    """ตัวหารต้องตรงกันทุก ranker

    ถ้าตัวไหนถูกนับบนตาที่น้อยกว่า มันจะได้เปรียบเพราะเหลือแต่ตาที่ง่าย
    """
    train, ev = split
    from rov.draft.recommend import recommend

    cmp_ = compare_rankers(
        train, ev, DraftFormat.load(), default_rankers(recommend), min_games=1
    )
    ns = {st.n_turns for st in cmp_.overall.values()}
    assert len(ns) == 1, f"ตัวหารไม่ตรงกัน: {ns}"
    ranked = {st.n_ranked for st in cmp_.overall.values()}
    assert len(ranked) == 1, f"จำนวนตาที่จัดอันดับได้ไม่ตรงกัน: {ranked}"
