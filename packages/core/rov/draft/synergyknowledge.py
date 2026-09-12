"""Synergy Knowledge — synergy ที่บอกได้ว่า **ช่วยกันอย่างไร** ไม่ใช่แค่ตัวเลข

PHASE M2A · spec เต็มใน docs/34-synergy-knowledge-spec.md · audit ใน docs/33

**ปัญหาที่โมดูลนี้แก้**

`_synergy_with()` ใน recommend.py ตอบได้แค่ "คู่นี้ชนะมากกว่าค่ากลางเท่าไร"
มันตอบไม่ได้ว่าสองตัวช่วยกันด้วยกลไกอะไร ต้องเกิดเงื่อนไขอะไรก่อน ได้ผลอะไร
และใครเป็นคนบอก · และที่สำคัญที่สุด มันสับสน **association กับ mechanism** เข้าด้วยกัน

**co-occurrence ≠ synergy** (docs/32 พิสูจน์แล้ว)

    association  "สองตัวนี้ถูกเลือกด้วยกันบ่อย + คู่นี้ชนะกี่ %"  — วัดจากข้อมูล
    mechanism   "สองตัวนี้ช่วยกันทำอะไร"                        — ความรู้ที่มี source

34/214 คู่ที่เล่นด้วยกัน ≥ 20 เกม **เปลี่ยนเครื่องหมาย** เมื่อหัก expected_synergy ออก
ดังนั้นตัวเลข co-occurrence ห้ามถูกเรียกว่า synergy โดยอัตโนมัติ โมดูลนี้จึงแยกสองสิ่งนี้
ออกจากกันในระดับ type — `SynergyEvidence` เก็บ mechanism · `SynergyAssociation` เก็บตัวเลข
· `DataCheck` เอาสองฝั่งมายืนคู่กันโดย **ไม่ overwrite** ฝั่งไหน

**ต่างจาก counter ตรงไหน**

counter มีทิศทาง (`counter → target`) และมีเส้น mechanism-inference (`threat → answer`)
synergy **ไม่มีทิศทาง** (`A + B → ผลรวม`) และ **ไม่มี threat** จึงจับคู่แบบ undirected
เส้นตรง (direct pair) เท่านั้น — ไม่เดาข้ามคู่ เพราะยังไม่มีกราฟ enabler→payoff ที่มี source

**ยังไม่ยุบเป็นคะแนน** — component ใน recommend ยังน้ำหนัก 0 (docs/34 §8)
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from rov.domain.enums import Confidence
from rov.macro.plays import Condition, DataCheck, Source

if TYPE_CHECKING:
    from rov.draft.meta import PooledStats

KNOWLEDGE_DIR = Path("knowledge/synergy")

# จำนวนเกมขั้นต่ำของคู่ ก่อนจะเชื่อ DataCheck — ตรงกับ recommend.MIN_PAIR_GAMES
MIN_PAIR_GAMES = 8

# ─────────────────────────────────────────────────────────── vocabulary
#
# ทุกป้ายมาจาก synergy.md §4 (Synergy Types) และ §6 (Synergy Tag System) ตรง ๆ
# ไม่มีป้ายไหนที่คิดขึ้นเอง — ถ้าจะเพิ่ม ต้องมีบรรทัดใน synergy.md รองรับก่อน

SynergyType = Literal[
    "global_warp",      # §6 Global_Warp_Synergy — วาร์ปดึงกลับบ้าน + ดันเลนข้าง
    "gold_boost",       # §6 Gold_Boost_Synergy — บู้สต์เงิน/บัฟ เร่ง power spike
    "aoe_pull_burst",   # §6 AoE_Pull_Burst_Synergy — รวบจุดเดียวแล้วเบิร์สต์
    "double_ult",       # §6 Double_Ult_Synergy — รีเซตอัลติ กดซ้ำ 2 รอบ
    "poke_siege",       # §6 Poke_Siege_Synergy — ตอดระยะไกลดันป้อม
    "front_to_back",    # §6 Front_to_Back_Synergy — แทงค์ค้ำ แผงหลังยิง
    "tag_farm",         # §6 Tag_Farm_Synergy — แท็กทรัพยากรร่วมกัน
]

# กลไก enabler→payoff — synergy.md §1 (Gameplay Interaction) บอกลำดับการกดสกิลไว้ชัด
SynergyMechanism = Literal[
    "recall_warp",      # วาร์ปส่งกลับบ้านรีเซตเลือด แล้วดึงกลับมาดันสองทาง  [Pair 1,7]
    "gold_accel",       # passive เพิ่มเงิน เร่งให้ carry ถึง power spike ก่อน  [Pair 2]
    "stat_buff",        # บัฟพลังโจมตี/ความเร็ว กดดันเลนต้นเกม               [Pair 3]
    "ult_reset",        # รีเซตคูลดาวน์อัลติ ทำให้กดอัลติซ้ำได้ในไฟต์เดียว     [Pair 4]
    "engage_followup",  # รวบ/เปิดพื้นที่ ตามด้วยดาเมจ AoE สังหารชุดใหญ่      [Pair 5,6]
    "cleanse_cover",    # ล้าง CC/กันสถานะ คุ้มกันการรำอัลติที่ต้อง channel    [Pair 8]
]

ObjectiveScope = Literal["pick", "ban", "both"]
EvidenceStatus = Literal["verified", "inferred", "unknown"]

SYNERGY_TYPE_LABEL: dict[str, str] = {
    "global_warp": "วาร์ปดึงกลับบ้าน + ดันเลนข้างสองทาง",
    "gold_boost": "บู้สต์เงิน/บัฟ เร่ง power spike",
    "aoe_pull_burst": "รวบศัตรูจุดเดียวแล้วเบิร์สต์ AoE",
    "double_ult": "รีเซตอัลติ กดซ้ำ 2 รอบในไฟต์เดียว",
    "poke_siege": "ตอดเลือดระยะไกล บีบแล้วดันป้อม",
    "front_to_back": "แทงค์ค้ำแผงหน้า เปิดให้แผงหลังยิงปลอดภัย",
    "tag_farm": "แท็กทรัพยากรร่วมกัน เร่งสปีดฟาร์ม",
}

MECHANISM_LABEL: dict[str, str] = {
    "recall_warp": "วาร์ปส่งเพื่อนกลับบ้านรีเซตเลือด แล้วดึงกลับมาดันป้อมสองทาง",
    "gold_accel": "passive เพิ่มเงิน เร่งให้ carry ถึงไอเทมหลักก่อนเวลา",
    "stat_buff": "บัฟพลังโจมตี/ความเร็ว ให้กดดันเลนต้นเกมได้ดุดัน",
    "ult_reset": "รีเซตคูลดาวน์อัลติของเพื่อน ให้กดอัลติซ้ำได้ 2 ครั้งในไฟต์เดียว",
    "engage_followup": "รวบ/เปิดพื้นที่ให้ศัตรูรวมจุด ตามด้วยดาเมจ AoE สังหารชุดใหญ่",
    "cleanse_cover": "ล้าง CC/กันสถานะ คุ้มกันเพื่อนที่ต้องรำอัลติค้างจนจบ",
}


# ─────────────────────────────────────────────────────────────── schema


class SynergyEvidence(BaseModel):
    """หลักฐานว่าฮีโร่สองตัวช่วยกันได้ — พร้อมกลไก เงื่อนไข ผลที่คาด จุดอ่อน และที่มา

    **ไม่ใช่คะแนน** เป็น record ที่อธิบายตัวเองได้ครบ · เก็บเฉพาะฝั่ง **mechanism**
    ตัวเลข co-occurrence (association) อยู่ที่ `SynergyAssociation` แยกต่างหากโดยเจตนา
    (STEP 3 — ห้ามรวมเป็น field เดียว)
    """

    evidence_id: str
    entity_a: str
    entity_b: str
    synergy_type: SynergyType
    mechanism: SynergyMechanism
    mechanism_detail: str
    condition: list[Condition] = Field(default_factory=list)
    # เงื่อนไขไม่สำคัญ ใช้ได้ตลอด — ต้องประกาศชัด ไม่ใช่ปล่อยว่างแล้วถือว่าใช่
    unconditional: bool = False
    expected_result: str
    weakness: str
    confidence: Confidence
    source: Source
    objective_scope: ObjectiveScope
    # entity ที่ยังยืนยันไม่ได้ว่าตรงกับ hero id ตัวไหน (เช่น "doria" — docs/33 §5)
    # ไม่ว่างเมื่อไร → status = unknown → ห้ามถูกใช้ใน matching/scoring/benchmark
    unresolved: list[str] = Field(default_factory=list)
    data_check: DataCheck | None = None

    # ------------------------------------------------------------------

    @property
    def pair(self) -> frozenset[str]:
        """คู่แบบไม่มีทิศทาง — synergy ไม่สนว่าใครมาก่อน"""
        return frozenset({self.entity_a, self.entity_b})

    @property
    def status(self) -> EvidenceStatus:
        """สถานะมาจากหลักฐาน ไม่ได้ตั้งเอง

        unknown ต้องมาก่อน — alias ที่ยืนยันไม่ได้สำคัญกว่าผล DataCheck
        เพราะเราไม่รู้ด้วยซ้ำว่าวัดถูกตัวไหม (docs/33 §5)
        """
        if self.unresolved:
            return "unknown"
        if self.data_check is None:
            return "inferred"
        return "verified" if self.data_check.verdict == "agrees" else "inferred"

    @property
    def usable(self) -> bool:
        """เอาไปใช้ match/score ได้ไหม — unknown = ไม่ได้ จนกว่าจะยืนยัน alias"""
        return self.status != "unknown"

    @model_validator(mode="after")
    def _assumption_cannot_be_high(self) -> SynergyEvidence:
        if self.source.type == "assumption" and self.confidence is Confidence.HIGH:
            raise ValueError(
                f"{self.evidence_id}: source เป็น assumption จะมี confidence HIGH ไม่ได้"
            )
        return self

    @model_validator(mode="after")
    def _contradicted_claims_cannot_be_high(self) -> SynergyEvidence:
        """ข้อมูลเราค้านอยู่ แต่ยังกล้าติดป้ายมั่นใจสูง = หลอกคนอ่าน

        กฎเดียวกับ CounterEvidence/MacroRule — docs/32 §4 พบ disagree 4 ใน 8 ข้อ
        """
        if (
            self.data_check is not None
            and self.data_check.verdict == "disagrees"
            and self.confidence is Confidence.HIGH
        ):
            raise ValueError(
                f"{self.evidence_id}: ข้อมูล synergy ของเราไม่เห็นด้วย "
                "จะมี confidence HIGH ไม่ได้"
            )
        return self

    @model_validator(mode="after")
    def _cannot_synergize_with_itself(self) -> SynergyEvidence:
        if self.entity_a == self.entity_b:
            raise ValueError(f"{self.evidence_id}: ฮีโร่ synergy กับตัวเองไม่ได้")
        return self

    @model_validator(mode="after")
    def _unresolved_must_name_an_entity(self) -> SynergyEvidence:
        stray = [u for u in self.unresolved if u not in (self.entity_a, self.entity_b)]
        if stray:
            raise ValueError(
                f"{self.evidence_id}: unresolved ต้องเป็น entity_a หรือ entity_b เท่านั้น "
                f"— {stray} ไม่ใช่ทั้งคู่"
            )
        return self

    @model_validator(mode="after")
    def _unresolved_cannot_be_high(self) -> SynergyEvidence:
        """ยังไม่รู้ด้วยซ้ำว่าเป็นฮีโร่ตัวไหน จะมั่นใจสูงได้อย่างไร (docs/33 §5)"""
        if self.unresolved and self.confidence is Confidence.HIGH:
            raise ValueError(
                f"{self.evidence_id}: entity ยังยืนยันไม่ได้ ({self.unresolved}) "
                "จะมี confidence HIGH ไม่ได้"
            )
        return self


class SynergyBook(BaseModel):
    """คลังความรู้ synergy ทั้งหมด อ่านจาก knowledge/synergy/*.yaml"""

    evidence: list[SynergyEvidence] = Field(default_factory=list)

    # ------------------------------------------------------------------

    @classmethod
    def load(cls, root: str | Path = KNOWLEDGE_DIR) -> SynergyBook:
        base = Path(root)
        if not base.exists():
            return cls()
        merged: list = []
        seen: set[str] = set()
        for path in sorted(base.rglob("*.yaml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for item in raw.get("evidence", []):
                eid = item.get("evidence_id")
                if eid in seen:
                    raise ValueError(f"{path}: evidence_id ซ้ำ — {eid}")
                seen.add(eid)
                merged.append(item)
        return cls.model_validate({"evidence": merged})

    # ---------------------------------------------------------- ค้นหา

    def between(self, a: str, b: str) -> list[SynergyEvidence]:
        """หา evidence ของคู่ (a, b) แบบไม่สนลำดับ — ว่างแปลว่า **ไม่รู้**"""
        want = frozenset({a, b})
        return [e for e in self.evidence if e.pair == want]

    def about(self, hero: str) -> list[SynergyEvidence]:
        """evidence ทั้งหมดที่พูดถึงฮีโร่ตัวนี้"""
        return [e for e in self.evidence if hero in e.pair]

    @property
    def usable_evidence(self) -> list[SynergyEvidence]:
        return [e for e in self.evidence if e.usable]

    @property
    def covered_pairs(self) -> set[frozenset[str]]:
        return {e.pair for e in self.usable_evidence}

    @property
    def covered_entities(self) -> set[str]:
        return {h for e in self.usable_evidence for h in e.pair}


# ────────────────────────── association — วัดจากข้อมูล ไม่ใช่ความรู้ (STEP 3)


@dataclass(frozen=True)
class SynergyAssociation:
    """**co-occurrence ที่วัดได้ — ไม่ใช่ข้ออ้าง synergy** (STEP 3)

    "สองตัวนี้ถูกเลือกด้วยกันบ่อยแค่ไหน และคู่นี้ชนะกี่ %"
    ตัวเลขนี้ปนความแข็งรายตัว จึงต้องเทียบกับ `expected` ก่อนตีความ
    `adjusted_score` คือส่วนที่เหลือหลังหัก expected — สัญญาณ synergy ที่แท้จริง
    (แต่ก็ยังไม่หักความแข็งของทีม — expected_synergy() ยอมรับข้อจำกัดนี้เอง)
    """

    entity_a: str
    entity_b: str
    games: int
    wins: int
    raw_win_rate: float   # shrink(g, w, 0.5) — association ถ่วงตัวอย่างแล้ว
    expected: float       # expected_synergy — ค่าที่ควรได้ถ้าไม่มีผลต่อกัน
    adjusted_score: float  # (shrink(g,w,exp) - exp) × 100 × conf — residual

    @property
    def reliable(self) -> bool:
        return self.games >= MIN_PAIR_GAMES

    @property
    def sign(self) -> Literal["positive", "negative", "flat", "unknown"]:
        """ทิศของสัญญาณ synergy — unknown เมื่อตัวอย่างไม่พอ (ห้ามเดา)"""
        if not self.reliable:
            return "unknown"
        if self.adjusted_score > 0.05:
            return "positive"
        if self.adjusted_score < -0.05:
            return "negative"
        return "flat"


def measure_association(
    pooled: PooledStats, a: str, b: str
) -> SynergyAssociation | None:
    """วัด association ของคู่ (a, b) จาก 861 เกม — คืน None เมื่อไม่เคยเล่นด้วยกัน

    **เรียก expected_synergy() เดิมใน stats.py — ไม่เขียนสูตร odds ซ้ำ**
    (หลักเดียวกับ recommend._synergy_adjusted ที่ test บังคับว่าห้าม duplicate)
    """
    from rov.draft.stats import SHRINKAGE_K, confidence, expected_synergy, shrink

    key = (a, b) if a < b else (b, a)
    m = pooled.synergies.get(key)
    if m is None:
        return None
    exp = expected_synergy(pooled.stats, a, b)
    conf = confidence(m.games, SHRINKAGE_K)
    return SynergyAssociation(
        entity_a=a,
        entity_b=b,
        games=m.games,
        wins=m.wins,
        raw_win_rate=shrink(m.games, m.wins, 0.5),
        expected=exp,
        adjusted_score=(shrink(m.games, m.wins, exp) - exp) * 100.0 * conf,
    )


def data_check_from_association(assoc: SynergyAssociation | None) -> DataCheck:
    """สร้าง DataCheck จาก association — สะพานเชื่อม mechanism ↔ data โดยไม่ทับกัน

    **DataCheck ไม่ตัดสิน mechanistic truth** (STEP 4) มันตอบแค่ว่า "ผลแพ้ชนะทั้งเกม
    เห็นด้วยกับข้ออ้างกลไกไหม" ซึ่งเป็นคนละมิติ — ตัวเลขนับทุกเกม ไม่ได้กรองเงื่อนไข
    ไม่ได้หักความแข็งของทีม และตัวอย่างถูกคัดด้วยการแบนมาแล้ว
    """
    if assoc is None:
        return DataCheck(
            verdict="insufficient", n=0,
            detail="ไม่มีเกมที่สองตัวนี้อยู่ทีมเดียวกันเลยในชุด 861 เกม",
        )
    if not assoc.reliable:
        return DataCheck(
            verdict="insufficient", n=assoc.games,
            detail=f"มีแค่ {assoc.games} เกม ต่ำกว่าเกณฑ์ MIN_PAIR_GAMES = {MIN_PAIR_GAMES}",
        )
    verdict = {"positive": "agrees", "negative": "disagrees", "flat": "mixed"}[assoc.sign]
    detail = (
        f"adjusted {assoc.raw_win_rate:.3f} เทียบค่าคาดหวัง {assoc.expected:.3f} · "
        f"score {assoc.adjusted_score:+.2f} จาก {assoc.games} เกม — "
        "วัดผลแพ้ชนะทั้งเกม ไม่ใช่กลไก (ดู STEP 4)"
    )
    return DataCheck(verdict=verdict, n=assoc.games, detail=detail)


# ──────────────────────────────────────────────── matching (undirected)


@dataclass(frozen=True)
class SynergyMatch:
    """หลักฐานหนึ่งชิ้นที่เข้ากับทีมตรงหน้า

    ไม่มี route แบบ counter เพราะ synergy จับคู่ตรง ๆ เท่านั้น (docs/33 §2)
    """

    evidence: SynergyEvidence
    ally: str
    confidence: Confidence
    condition_state: Literal["met", "unchecked", "unmet"] = "unchecked"

    @property
    def counts(self) -> bool:
        """นับเข้าคะแนนได้ไหม — เงื่อนไขที่ยังไม่ผ่านต้องไม่ถูกนับ"""
        return self.condition_state != "unmet"


@dataclass
class SynergyContext:
    """บริบทที่ evidence ต้องรู้ก่อนตัดสินว่าเข้าเงื่อนไขไหม"""

    allies: list[str] = field(default_factory=list)
    phase: int = 1
    objective: Literal["pick", "ban"] = "pick"


def _scope_allows(evidence: SynergyEvidence, objective: str) -> bool:
    return evidence.objective_scope in (objective, "both")


def _condition_state(
    evidence: SynergyEvidence, ctx: SynergyContext
) -> Literal["met", "unchecked", "unmet"]:
    """เงื่อนไขของ evidence ผ่านหรือยัง

    condition ของ synergy.md เกือบทั้งหมดเป็น cue ภาษาคน (เช่น "Capheny ต้องมีไอเทมหลัก")
    ซึ่งระบบยังไม่รู้เรื่องไอเทม จึงคืน `unchecked` ไม่ใช่ `met`
    **ห้ามแกล้งทำเป็นตรวจแล้ว** — หลักเดียวกับ counterknowledge._condition_state
    """
    if evidence.unconditional:
        return "met"
    return "unchecked" if evidence.condition else "met"


def find_matches(
    book: SynergyBook, candidate: str, ctx: SynergyContext
) -> list[SynergyMatch]:
    """หา evidence ที่บอกว่า `candidate` เข้ากับเพื่อนที่ทีมเลือกไปแล้ว

    จับคู่ **undirected** — `candidate` จะเป็น entity_a หรือ entity_b ก็ได้
    ข้าม record ที่ `not usable` (alias ยังไม่ยืนยัน) — จะไม่มีวันโผล่มา match

    คืนลิสต์ว่างเมื่อ **ไม่รู้** ซึ่งเป็นสถานะปกติของฮีโร่ส่วนใหญ่
    """
    out: list[SynergyMatch] = []
    seen: set[tuple[str, str]] = set()
    for ally in ctx.allies:
        for ev in book.between(candidate, ally):
            if not ev.usable:
                continue
            if not _scope_allows(ev, ctx.objective):
                continue
            key = (ev.evidence_id, ally)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                SynergyMatch(
                    evidence=ev,
                    ally=ally,
                    confidence=ev.confidence,
                    condition_state=_condition_state(ev, ctx),
                )
            )
    return out


# ───────────────────────────────────────────────────────── สรุปสัญญาณ


@dataclass
class SynergySummary:
    """สัญญาณย่อยที่ยัง **ไม่ยุบเป็นคะแนนเดียว**"""

    direct: int = 0
    condition_met: int = 0
    condition_unchecked: int = 0
    condition_unmet: int = 0
    best: Confidence | None = None
    matches: list[SynergyMatch] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.direct

    @property
    def known(self) -> bool:
        return self.total > 0


_RANK = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}


def summarize(matches: list[SynergyMatch]) -> SynergySummary:
    s = SynergySummary(matches=list(matches))
    for m in matches:
        s.direct += 1
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


def explain(match: SynergyMatch, objective: str = "pick") -> str:
    """ข้อความอธิบาย synergy — pick กับ ban ได้คนละประโยค (docs/34 §7)"""
    ev = match.evidence
    other = ev.entity_b if match.ally == ev.entity_a else ev.entity_a
    if objective == "ban":
        headline = (
            f"ถ้าปล่อย {other} ให้ศัตรู เขาจะจับคู่กับ {match.ally} ที่เปิดไปแล้วได้"
        )
    else:
        headline = f"{other} เข้าคู่กับ {match.ally} ที่ทีมเราเลือกไปแล้ว"

    lines = [
        headline,
        f"  ชนิด:       {SYNERGY_TYPE_LABEL[ev.synergy_type]}",
        f"  กลไก:       {MECHANISM_LABEL[ev.mechanism]}",
        f"              {ev.mechanism_detail}",
    ]
    if ev.unconditional:
        lines.append("  เงื่อนไข:   ไม่มี ใช้ได้ตลอด")
    else:
        mark = {
            "met": "ผ่านแล้ว",
            "unmet": "ยังไม่เข้าเงื่อนไข",
            "unchecked": "ระบบยังตรวจให้ไม่ได้ ต้องดูเอง",
        }[match.condition_state]
        for c in ev.condition:
            lines.append(f"  เงื่อนไข:   {c.cue}  [{mark}]")
    lines.append(f"  ผลที่คาด:   {ev.expected_result}")
    lines.append(f"  จุดอ่อน:    {ev.weakness}")
    lines.append(f"  ที่มา:      {ev.source.ref} ({ev.source.label})")
    lines.append(f"  ความมั่นใจ: {match.confidence.value}")
    if ev.data_check is not None:
        dc = ev.data_check
        n = f" · {dc.n} เกม" if dc.n else ""
        lines.append(f"  ข้อมูลเรา:  {dc.label}{n} — {dc.detail}")
    else:
        lines.append("  ข้อมูลเรา:  ยังไม่ได้ตรวจกับแมตช์จริง")
    return "\n".join(lines)


def coverage(book: SynergyBook, hero_ids: list[str]) -> dict[str, object]:
    """ครอบคลุมแค่ไหนจริง ๆ — รายงานตรง ๆ ไม่ขยายด้วยการเดา"""
    n = len(hero_ids) or 1
    known = {h for h in hero_ids if any(h in e.pair for e in book.usable_evidence)}
    return {
        "heroes": len(hero_ids),
        "evidence": len(book.evidence),
        "usable": len(book.usable_evidence),
        "unknown_records": sum(1 for e in book.evidence if e.status == "unknown"),
        "pairs": len(book.covered_pairs),
        "entities_known": len(known),
        "entity_share": len(known) / n,
        "unknown_heroes": n - len(known),
        "with_data_check": sum(1 for e in book.evidence if e.data_check),
        "verified": sum(1 for e in book.evidence if e.status == "verified"),
        "inferred": sum(1 for e in book.evidence if e.status == "inferred"),
        "unconditional": sum(1 for e in book.evidence if e.unconditional),
    }


# ─────────────────────────────── คุณภาพของหลักฐาน — association ↔ mechanism


VERDICT_LABEL: dict[str, str] = {
    "agrees": "agree",
    "disagrees": "disagree",
    "mixed": "partial",
    "insufficient": "insufficient",
}


@dataclass
class QualityRow:
    """ข้ออ้างหนึ่งข้อ — ฝั่ง mechanism กับฝั่ง association (data) ยืนคู่กัน

    **disagree ไม่ได้แปลว่า synergy ใช้ไม่ได้** มันแปลว่าผลแพ้ชนะทั้งเกมไม่ยืนยัน
    ซึ่งเป็นคนละมิติกับ "กลไกทำงานไหม" — ห้ามเอา data เขียนทับ knowledge
    """

    evidence_id: str
    entity_a: str
    entity_b: str
    mechanism_claim: str        # ฝั่ง mechanism (ความรู้)
    association_detail: str      # ฝั่ง association (ตัวเลข)
    verdict: str
    n: int | None
    confidence: Confidence
    status: EvidenceStatus

    @property
    def rule_still_stands(self) -> bool:
        """ข้ออ้างยังอยู่ในระบบไหม — ทุกข้อยังอยู่ แม้ข้อมูลจะค้าน"""
        return True


def quality_table(book: SynergyBook) -> list[QualityRow]:
    out: list[QualityRow] = []
    for e in book.evidence:
        dc = e.data_check
        out.append(
            QualityRow(
                evidence_id=e.evidence_id,
                entity_a=e.entity_a,
                entity_b=e.entity_b,
                mechanism_claim=(
                    f"{e.entity_a} + {e.entity_b} — {MECHANISM_LABEL[e.mechanism]}"
                ),
                association_detail=dc.detail if dc else "ยังไม่ได้ตรวจกับแมตช์จริง",
                verdict=(
                    "unknown" if e.status == "unknown"
                    else VERDICT_LABEL.get(dc.verdict, "insufficient") if dc
                    else "insufficient"
                ),
                n=dc.n if dc else None,
                confidence=e.confidence,
                status=e.status,
            )
        )
    return out


def quality_report(book: SynergyBook) -> str:
    rows = quality_table(book)
    counts = Counter(r.verdict for r in rows)
    lines = [
        "── คุณภาพหลักฐาน synergy ──",
        "",
        f"  {'id':<22}{'pair':<24}{'verdict':<14}{'conf':<8}{'n':>5}",
    ]
    for r in sorted(rows, key=lambda x: (x.verdict, x.evidence_id)):
        pair = f"{r.entity_a} + {r.entity_b}"
        lines.append(
            f"  {r.evidence_id:<22}{pair:<24}{r.verdict:<14}"
            f"{r.confidence.value:<8}{r.n if r.n is not None else '—':>5}"
        )
    lines += ["", "  สรุป  " + " · ".join(f"{k} {v}" for k, v in counts.most_common())]
    lines += [
        "",
        "  ⚠️ association (co-occurrence) ≠ mechanism (กลไก)",
        "     disagree แปลว่าผลแพ้ชนะทั้งเกมไม่ยืนยัน ไม่ใช่ว่ากลไกใช้ไม่ได้",
        "     ข้ออ้างทุกข้อยังอยู่ในระบบ · สิ่งที่เปลี่ยนคือความมั่นใจ",
    ]
    return "\n".join(lines)


def data_check_report(pooled: PooledStats, book: SynergyBook) -> str:
    """เทียบข้ออ้างทุกข้อกับ 861 เกม สด ๆ — measurement เท่านั้น

    ใช้ตรวจว่า data_check ในไฟล์ตรงกับที่คำนวณได้จริง (docs/35)
    """
    lines = [
        "── synergy DataCheck (สดจากข้อมูล) ──",
        "",
        f"  {'pair':<24}{'g':>4}{'raw':>8}{'exp':>8}{'score':>8}  verdict",
    ]
    for e in book.evidence:
        assoc = measure_association(pooled, e.entity_a, e.entity_b)
        dc = data_check_from_association(assoc)
        tag = " (unresolved)" if e.status == "unknown" else ""
        if assoc is None:
            lines.append(
                f"  {e.entity_a + '+' + e.entity_b:<24}{'—':>4}{'—':>8}{'—':>8}"
                f"{'—':>8}  {VERDICT_LABEL[dc.verdict]}{tag}"
            )
            continue
        lines.append(
            f"  {e.entity_a + '+' + e.entity_b:<24}{assoc.games:>4}"
            f"{assoc.raw_win_rate:>8.3f}{assoc.expected:>8.3f}"
            f"{assoc.adjusted_score:>+8.2f}  {VERDICT_LABEL[dc.verdict]}{tag}"
        )
    return "\n".join(lines)
