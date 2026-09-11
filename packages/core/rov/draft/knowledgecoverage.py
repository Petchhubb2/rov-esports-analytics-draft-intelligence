"""ฮีโร่ตัวไหนรู้แล้ว ตัวไหนยังไม่รู้ — PHASE M1.5 · GOAL 3

**คำถามที่โมดูลนี้ตอบ**

    ระบบรู้อะไรเกี่ยวกับฮีโร่แต่ละตัวแค่ไหน · และตัวไหนควรกรอกก่อน

**หลักที่ไม่ยอมแลก**

ห้ามเติมข้อมูลเอง โมดูลนี้ **อ่านอย่างเดียว** มันนับว่าอะไรมีอยู่แล้ว
ไม่ได้เดาค่าที่หายไป ตัวที่ยังไม่รู้ต้องถูกนับเป็นไม่รู้ ไม่ใช่ถูกเติมให้ครบ

**สามชั้นความรู้ที่นับแยกกัน**

    ชั้น 1  hero_class          จาก Liquipedia · derived · 117/119
    ชั้น 2  assessment          utility 12 ช่อง + scaling + damage + lane
                                จาก hero_assessment.yaml · assistant · 30/119
    ชั้น 3  counter knowledge   threat หรือ mechanism จาก counter.md · 24/119

สามชั้นนี้ไม่ได้ซ้อนกันเป็นขั้นบันไดเสมอไป ฮีโร่บางตัวมี counter knowledge
แต่ไม่มี assessment และกลับกัน จึงต้องนับแยก ไม่ใช่ยุบเป็นคะแนนเดียว

**การจัดลำดับความสำคัญ**

ใช้สามอย่างตามที่ M1.5 กำหนด

    1. pick frequency     ถูกเลือกบ่อย = เจอบ่อย = ต้องรู้
    2. ban frequency      ถูกแบนบ่อย = ทีมอาชีพกลัว = สำคัญกว่าที่ pick บอก
    3. strategic impact   ปรากฏใน counter.md · เป็น target ของ counter ·
                          ถูกแบนมากกว่าถูกเลือก (ตัวที่ถูกแบนทิ้งเพราะอันตราย)

⚠️ ข้อ 3 คำนวณจากสิ่งที่ **มีหลักฐานรองรับ** เท่านั้น ไม่ใช่ความเห็นว่าตัวไหนแข็ง
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from rov.draft.counterknowledge import CounterBook
from rov.draft.heroes import Hero, HeroDB
from rov.draft.stats import DraftStats

Tier = Literal["A", "B", "C"]

TIER_LABEL: dict[str, str] = {
    "A": "ครบ — engine ใช้ได้เต็มที่",
    "B": "บางส่วน — ใช้ได้บางกลไก",
    "C": "ยังไม่รู้ — มีแค่ class หรือน้อยกว่า",
}


@dataclass
class HeroKnowledge:
    """สิ่งที่ระบบรู้เกี่ยวกับฮีโร่หนึ่งตัว"""

    hero_id: str
    name: str
    has_class: bool = False
    has_assessment: bool = False
    missing_fields: list[str] = field(default_factory=list)
    has_threat: bool = False
    has_mechanism: bool = False
    is_counter_target: bool = False
    is_counter_answer: bool = False

    picks: int = 0
    bans: int = 0
    total_games: int = 1

    # ------------------------------------------------------------------

    @property
    def has_counter_knowledge(self) -> bool:
        return self.has_threat or self.has_mechanism

    @property
    def tier(self) -> Tier:
        """A ต้องครบทั้งสามชั้น — ไม่ใช่แค่ "กรอกเยอะ"

        เกณฑ์เข้มแบบนี้เพราะ engine ต้องใช้ทั้งสามชั้นถึงจะทำงานเต็มที่
        ตัวที่มี assessment แต่ไม่มี counter knowledge ยังใช้ mechanism matching ไม่ได้
        """
        if self.has_class and self.has_assessment and self.has_counter_knowledge:
            return "A"
        if self.has_assessment or self.has_counter_knowledge:
            return "B"
        return "C"

    @property
    def presence(self) -> float:
        return (self.picks + self.bans) / self.total_games if self.total_games else 0.0

    @property
    def ban_lean(self) -> float:
        """ถูกแบนมากกว่าถูกเลือกแค่ไหน — 0.5 คือพอ ๆ กัน · 1.0 คือแบนอย่างเดียว

        ตัวที่ค่านี้สูงคือตัวที่ทีมอาชีพเลือกจะ **ตัดทิ้ง** มากกว่าจะใช้
        ซึ่งเป็นสัญญาณของอันตรายที่ตรงกว่าจำนวน pick

        **ถ่วงด้วยขนาดตัวอย่าง** ด้วย `confidence()` ตัวเดียวกับที่ระบบใช้ทุกที่

        ถ้าไม่ถ่วง ตัวที่ถูกแบนครั้งเดียวและไม่เคยถูกเลือกจะได้ 1.0 เต็ม
        แล้วขึ้นมาอยู่เหนือตัวที่ presence 20% ซึ่งผิดอย่างชัดเจน —
        เจอจริงตอนรันครั้งแรก (`mortos` กับ `aleister` แบน 1 เลือก 0
        ขึ้นมาอันดับ 3 และ 4)
        """
        from rov.draft.stats import confidence

        tot = self.picks + self.bans
        if not tot:
            return 0.0
        return (self.bans / tot) * confidence(tot)

    @property
    def priority(self) -> float:
        """ควรกรอกก่อนแค่ไหน — สูงคือควรก่อน

        ถ่วงสามอย่างตามที่ M1.5 กำหนด แล้วคูณด้วย "ยังขาดอยู่เท่าไร"
        ตัวที่รู้ครบแล้วได้ 0 เสมอ ไม่ว่าจะดังแค่ไหน
        """
        if self.tier == "A":
            return 0.0
        gap = 1.0 if self.tier == "C" else 0.5
        strategic = 0.0
        if self.is_counter_target:
            strategic += 0.5      # counter.md ชี้ว่าตัวนี้เป็นภัยที่ต้องแก้
        if self.is_counter_answer:
            strategic += 0.25     # เป็นคำตอบของภัยอื่น
        strategic += self.ban_lean * 0.5
        return (self.presence + strategic) * gap

    @property
    def why(self) -> str:
        bits = [f"presence {self.presence * 100:.0f}%"]
        if self.bans:
            bits.append(f"แบน {self.bans} เลือก {self.picks}")
        if self.is_counter_target:
            bits.append("เป็น target ใน counter.md")
        if self.is_counter_answer:
            bits.append("เป็นคำตอบใน counter.md")
        return " · ".join(bits)

    @property
    def missing(self) -> list[str]:
        out = []
        if not self.has_class:
            out.append("hero_class")
        if not self.has_assessment:
            out.append(f"assessment ({len(self.missing_fields)} ช่อง)")
        if not self.has_counter_knowledge:
            out.append("counter knowledge")
        return out


@dataclass
class CoverageReport:
    heroes: list[HeroKnowledge] = field(default_factory=list)

    def tier(self, t: Tier) -> list[HeroKnowledge]:
        return [h for h in self.heroes if h.tier == t]

    @property
    def counts(self) -> dict[str, int]:
        return {t: len(self.tier(t)) for t in ("A", "B", "C")}

    def share(self, t: Tier) -> float:
        return len(self.tier(t)) / len(self.heroes) if self.heroes else 0.0

    def presence_share(self, t: Tier) -> float:
        """ชั้นนี้กินสัดส่วน pick+ban เท่าไรของทั้งลีก

        ตัวเลขนี้สำคัญกว่าการนับหัว — รู้ 30 ตัวจาก 119 ฟังดูน้อย
        แต่ถ้า 30 ตัวนั้นคือตัวที่ถูกใช้ 70% ของเวลา สถานการณ์ต่างกันมาก
        """
        total = sum(h.picks + h.bans for h in self.heroes)
        if not total:
            return 0.0
        return sum(h.picks + h.bans for h in self.tier(t)) / total

    def next_to_fill(self, limit: int = 15) -> list[HeroKnowledge]:
        return sorted(
            (h for h in self.heroes if h.tier != "A"),
            key=lambda h: -h.priority,
        )[:limit]


def _assessed(hero: Hero) -> bool:
    return hero.complete


def build(db: HeroDB, stats: DraftStats, book: CounterBook) -> CoverageReport:
    """ประกอบรายงาน — อ่านอย่างเดียว ไม่แก้ไฟล์ไหนทั้งสิ้น"""
    targets = book.covered_targets
    answers = book.covered_counters
    total = stats.total_games or 1
    rows: list[HeroKnowledge] = []
    for h in db.heroes:
        st = stats.get(h.id)
        rows.append(
            HeroKnowledge(
                hero_id=h.id,
                name=h.name_en or h.id,
                has_class=bool(h.hero_class),
                has_assessment=_assessed(h),
                missing_fields=list(h.missing_fields()),
                has_threat=bool(book.threats_of(h.id)),
                has_mechanism=bool(book.mechanisms_of(h.id)),
                is_counter_target=h.id in targets,
                is_counter_answer=h.id in answers,
                picks=st.picks if st else 0,
                bans=st.bans if st else 0,
                total_games=total,
            )
        )
    return CoverageReport(heroes=rows)


def report(cov: CoverageReport, top: int = 15) -> str:
    lines = ["── ความรู้ต่อฮีโร่ ──", ""]
    for t in ("A", "B", "C"):
        n = len(cov.tier(t))
        lines.append(
            f"  {t}  {TIER_LABEL[t]:<34} {n:>3}/{len(cov.heroes)} "
            f"= {cov.share(t) * 100:>5.1f}%  "
            f"· กินพื้นที่ pick+ban {cov.presence_share(t) * 100:>5.1f}%"
        )
    lines += ["", f"  ควรกรอกก่อน {top} ตัวแรก", ""]
    lines.append(f"    {'ฮีโร่':<14}{'tier':<6}{'คะแนน':>7}  ที่ยังขาด / เหตุผล")
    for h in cov.next_to_fill(top):
        lines.append(
            f"    {h.hero_id:<14}{h.tier:<6}{h.priority:>7.2f}  "
            f"{', '.join(h.missing)}"
        )
        lines.append(f"    {'':<27}{h.why}")
    return "\n".join(lines)
