"""หน้าต่างข้อมูลที่ยังไม่เคยถูกดู — PHASE M1.5 · GOAL 2

**ปัญหาที่โมดูลนี้กัน**

M0.75 ใช้หน้าต่าง validation และ holdout ไปแล้วทั้งคู่ ทุกครั้งที่เราดูผล
บนหน้าต่างหนึ่ง หน้าต่างนั้นก็เลิกเป็นหลักฐานอิสระ เพราะการตัดสินใจครั้งต่อไป
ของเราถูกผลนั้นชี้นำไปแล้ว แม้จะไม่ได้ตั้งใจ overfit ก็ตาม

ตอนนี้จึงเหลือหลักฐานสะอาดศูนย์ชิ้น และการปรับน้ำหนักใด ๆ จะพิสูจน์ไม่ได้

หน้าต่างสะอาดคือเกมที่แข่ง **หลัง** `CLEAN_CUTOFF` ซึ่งยังไม่มีใครดู

**กติกาที่บังคับด้วยโค้ด ไม่ใช่แค่เขียนไว้ในเอกสาร**

    ใช้ได้    วัดผล (measurement) — ดูว่าตัวเลขเป็นเท่าไร
    ใช้ไม่ได้  เลือก rule · ปรับน้ำหนัก · จูน threshold · แก้ implementation
              โดยอ้างผลจากหน้าต่างนี้

`assert_measurement_only()` มีไว้ให้เรียกก่อนใช้ข้อมูลนี้ทุกครั้ง
มันหยุดโปรแกรมไม่ได้จริงถ้าคนตั้งใจจะโกง แต่มันทำให้การโกงต้องเกิดขึ้น
อย่างจงใจและเห็นได้ในโค้ด แทนที่จะเกิดขึ้นเงียบ ๆ ด้วยความเคยชิน

**ทำไมตัดที่ 2026-09-06**

เพราะเป็นวันสุดท้ายที่มีข้อมูลตอนปิด M1 ทุกเกมก่อนหน้านั้นถูกใช้ไปแล้ว
ไม่ทางใดก็ทางหนึ่ง — เป็น train ของ benchmark, เป็น eval ที่ดูผลไปแล้ว,
หรือเป็นตัวคำนวณ `data_check` ของ counter knowledge
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from rov.draft.importer.parser import SeriesDraft
from rov.draft.scouting import parse_date

# วันสุดท้ายที่มีข้อมูลตอนปิด M1 — เกมหลังวันนี้คือหลักฐานที่ยังไม่เคยถูกดู
CLEAN_CUTOFF = date(2026, 9, 6)

# เหตุผลที่ยอมรับได้เมื่อเรียกใช้หน้าต่างสะอาด
ALLOWED_PURPOSES: frozenset[str] = frozenset({"measurement", "report"})


class CleanWindowMisuse(RuntimeError):
    """ใช้หน้าต่างสะอาดผิดวัตถุประสงค์ — จะทำให้มันเลิกสะอาดทันที"""


def assert_measurement_only(purpose: str) -> None:
    """ประกาศว่ากำลังจะใช้หน้าต่างสะอาดทำอะไร

    ต้องเรียกก่อนใช้ข้อมูลจาก `clean_series()` เสมอ
    การบังคับให้เขียนวัตถุประสงค์ออกมาเป็นตัวอักษร ทำให้การใช้ผิด
    กลายเป็นสิ่งที่ต้องพิมพ์ลงไปเอง ไม่ใช่สิ่งที่หลุดไปเพราะลืม
    """
    if purpose not in ALLOWED_PURPOSES:
        raise CleanWindowMisuse(
            f"ใช้หน้าต่างสะอาดเพื่อ {purpose!r} ไม่ได้ — "
            f"อนุญาตเฉพาะ {sorted(ALLOWED_PURPOSES)} "
            "(ดู docs/30-engine-version.md §3 · การ fit น้ำหนักบนหน้าต่างนี้ "
            "จะทำให้เราไม่เหลือหลักฐานอิสระอีกเลย)"
        )


@dataclass
class CleanWindow:
    """สถานะของหน้าต่างสะอาด ณ ตอนนี้"""

    cutoff: date = CLEAN_CUTOFF
    series: list[SeriesDraft] = field(default_factory=list)
    games: int = 0
    scheduled: int = 0          # นัดที่ลงตารางแล้วแต่ยังไม่มีข้อมูลเกม
    first_scheduled: date | None = None
    last_scheduled: date | None = None

    @property
    def ready(self) -> bool:
        """มีข้อมูลพอจะวัดอะไรได้หรือยัง"""
        return self.games > 0

    @property
    def status(self) -> str:
        if self.games == 0 and self.scheduled == 0:
            return "ว่าง และไม่มีนัดรออยู่"
        if self.games == 0:
            return f"ยังว่าง · มี {self.scheduled} นัดรอแข่ง"
        return f"มี {self.games} เกมจาก {len(self.series)} ซีรีส์"


def split_clean(
    all_series: list[SeriesDraft], cutoff: date = CLEAN_CUTOFF
) -> tuple[list[SeriesDraft], CleanWindow]:
    """แยกข้อมูลเป็น (ที่ใช้ได้ทั่วไป, หน้าต่างสะอาด)

    ซีรีส์ที่อ่านวันที่ไม่ได้ ถูกจัดเข้าฝั่ง "ใช้ได้ทั่วไป" เสมอ
    เพราะการเดาว่ามันอยู่หลัง cutoff จะทำให้หน้าต่างสะอาดปนเปื้อน
    ซึ่งเป็นความผิดพลาดที่แพงกว่าการเสียตัวอย่างไปไม่กี่ชิ้น
    """
    seen: list[SeriesDraft] = []
    clean: list[SeriesDraft] = []
    scheduled = 0
    dates: list[date] = []
    for s in all_series:
        d = parse_date(s.date)
        if d is None or d <= cutoff:
            seen.append(s)
            continue
        if s.complete_games:
            clean.append(s)
            dates.append(d)
        else:
            scheduled += 1
            dates.append(d)
    upcoming = [
        parse_date(s.date)
        for s in all_series
        if (pd := parse_date(s.date)) and pd > cutoff and not s.complete_games
    ]
    upcoming = [d for d in upcoming if d]
    return seen, CleanWindow(
        cutoff=cutoff,
        series=clean,
        games=sum(len(s.complete_games) for s in clean),
        scheduled=scheduled,
        first_scheduled=min(upcoming) if upcoming else None,
        last_scheduled=max(upcoming) if upcoming else None,
    )


def clean_series(
    all_series: list[SeriesDraft], purpose: str, cutoff: date = CLEAN_CUTOFF
) -> list[SeriesDraft]:
    """ดึงเฉพาะซีรีส์ในหน้าต่างสะอาด — ต้องบอกวัตถุประสงค์เสมอ"""
    assert_measurement_only(purpose)
    _seen, window = split_clean(all_series, cutoff)
    return window.series


def report(window: CleanWindow) -> str:
    lines = [
        "── CLEAN EVALUATION WINDOW ──",
        f"  cutoff        หลัง {window.cutoff}",
        f"  สถานะ         {window.status}",
        f"  เกมที่ใช้วัดได้  {window.games}",
    ]
    if window.scheduled:
        lines.append(
            f"  นัดที่รออยู่    {window.scheduled}"
            + (
                f" · {window.first_scheduled} ถึง {window.last_scheduled}"
                if window.first_scheduled
                else ""
            )
        )
    if not window.ready:
        lines += [
            "",
            "  ⚠️ ยังวัดอะไรไม่ได้ และนั่นคือสถานะที่ถูกต้อง",
            "     ไม่ใช่บั๊ก ไม่ใช่ข้อมูลหาย — แค่ยังไม่มีเกมใหม่เข้ามา",
            "     ห้ามถอยไปใช้หน้าต่างเดิมแทน เพราะมันถูกดูไปแล้ว",
        ]
    lines += [
        "",
        "  ใช้ได้    วัดผล · ทำรายงาน",
        "  ใช้ไม่ได้  เลือก rule · ปรับน้ำหนัก · จูน threshold",
    ]
    return "\n".join(lines)
