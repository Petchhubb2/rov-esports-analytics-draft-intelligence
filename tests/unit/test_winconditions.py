"""ทดสอบ winconditions.py และ parity กับ winCondition() ในหน้าเว็บ — Q7

ก่อน PHASE B ตรรกะนี้มีอยู่**ที่เดียวคือ JavaScript** ทำให้ CLI กับเว็บ
สรุปกลยุทธ์ต่างกันโดยไม่มีอะไรฟ้อง (docs/17 §9 ข้อ 15)

ไฟล์นี้บังคับสองอย่าง
    1. Python ให้ผลเหมือน JS ทุกกรณี (parity)
    2. เกณฑ์ที่ยังไม่ยืนยัน ต้องบอกผู้ใช้เสมอ
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from rov.draft.winconditions import (
    TEMPO_EARLY,
    TEMPO_LATE,
    TEMPO_THRESHOLD_VERIFIED,
    TempoProfile,
    WinCondition,
    classify,
    describe,
    team_tempo,
)

TPL = Path("apps/web/draft_board.tpl.html")


@pytest.fixture(scope="module")
def tpl() -> str:
    return TPL.read_text(encoding="utf-8")


# ------------------------------------------------------------- parity กับ JS


def test_js_thresholds_match_python(tpl):
    """เกณฑ์ ±0.12 ต้องตรงกันสองฝั่ง

    ถ้าฝั่งไหนขยับ ผู้ใช้จะเห็น "คอมพ์สายต้นเกม" บนเว็บ
    แต่ CLI บอก "คอมพ์กลาง ๆ" สำหรับคอมพ์เดียวกัน
    """
    block = re.search(r"function winCondition\(tempo, team\) \{(.*?)\n\}", tpl, re.S)
    assert block, "หา winCondition ใน template ไม่เจอ"
    body = block.group(1)

    early = re.search(r"if \(a <= (-?[\d.]+)\)", body)
    late = re.search(r"if \(a >= (-?[\d.]+)\)", body)
    assert early, "หาเกณฑ์สายต้นเกมใน JS ไม่เจอ"
    assert late, "หาเกณฑ์สายท้ายเกมใน JS ไม่เจอ"
    assert float(early.group(1)) == TEMPO_EARLY
    assert float(late.group(1)) == TEMPO_LATE


def js_classify(avg: float | None) -> WinCondition:
    """จำลอง winCondition() ฝั่ง JS ด้วยโครงสร้างเดียวกันทุกบรรทัด"""
    if avg is None:
        return WinCondition.UNKNOWN
    if avg <= TEMPO_EARLY:
        return WinCondition.EARLY
    if avg >= TEMPO_LATE:
        return WinCondition.LATE
    return WinCondition.FLEXIBLE


@pytest.mark.parametrize(
    "avg",
    [-1.0, -0.5, -0.13, -0.12, -0.119, -0.05, 0.0, 0.05, 0.119, 0.12, 0.13, 0.5, 1.0],
)
def test_classify_matches_js_on_every_boundary(avg):
    """ทดสอบตรงขอบเขตด้วย — จุดที่ <= กับ < ต่างกันคือจุดที่มักเพี้ยน"""
    tempo = TempoProfile(avg=avg, used=5, total=5)
    assert classify(tempo) is js_classify(avg)


def test_boundary_values_are_inclusive():
    """-0.12 พอดีต้องเป็น EARLY และ +0.12 พอดีต้องเป็น LATE

    JS ใช้ <= และ >= ถ้าฝั่ง Python เผลอใช้ < กับ > จะต่างกันเฉพาะค่าขอบ
    ซึ่งเป็นบั๊กที่หายากมากถ้าไม่ทดสอบตรงนี้
    """
    assert classify(TempoProfile(TEMPO_EARLY, 5, 5)) is WinCondition.EARLY
    assert classify(TempoProfile(TEMPO_LATE, 5, 5)) is WinCondition.LATE


# --------------------------------------------------------------- team_tempo


def test_team_tempo_averages_only_heroes_with_data():
    """เฉลี่ยเฉพาะตัวที่มีข้อมูล — ไม่นับตัวที่ไม่รู้เป็น 0

    ถ้านับเป็น 0 คอมพ์ที่มีข้อมูลแค่ตัวเดียวจะถูกลากเข้าหากลางเสมอ
    ซึ่งเป็นการอ้างสิ่งที่ยังไม่รู้
    """
    t = team_tempo(["a", "b", "c"], {"a": -0.4, "b": None, "c": -0.2})
    assert t is not None
    assert t.avg == pytest.approx(-0.3)
    assert (t.used, t.total) == (2, 3)


def test_team_tempo_is_none_when_nothing_is_known():
    assert team_tempo(["a", "b"], {"a": None, "b": None}) is None
    assert team_tempo([], {}) is None


def test_coverage_reports_how_much_was_actually_used():
    t = team_tempo(["a", "b", "c", "d"], {"a": 0.1, "b": 0.2})
    assert t.coverage == pytest.approx(0.5)


def test_team_tempo_matches_js_comp_tempo(tpl):
    """compTempo() ฝั่ง JS กรอง null แล้วเฉลี่ยเฉพาะที่เหลือ — ต้องเหมือนกัน"""
    block = re.search(r"function compTempo\(team\) \{(.*?)\n\}", tpl, re.S)
    assert block
    body = block.group(1)
    assert ".filter(v => v != null)" in body, "JS เลิกกรอง null แล้ว"
    assert "vals.reduce((a, b) => a + b, 0) / vals.length" in body, "JS เปลี่ยนวิธีเฉลี่ย"


# ---------------------------------------------------- UNKNOWN ไม่ใช่ FLEXIBLE


def test_no_data_is_unknown_not_flexible():
    """"ไม่รู้ว่าต้องเล่นยังไง" กับ "เล่นได้หลายแบบ" เป็นคนละเรื่อง"""
    assert classify(None) is WinCondition.UNKNOWN
    assert classify(None) is not WinCondition.FLEXIBLE


def test_unknown_says_so_plainly():
    assert "ยังไม่ได้เลือกตัว" in describe(None)


# ------------------------------------------- เกณฑ์ที่ยังไม่ยืนยันต้องบอกผู้ใช้


def test_threshold_is_still_marked_unverified():
    """กันไม่ให้ใครติ๊กว่ายืนยันแล้วโดยยังไม่ได้วัด

    ปลดได้ต่อเมื่อทดสอบบนชุด evaluation ใน PHASE I แล้วเท่านั้น
    """
    assert TEMPO_THRESHOLD_VERIFIED is False


def test_description_warns_while_threshold_is_unverified():
    if TEMPO_THRESHOLD_VERIFIED:
        pytest.skip("ยืนยันแล้ว ไม่ต้องเตือน")
    for avg in (-0.5, 0.0, 0.5):
        text = describe(TempoProfile(avg, 5, 5))
        assert "ยังไม่ได้ตรวจ" in text, f"ไม่มีคำเตือนที่ avg={avg}"


def test_description_shows_how_many_heroes_it_used():
    text = describe(TempoProfile(-0.4, 3, 5))
    assert "3/5" in text, "ต้องบอกว่าคิดจากกี่ตัว ไม่ใช่สรุปลอย ๆ"


@pytest.mark.parametrize("wc", list(WinCondition))
def test_every_win_condition_has_text(wc):
    from rov.draft.winconditions import PLAN_TEXT

    assert PLAN_TEXT[wc].strip()
