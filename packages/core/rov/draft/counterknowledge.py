"""Counter Knowledge — counter ที่บอกได้ว่า **เพราะอะไร** ไม่ใช่แค่ตัวเลข

PHASE M1 · spec เต็มใน docs/28-counter-knowledge-spec.md

**ปัญหาที่โมดูลนี้แก้**

`_counter_against()` ใน recommend.py ตอบได้แค่ "คู่นี้ชนะมากกว่าค่ากลางเท่าไร"
มันตอบไม่ได้ว่า counter ด้วยกลไกอะไร ต้องเกิดเงื่อนไขอะไรก่อน เสี่ยงอะไร
และใครเป็นคนบอก

**ความรู้กับตัวเลขขัดกันได้โดยไม่มีใครผิด**

เอาข้ออ้าง Direct Hero Counter 15 คู่จาก counter.md มาเทียบกับ 861 เกมจริง
ได้ผลว่า **เห็นด้วย 2 · ไม่เห็นด้วย 8 · ข้อมูลไม่พอ 5** (docs/27 §3)

นั่นไม่ได้แปลว่าความรู้ผิด เพราะสองฝั่งตอบคนละคำถาม

    ความรู้   "Tachi ผลัก Rouie ออกจากวงวาร์ปได้ไหม"   — จริง/เท็จเกี่ยวกับตัวเกม
    ตัวเลข    "เกมที่ Tachi อยู่ตรงข้าม Rouie ชนะกี่ %"  — ผลรวมทั้งเกม

และตัวอย่างถูกคัดมาแล้ว — `rouie` ถูกแบน 565 จาก 861 เกม เกมที่เขาได้ลง
คือเกมที่อีกฝั่ง**เลือกจะไม่แบน** ซึ่งไม่ใช่ตัวอย่างสุ่ม

โมดูลนี้จึงเก็บ **ทั้งสองฝั่งไว้ด้วยกัน** ผ่าน `DataCheck` แบบเดียวกับที่
`rov/macro/plays.py` ทำกับ macro rule มาก่อนแล้ว และห้ามข้อที่ข้อมูลค้าน
ติดป้าย confidence HIGH

**ห้ามยุบเป็นคะแนนเดียว** — `counter.md` §6 เสนอ `Direct_Counter_Score +30%`
มาให้เลย ถ้าทำตามทันทีจะได้ระบบที่เดิมพันบนตัวเลขที่ข้อมูลเราค้าน 8 ใน 15 ข้อ
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from rov.domain.enums import Confidence, LaneRole
from rov.macro.plays import Condition, DataCheck, Source

KNOWLEDGE_DIR = Path("knowledge/counter")

# ─────────────────────────────────────────────────────────── vocabulary
#
# ทุกป้ายในสามชุดนี้มาจาก counter.md §6 (Algorithm Potential) ตรง ๆ
# ไม่มีป้ายไหนที่คิดขึ้นเอง — ถ้าจะเพิ่ม ต้องมีบรรทัดใน counter.md รองรับก่อน

ThreatTag = Literal[
    "recall_warp",        # ดึงทีมกลับบ้าน/เติมไฟต์ด้วยวงวาร์ป
    "heavy_cc",           # สเปม CC ล็อกจนจ่ายดาเมจไม่ได้
    "tank_frontline",     # ค้ำไฟต์จนยิงไม่เข้า
    "immobile_backline",  # แผงหลังขาตาย เสี่ยงโดนล้วง
    "poke_siege",         # ตอดเลือดระยะไกล บีบไม่ให้เข้าใกล้
]

MechanismTag = Literal[
    "burst",         # ฆ่าเป้าหมายเดี่ยวในชุดเดียว
    "displacement",  # ผลัก/ปัดออกจากพื้นที่
    "cleanse",       # ล้างสถานะ CC ทั้งทีม
    "tank_melt",     # true damage / %HP ละลายแผงหน้า
    "dive",          # พุ่งข้ามแผงหน้าถึงแผงหลัง
    "lane_trade",    # ได้เปรียบการเทรดในเลน 1v1
    "peel",          # ปกป้องแผงหลังจากตัวล้วง
]

CounterType = Literal[
    "hard", "displacement", "cleanse", "burst", "poke", "lane", "flex"
]

ObjectiveScope = Literal["pick", "ban", "both"]
EvidenceStatus = Literal["verified", "inferred", "unknown"]

THREAT_LABEL: dict[str, str] = {
    "recall_warp": "ดึงทีมกลับบ้าน/เติมไฟต์ด้วยวงวาร์ป",
    "heavy_cc": "สเปม CC ล็อกจนจ่ายดาเมจไม่ได้",
    "tank_frontline": "ค้ำไฟต์จนยิงแผงหน้าไม่เข้า",
    "immobile_backline": "แผงหลังขาตาย เสี่ยงโดนล้วง",
    "poke_siege": "ตอดเลือดระยะไกล บีบไม่ให้เข้าใกล้",
}

MECHANISM_LABEL: dict[str, str] = {
    "burst": "เบิร์สต์สังหารเป้าหมายเดี่ยวในชุดเดียว",
    "displacement": "ผลัก/ปัดศัตรูออกจากพื้นที่",
    "cleanse": "ล้างสถานะ CC ให้ทั้งทีม",
    "tank_melt": "ดาเมจจริง/ตาม %HP ละลายแผงหน้า",
    "dive": "พุ่งข้ามแผงหน้าเข้าถึงแผงหลัง",
    "lane_trade": "ได้เปรียบการเทรดดาเมจในเลน 1v1",
    "peel": "ปกป้องแผงหลังจากตัวล้วง",
}

# ลดความมั่นใจหนึ่งขั้น — ใช้กับ evidence ที่ได้จากการจับคู่กลไก
# ไม่ใช่คำกล่าวตรง ๆ ของ source (docs/28 §4.1)
_DOWNGRADE: dict[Confidence, Confidence] = {
    Confidence.HIGH: Confidence.MEDIUM,
    Confidence.MEDIUM: Confidence.LOW,
    Confidence.LOW: Confidence.LOW,
}


# ─────────────────────────────────────────────────────────────── schema


class HeroThreat(BaseModel):
    """ฮีโร่ตัวนี้สร้างภัยแบบไหน — ข้อเท็จจริงที่ต้องมี source"""

    hero: str
    threats: list[ThreatTag] = Field(min_length=1)
    detail: str
    source: Source


class HeroCapability(BaseModel):
    """ฮีโร่ตัวนี้มีกลไกอะไร — ข้อเท็จจริงที่ต้องมี source

    ⚠️ ห้าม derive จาก hero_class หรือ Liquipedia skill tag
    docs/27 §5.3 พิสูจน์แล้วว่าป้ายที่ดึงมาหยาบเกิน (ได้ "Control" ไม่ใช่
    "Knock Back") และครอบคลุมแค่ 30/119 ตัว การเดาจากตรงนั้นจะผิดแบบเงียบ ๆ
    """

    hero: str
    mechanisms: list[MechanismTag] = Field(min_length=1)
    detail: str
    source: Source


class MechanismAnswer(BaseModel):
    """กลไกไหนตอบภัยแบบไหนได้ — ขากลางของ mechanism matching"""

    threat: ThreatTag
    mechanisms: list[MechanismTag] = Field(min_length=1)
    reason: str
    source: Source
    confidence: Confidence = Confidence.MEDIUM


class CounterEvidence(BaseModel):
    """หลักฐานว่าฮีโร่หนึ่งแก้ทางอีกฮีโร่หนึ่งได้ — พร้อมเหตุผลและที่มา

    **ไม่ใช่คะแนน** เป็น record ที่อธิบายตัวเองได้ครบ
    การแปลงเป็นคะแนนเกิดทีหลังและตอนนี้ยังน้ำหนัก 0
    """

    evidence_id: str
    target: str
    counter: str
    counter_type: CounterType
    threat: ThreatTag | None = None
    mechanism: MechanismTag
    mechanism_detail: str
    condition: list[Condition] = Field(default_factory=list)
    # เงื่อนไขไม่สำคัญ ใช้ได้ตลอด — ต้องประกาศชัด ไม่ใช่ปล่อยว่างแล้วถือว่าใช่
    unconditional: bool = False
    risk: str
    confidence: Confidence
    source: Source
    objective_scope: ObjectiveScope
    lane: LaneRole | None = None
    data_check: DataCheck | None = None

    # ------------------------------------------------------------------

    @property
    def status(self) -> EvidenceStatus:
        """สถานะมาจากหลักฐาน ไม่ได้ตั้งเอง (docs/28 §2.3)"""
        if self.data_check is None:
            return "inferred"
        return "verified" if self.data_check.verdict == "agrees" else "inferred"

    @model_validator(mode="after")
    def _assumption_cannot_be_high(self) -> CounterEvidence:
        if self.source.type == "assumption" and self.confidence is Confidence.HIGH:
            raise ValueError(
                f"{self.evidence_id}: source เป็น assumption จะมี confidence HIGH ไม่ได้"
            )
        return self

    @model_validator(mode="after")
    def _contradicted_claims_cannot_be_high(self) -> CounterEvidence:
        """ข้อมูลเราค้านอยู่ แต่ยังกล้าติดป้ายมั่นใจสูง = หลอกคนอ่าน

        กฎเดียวกับ MacroRule — และ docs/27 §3 พบว่าเกิดขึ้นจริง 8 ใน 15 ข้อ
        """
        if (
            self.data_check is not None
            and self.data_check.verdict == "disagrees"
            and self.confidence is Confidence.HIGH
        ):
            raise ValueError(
                f"{self.evidence_id}: ข้อมูล 861 เกมของเราไม่เห็นด้วย "
                "จะมี confidence HIGH ไม่ได้"
            )
        return self

    @model_validator(mode="after")
    def _cannot_counter_itself(self) -> CounterEvidence:
        if self.target == self.counter:
            raise ValueError(f"{self.evidence_id}: ฮีโร่ counter ตัวเองไม่ได้")
        return self

    @model_validator(mode="after")
    def _lane_counter_needs_a_lane(self) -> CounterEvidence:
        if self.counter_type == "lane" and self.lane is None:
            raise ValueError(
                f"{self.evidence_id}: counter_type=lane ต้องระบุว่าเลนไหน "
                "ไม่งั้นตรวจเงื่อนไขไม่ได้"
            )
        return self


class CounterBook(BaseModel):
    """คลังความรู้ counter ทั้งหมด อ่านจาก knowledge/counter/*.yaml"""

    threats: list[HeroThreat] = Field(default_factory=list)
    capabilities: list[HeroCapability] = Field(default_factory=list)
    answers: list[MechanismAnswer] = Field(default_factory=list)
    evidence: list[CounterEvidence] = Field(default_factory=list)

    # ------------------------------------------------------------------

    @classmethod
    def load(cls, root: str | Path = KNOWLEDGE_DIR) -> CounterBook:
        base = Path(root)
        if not base.exists():
            return cls()
        merged: dict[str, list] = {
            "threats": [], "capabilities": [], "answers": [], "evidence": []
        }
        seen: set[str] = set()
        for path in sorted(base.rglob("*.yaml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for key in merged:
                for item in raw.get(key, []):
                    if key == "evidence":
                        eid = item.get("evidence_id")
                        if eid in seen:
                            raise ValueError(f"{path}: evidence_id ซ้ำ — {eid}")
                        seen.add(eid)
                    merged[key].append(item)
        return cls.model_validate(merged)

    # ---------------------------------------------------------- ค้นหา

    def threats_of(self, hero: str) -> list[ThreatTag]:
        """ภัยที่ฮีโร่ตัวนี้สร้าง — ว่างแปลว่า **ไม่รู้** ไม่ใช่ไม่มีภัย"""
        return [t for row in self.threats if row.hero == hero for t in row.threats]

    def mechanisms_of(self, hero: str) -> list[MechanismTag]:
        """กลไกที่ฮีโร่ตัวนี้มี — ว่างแปลว่า **ไม่รู้**"""
        return [
            m for row in self.capabilities if row.hero == hero for m in row.mechanisms
        ]

    def answers_for(self, threat: ThreatTag) -> list[MechanismAnswer]:
        return [a for a in self.answers if a.threat == threat]

    def direct(self, counter: str, target: str) -> list[CounterEvidence]:
        return [
            e for e in self.evidence if e.counter == counter and e.target == target
        ]

    @property
    def covered_targets(self) -> set[str]:
        return {e.target for e in self.evidence}

    @property
    def covered_counters(self) -> set[str]:
        return {e.counter for e in self.evidence}


# ──────────────────────────────────────────────── mechanism matching


@dataclass(frozen=True)
class Match:
    """หลักฐานหนึ่งชิ้นที่เข้ากับสถานการณ์ตรงหน้า

    `route` บอกว่ามาจากไหน — direct คือ source พูดถึงคู่นี้ตรง ๆ
    ส่วน mechanism คือการอนุมานข้ามคู่ ซึ่งความมั่นใจถูกลดหนึ่งขั้นแล้ว
    """

    evidence: CounterEvidence
    route: Literal["direct", "mechanism"]
    confidence: Confidence
    enemy: str
    threat: ThreatTag | None = None
    condition_state: Literal["met", "unchecked", "unmet"] = "unchecked"

    @property
    def counts(self) -> bool:
        """นับเข้าคะแนนได้ไหม — เงื่อนไขที่ยังไม่ผ่านต้องไม่ถูกนับ"""
        return self.condition_state != "unmet"


@dataclass
class CounterContext:
    """บริบทที่ evidence ต้องรู้ก่อนตัดสินว่าเข้าเงื่อนไขไหม (docs/28 §5)"""

    enemies: list[str] = field(default_factory=list)
    allies: list[str] = field(default_factory=list)
    phase: int = 1
    objective: Literal["pick", "ban"] = "pick"
    candidate_lane: LaneRole | None = None


def _scope_allows(evidence: CounterEvidence, objective: str) -> bool:
    return evidence.objective_scope in (objective, "both")


def _condition_state(
    evidence: CounterEvidence, ctx: CounterContext
) -> Literal["met", "unchecked", "unmet"]:
    """เงื่อนไขของ evidence ผ่านหรือยัง

    ตอนนี้ condition ของ counter.md เกือบทั้งหมดเป็น `cue` ภาษาคน
    เช่น "ก่อน Marja ได้ดาบ Z" ซึ่งระบบยังไม่รู้เรื่องไอเทม
    จึงคืน `unchecked` ไม่ใช่ `met` — **ห้ามแกล้งทำเป็นตรวจแล้ว**

    สิ่งเดียวที่ตรวจได้จริงตอนนี้คือเลน เพราะเรารู้เลนของ candidate
    """
    if evidence.unconditional:
        return "met"
    if evidence.counter_type == "lane" and evidence.lane is not None:
        if ctx.candidate_lane is None:
            return "unchecked"
        return "met" if ctx.candidate_lane == evidence.lane else "unmet"
    return "unchecked" if evidence.condition else "met"


def find_matches(
    book: CounterBook, candidate: str, ctx: CounterContext
) -> list[Match]:
    """หา evidence ทั้งหมดที่บอกว่า `candidate` แก้ทางศัตรูที่เปิดมาแล้ว

    เดินสองเส้นทางตาม docs/28 §4

        1. direct      — source พูดถึงคู่นี้ตรง ๆ
        2. mechanism   — ศัตรูมี threat T · มีกฎว่ากลไก M ตอบ T ได้
                         · candidate มีกลไก M

    คืนลิสต์ว่างเมื่อ **ไม่รู้** ซึ่งเป็นสถานะปกติของฮีโร่ส่วนใหญ่
    ห้ามคืน Match ที่มี confidence ต่ำแทนการไม่รู้
    """
    out: list[Match] = []
    seen: set[tuple[str, str]] = set()

    # ── เส้นที่ 1 · direct ────────────────────────────────────────────
    for enemy in ctx.enemies:
        for ev in book.direct(candidate, enemy):
            if not _scope_allows(ev, ctx.objective):
                continue
            seen.add((ev.evidence_id, enemy))
            out.append(
                Match(
                    evidence=ev,
                    route="direct",
                    confidence=ev.confidence,
                    enemy=enemy,
                    threat=ev.threat,
                    condition_state=_condition_state(ev, ctx),
                )
            )

    # ── เส้นที่ 2 · mechanism ────────────────────────────────────────
    have = set(book.mechanisms_of(candidate))
    if not have:
        return out  # ไม่รู้ว่า candidate มีกลไกอะไร → ไม่เดา
    for enemy in ctx.enemies:
        for threat in book.threats_of(enemy):
            for answer in book.answers_for(threat):
                usable = have & set(answer.mechanisms)
                if not usable:
                    continue
                for ev in book.evidence:
                    if ev.mechanism not in usable or ev.threat != threat:
                        continue
                    if not _scope_allows(ev, ctx.objective):
                        continue
                    if (ev.evidence_id, enemy) in seen:
                        continue
                    seen.add((ev.evidence_id, enemy))
                    out.append(
                        Match(
                            evidence=ev,
                            route="mechanism",
                            # อนุมานข้ามคู่ ความมั่นใจต้องลดลงหนึ่งขั้นเสมอ
                            confidence=_DOWNGRADE[ev.confidence],
                            enemy=enemy,
                            threat=threat,
                            condition_state=_condition_state(ev, ctx),
                        )
                    )
    return out


# ───────────────────────────────────────────────────────── สรุปสัญญาณ


@dataclass
class EvidenceSummary:
    """สัญญาณย่อยที่ยัง **ไม่ยุบเป็นคะแนนเดียว** (docs/28 §7.1)"""

    direct: int = 0
    mechanism: int = 0
    condition_met: int = 0
    condition_unchecked: int = 0
    condition_unmet: int = 0
    best: Confidence | None = None
    matches: list[Match] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.direct + self.mechanism

    @property
    def known(self) -> bool:
        """มีอะไรให้พูดถึงไหม — False คือ UNKNOWN ที่แท้จริง"""
        return self.total > 0


_RANK = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}


def summarize(matches: list[Match]) -> EvidenceSummary:
    s = EvidenceSummary(matches=list(matches))
    for m in matches:
        if m.route == "direct":
            s.direct += 1
        else:
            s.mechanism += 1
        if m.condition_state == "met":
            s.condition_met += 1
        elif m.condition_state == "unmet":
            s.condition_unmet += 1
        else:
            s.condition_unchecked += 1
        if m.counts and (s.best is None or _RANK[m.confidence] > _RANK[s.best]):
            s.best = m.confidence
    return s


# ─────────────────────────────────────────────────────────── คำอธิบาย


def explain(match: Match, objective: str = "pick") -> str:
    """ข้อความตาม docs/28 §8 — pick กับ ban ได้คนละประโยค"""
    ev = match.evidence
    if objective == "ban":
        headline = (
            f"ถ้าปล่อย {ev.counter} ให้ศัตรู เขาจะใช้กลไกนี้กด {ev.target} ของเรา"
        )
    else:
        headline = f"{ev.counter} ช่วยเราแก้ {ev.target} ที่ศัตรูเปิดมา"

    lines = [
        headline,
        f"  กลไก:      {MECHANISM_LABEL[ev.mechanism]}",
        f"             {ev.mechanism_detail}",
    ]
    if ev.threat:
        lines.insert(1, f"  ภัย:       {THREAT_LABEL[ev.threat]}")
    if ev.unconditional:
        lines.append("  เงื่อนไข:   ไม่มี ใช้ได้ตลอด")
    else:
        for c in ev.condition:
            mark = {
                "met": "ผ่านแล้ว",
                "unmet": "ยังไม่เข้าเงื่อนไข",
                "unchecked": "ระบบยังตรวจให้ไม่ได้ ต้องดูเอง",
            }[match.condition_state]
            lines.append(f"  เงื่อนไข:   {c.cue}  [{mark}]")
    lines.append(f"  ความเสี่ยง: {ev.risk}")
    lines.append(f"  ที่มา:      {ev.source.ref} ({ev.source.label})")
    conf = f"  ความมั่นใจ: {match.confidence.value}"
    if match.route == "mechanism":
        conf += f"  (ลดจาก {ev.confidence.value} เพราะอนุมานข้ามคู่)"
    lines.append(conf)
    if ev.data_check is not None:
        dc = ev.data_check
        n = f" · {dc.n} เกม" if dc.n else ""
        lines.append(f"  ข้อมูลเรา:  {dc.label}{n} — {dc.detail}")
    else:
        lines.append("  ข้อมูลเรา:  ยังไม่ได้ตรวจกับแมตช์จริง")
    return "\n".join(lines)


def coverage(book: CounterBook, hero_ids: list[str]) -> dict[str, object]:
    """ครอบคลุมแค่ไหนจริง ๆ — ตัวเลขนี้ต้องรายงานตรง ๆ ไม่ใช่ขยายด้วยการเดา"""
    n = len(hero_ids) or 1
    known_threat = {h for h in hero_ids if book.threats_of(h)}
    known_mech = {h for h in hero_ids if book.mechanisms_of(h)}
    return {
        "heroes": len(hero_ids),
        "evidence": len(book.evidence),
        "targets": len(book.covered_targets),
        "counters": len(book.covered_counters),
        "threat_known": len(known_threat),
        "threat_share": len(known_threat) / n,
        "mechanism_known": len(known_mech),
        "mechanism_share": len(known_mech) / n,
        "unknown_heroes": n - len(known_threat | known_mech),
        "with_data_check": sum(1 for e in book.evidence if e.data_check),
        "verified": sum(1 for e in book.evidence if e.status == "verified"),
        "inferred": sum(1 for e in book.evidence if e.status == "inferred"),
        "unconditional": sum(1 for e in book.evidence if e.unconditional),
    }
