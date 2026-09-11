"""จังหวะของคอมพ์ — ทีมนี้ต้องรีบจบ ยื้อเกม หรือดูจังหวะอีกฝั่ง

PHASE B · Q7

**ทำไมไฟล์นี้ถึงเกิดทีหลัง**

ตรรกะนี้ถูกเขียนไว้ที่เดียวคือ `winCondition()` ใน `draft_board.tpl.html`
ซึ่งแปลว่าหน้าเว็บสรุปเชิงกลยุทธ์ให้ผู้ใช้ แต่ CLI ทำไม่ได้ และไม่มีอะไร
เทียบสองฝั่งได้เลยเพราะฝั่ง Python ไม่มีของให้เทียบ
(docs/17-intelligence-audit.md §9 ข้อ 15 — ระบุว่าอันตรายที่สุดใน 18 จุด)

ไฟล์นี้ย้ายตรรกะมาฝั่ง Python โดย **ใช้ JS เป็นต้นแบบของพฤติกรรมปัจจุบัน**
ตามที่ PHASE B กำหนด: ห้ามเปลี่ยน behavior ก่อนมี parity test

**ที่มาของเกณฑ์ ±0.12**

ยังไม่มี — นี่คือค่าที่ถูกเลือกตอนเขียนหน้าเว็บโดยไม่ได้บันทึกเหตุผลไว้
และยังไม่เคยถูกตรวจกับผลแพ้ชนะ จึงกำกับไว้เป็น `verified = False`
และ `tempo_source` บอกตรง ๆ ว่ามาจากไหน

สิ่งที่ต้องทำเพื่อยืนยัน: ดูว่าคอมพ์ที่ระบบจัดเป็น EARLY ชนะเกมสั้นจริงไหม
บนชุด evaluation ที่แยกไว้ (docs/20 §11) — เป็นงานของ PHASE I
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# เกณฑ์ตัดสิน — ยกมาจาก winCondition() ในหน้าเว็บตรง ๆ
# ⚠️ ยังไม่ได้ตรวจกับผลแพ้ชนะ ห้ามขยับจนกว่าจะมี benchmark
TEMPO_EARLY = -0.12
TEMPO_LATE = 0.12

# เกณฑ์นี้ยืนยันแล้วหรือยัง — ใช้บังคับให้ UI ต้องขึ้นคำเตือน
TEMPO_THRESHOLD_VERIFIED = False


class WinCondition(StrEnum):
    """แผนที่คอมพ์นี้ถูกบังคับให้เล่น"""

    EARLY = "early"
    LATE = "late"
    FLEXIBLE = "flexible"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TempoProfile:
    """จังหวะเฉลี่ยของคอมพ์ พร้อมบอกว่าคิดจากกี่ตัว"""

    avg: float
    used: int
    total: int

    @property
    def coverage(self) -> float:
        return self.used / self.total if self.total else 0.0


def team_tempo(
    picks: list[str], tempo_by_hero: dict[str, float | None]
) -> TempoProfile | None:
    """จังหวะเฉลี่ยของทีม — คืน None เมื่อไม่มีตัวไหนมีข้อมูลเลย

    เฉลี่ยเฉพาะตัวที่มีข้อมูล ไม่ใช่เฉลี่ยทั้งห้าโดยนับตัวที่ไม่รู้เป็น 0
    เพราะ 0 แปลว่า "กลาง ๆ" ซึ่งเป็นการอ้างสิ่งที่ยังไม่รู้

    ตรงกับ compTempo() ในหน้าเว็บทุกประการ
    """
    vals = [
        t for p in picks
        if (t := tempo_by_hero.get(p)) is not None
    ]
    if not vals:
        return None
    return TempoProfile(avg=sum(vals) / len(vals), used=len(vals), total=len(picks))


def classify(tempo: TempoProfile | None) -> WinCondition:
    """จัดคอมพ์เป็นสายต้นเกม ท้ายเกม หรือกลาง ๆ

    `UNKNOWN` เมื่อไม่มีข้อมูล — ไม่ใช่ `FLEXIBLE`
    "ไม่รู้ว่าคอมพ์นี้ต้องเล่นยังไง" กับ "คอมพ์นี้เล่นได้หลายแบบ" ต่างกันมาก
    """
    if tempo is None:
        return WinCondition.UNKNOWN
    if tempo.avg <= TEMPO_EARLY:
        return WinCondition.EARLY
    if tempo.avg >= TEMPO_LATE:
        return WinCondition.LATE
    return WinCondition.FLEXIBLE


# ข้อความอธิบายแต่ละแผน — ตรงกับหน้าเว็บ เพื่อให้ CLI กับเว็บพูดเหมือนกัน
PLAN_TEXT: dict[WinCondition, str] = {
    WinCondition.EARLY: (
        "คอมพ์สายต้นเกม — ต้องเปลี่ยนความได้เปรียบเป็นของให้ทันภายในนาทีที่ 8 "
        "กดดันตั้งแต่ 4:00 ที่ป้องกันป่าหาย ถ้าปล่อยให้ยืดไปถึง Battle จะเสียเปรียบ"
    ),
    WinCondition.LATE: (
        "คอมพ์สายท้ายเกม — ยอมเสียพื้นที่ได้แต่ห้ามเสียคนฟรี "
        "เป้าหมายคือพาเกมไปถึง 15:00 ที่ God Slayer เกิด แล้วค่อยหาปะทะ"
    ),
    WinCondition.FLEXIBLE: (
        "คอมพ์กลาง ๆ — ไม่ได้ถูกบังคับให้รีบจบหรือยืดเกม "
        "ให้ดูจังหวะของอีกฝั่งแล้วเล่นสวนทางกับเขา"
    ),
    WinCondition.UNKNOWN: "ยังไม่ได้เลือกตัว จึงยังบอกจังหวะของทีมไม่ได้",
}


def describe(tempo: TempoProfile | None) -> str:
    """ข้อความที่ผู้ใช้อ่าน พร้อมคำเตือนเรื่องเกณฑ์ที่ยังไม่ยืนยัน"""
    wc = classify(tempo)
    text = PLAN_TEXT[wc]
    if wc is WinCondition.UNKNOWN:
        return text
    parts = [text]
    if tempo is not None:
        parts.append(f"(tempo {tempo.avg:+.3f} จาก {tempo.used}/{tempo.total} ตัวที่มีข้อมูล)")
    if not TEMPO_THRESHOLD_VERIFIED:
        parts.append("เกณฑ์ ±0.12 ยังไม่ได้ตรวจกับผลแพ้ชนะ")
    return " ".join(parts)
