"""ทดสอบ benchmark harness — PHASE B · Q8

**เทสต์ที่สำคัญที่สุดคือเรื่อง leakage**

ถ้า evaluation set รั่วเข้าไปใน training คะแนนจะพุ่งขึ้นแบบไม่มีความหมาย
และไม่มีทางรู้จากตัวเลขปลายทางเลยว่าเกิดขึ้น ต้องกันตั้งแต่ต้นทาง
"""

from __future__ import annotations

from datetime import date

import pytest
from rov.draft.importer.parser import GameDraft, SeriesDraft
from rov.eval.benchmark import (
    Benchmark,
    LeakageError,
    assert_no_leakage,
    split_by_time,
)

PICKS_A = ["marja", "tachi", "lorion", "capheny", "toro"]
PICKS_B = ["qi", "billow", "annette", "hayate", "ybneth"]


def series(team1: str, team2: str, date_str: str | None, n: int = 1) -> SeriesDraft:
    games = [
        GameDraft(
            game_index=i,
            blue_team=team1,
            red_team=team2,
            winner_team=team1,
            blue_picks=list(PICKS_A),
            red_picks=list(PICKS_B),
            blue_bans=["a", "b", "c", "d"],
            red_bans=["e", "f", "g", "h"],
            length_sec=900.0,
        )
        for i in range(1, n + 1)
    ]
    return SeriesDraft(team1=team1, team2=team2, best_of=n, date=date_str, games=games)


# --------------------------------------------------------------- การแบ่ง


def test_split_puts_newer_matches_in_eval():
    old = series("a", "b", "January 5, 2026")
    new = series("c", "d", "August 5, 2026")
    train, ev = split_by_time([old, new], date(2026, 5, 1))
    assert train == [old]
    assert ev == [new]


def test_cutoff_is_inclusive_on_the_eval_side():
    on = series("a", "b", "May 1, 2026")
    train, ev = split_by_time([on], date(2026, 5, 1))
    assert ev == [on] and train == []


def test_undated_series_go_to_train_not_eval():
    """ซีรีส์ที่ไม่มีวันที่ใช้ทดสอบไม่ได้ เพราะไม่รู้ว่าอยู่ก่อนหรือหลัง cutoff

    ถ้าเผลอใส่เข้า eval จะกลายเป็นการทดสอบด้วยข้อมูลที่อาจเก่ากว่า train
    """
    undated = series("a", "b", None)
    train, ev = split_by_time([undated], date(2026, 5, 1))
    assert train == [undated] and ev == []


# --------------------------------------------------------------- leakage


def test_leakage_guard_accepts_a_clean_split():
    train = [series("a", "b", "January 5, 2026")]
    ev = [series("c", "d", "August 5, 2026")]
    assert_no_leakage(train, ev)  # ต้องไม่โยน


def test_leakage_guard_catches_the_same_series_on_both_sides():
    s = series("a", "b", "January 5, 2026")
    with pytest.raises(LeakageError, match="ซ้ำ"):
        assert_no_leakage([s], [s])


def test_leakage_guard_catches_overlapping_date_ranges():
    """train ที่ใหม่กว่า eval แปลว่า engine เห็นอนาคตแล้ว"""
    train = [series("a", "b", "August 20, 2026")]
    ev = [series("c", "d", "August 5, 2026")]
    with pytest.raises(LeakageError, match="คาบกัน"):
        assert_no_leakage(train, ev)


def test_leakage_guard_catches_a_split_that_was_never_split():
    """เคสที่พลาดง่ายที่สุด — ส่งชุดเดียวกันเข้าไปทั้งสองฝั่ง"""
    all_series = [
        series("a", "b", "January 5, 2026"),
        series("c", "d", "August 5, 2026"),
    ]
    with pytest.raises(LeakageError):
        assert_no_leakage(all_series, all_series)


# ------------------------------------------------------------- การรายงาน


def test_report_never_shows_a_percentage_without_its_denominator():
    """เปอร์เซ็นต์ลอย ๆ ตรวจย้อนไม่ได้ — ทุกค่าต้องมี n/d กำกับ"""
    bm = Benchmark(n_drafts=2, n_turns=10, n_candidates=50, scored_turns=8, top1=3)
    text = bm.report()
    assert "3/8" in text
    assert "0/50" in text or "/50" in text


def test_report_handles_an_empty_run_without_dividing_by_zero():
    text = Benchmark().report()
    assert "—" in text
    assert "ZeroDivision" not in text


def test_report_states_what_top_k_actually_measures():
    """ต้องเตือนว่า 'ตรงกับทีมอาชีพ' ไม่เท่ากับ 'ถูกต้อง'

    ถ้าไม่เตือน คนอ่านจะไล่ตัวเลขนี้ให้สูงสุดซึ่งเป็นเป้าที่ผิด
    """
    text = Benchmark(scored_turns=1).report()
    assert "ไม่ใช่ความ 'ถูกต้อง'" in text


def test_informative_separates_no_data_from_neutral():
    from rov.draft.recommend import Component
    from rov.eval.benchmark import _informative

    empty = {"x": Component("x", "X", 0.0, 50.0, "ยังไม่มีคู่ที่ถึงเกณฑ์")}
    real = {"x": Component("x", "X", 1.4, 73.0, "จาก 2/3 คู่")}
    assert _informative(empty, "x") is False
    assert _informative(real, "x") is True
    assert _informative({}, "x") is False
