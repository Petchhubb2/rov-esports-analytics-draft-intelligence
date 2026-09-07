"""Macro Knowledge Base — คลังความรู้การเดินเกม

ทำตามสคีมาที่ออกแบบไว้ใน docs/11-macro-planner.md §2

**หลักการเดียวกับ heroes.yaml: ระบบไม่แต่งกฎเอง**

ทุก rule ต้องมี `source` บอกว่ามาจากไหน และ UI ต้องแสดงที่มาเสมอ
rule ที่เป็น `assumption` ห้ามมี confidence HIGH — บังคับด้วย validator
ไม่ใช่แค่เขียนไว้ในเอกสาร

**สิ่งที่ยังไม่ได้ทำ และทำไม**

docs/11 §3 ออกแบบ rule engine ที่ประเมิน `conditions` กับสถานะเกมสด
ตอนนี้ยังไม่มีสถานะเกมสด เพราะ vision pipeline ยังตอบคำถาม Phase 0 ไม่ได้
`conditions` จึงถูกเก็บไว้ในสคีมาเพื่อรออนาคต แต่ตอนนี้ใช้ **แสดงผล**
เป็น checklist ให้คนอ่าน ไม่ได้ประเมินอัตโนมัติ

การเรียกมันว่า "ระบบแนะนำอัตโนมัติ" ทั้งที่ยังไม่มีข้อมูลสด
จะเป็นการหลอกตัวเอง — เอกสารกับโค้ดตรงนี้จึงพูดตรงกัน
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from rov.domain.enums import Confidence, GamePhase, LaneRole, MacroShape

KNOWLEDGE_DIR = Path("knowledge/macro")

# docs/11 §2 ระบุไว้ 4 ชนิด เพิ่ม game_client เข้ามาเพราะคลิปแนะนำแผนที่ในเกม
# เป็นที่มาที่หนักแน่นที่สุด — ตัวเกมบอกเอง ไม่ใช่บทวิเคราะห์ของใคร
# และ 4 ชนิดเดิมไม่มีอันไหนอธิบายมันได้ตรง
SourceType = Literal[
    "game_client", "derived_from_data", "coach_input", "literature", "assumption"
]

# ป้ายภาษาไทยของที่มา ใช้ทั้ง CLI และหน้าเว็บ ให้ตรงกัน
SOURCE_LABEL: dict[str, str] = {
    "game_client": "ตัวเกมบอกเอง",
    "derived_from_data": "คำนวณจากแมตช์จริง",
    "coach_input": "โค้ช/ผู้เล่นให้มา",
    "literature": "บทวิเคราะห์ที่อ้างอิงได้",
    "assumption": "สมมติฐาน ยังไม่ได้ตรวจ",
}


class Source(BaseModel):
    type: SourceType
    ref: str
    detail: str | None = None
    url: str | None = None

    @property
    def label(self) -> str:
        return SOURCE_LABEL[self.type]


class Condition(BaseModel):
    """เงื่อนไขของ rule

    เก็บเป็นโครงสร้างไว้รอ rule engine แต่ตอนนี้ใช้แสดงเป็นข้อความ
    `cue` คือคำอธิบายที่คนอ่านรู้เรื่อง ต้องมีเสมอเพราะตอนนี้ใช้อันนี้จริง
    """

    cue: str
    fact: str | None = None
    op: Literal["eq", "ne", "lt", "lte", "gt", "gte", "in"] | None = None
    value: object = None


class Assignment(BaseModel):
    role: LaneRole
    goto: str
    note: str | None = None


class Action(BaseModel):
    shape: MacroShape | None = None
    assignments: list[Assignment] = Field(default_factory=list)
    summary: str | None = None


class MacroRule(BaseModel):
    rule_id: str
    name: str
    phase: GamePhase
    priority: int = Field(ge=0, le=100, default=50)
    conditions: list[Condition] = Field(default_factory=list)
    action: Action
    patch: str | None = None
    confidence: Confidence = Confidence.MEDIUM
    source: Source
    notes: str | None = None
    # rule ที่ผูกกับฮีโร่บางตัว — ว่างแปลว่าใช้ได้ทั่วไป
    heroes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _assumption_cannot_be_high(self) -> MacroRule:
        if self.source.type == "assumption" and self.confidence is Confidence.HIGH:
            raise ValueError(
                f"{self.rule_id}: source เป็น assumption จะมี confidence HIGH ไม่ได้ "
                "(docs/11-macro-planner.md §2)"
            )
        return self

    @model_validator(mode="after")
    def _data_source_needs_numbers(self) -> MacroRule:
        if self.source.type == "derived_from_data" and not self.source.detail:
            raise ValueError(
                f"{self.rule_id}: source เป็น derived_from_data ต้องมี detail "
                "ที่บอกตัวเลขและจำนวนเกม ไม่งั้นตรวจย้อนไม่ได้"
            )
        return self


class MacroBook(BaseModel):
    rules: list[MacroRule] = Field(default_factory=list)

    @classmethod
    def load(cls, root: str | Path = KNOWLEDGE_DIR) -> MacroBook:
        """อ่านทุกไฟล์ .yaml ใต้ไดเรกทอรี — หนึ่งไฟล์ได้หลาย rule"""
        base = Path(root)
        rules: list[MacroRule] = []
        seen: set[str] = set()
        for path in sorted(base.rglob("*.yaml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            items = raw.get("rules", [raw]) if isinstance(raw, dict) else raw
            for item in items:
                if not item:
                    continue
                rule = MacroRule.model_validate(item)
                if rule.rule_id in seen:
                    raise ValueError(f"rule_id ซ้ำ: {rule.rule_id} ({path})")
                seen.add(rule.rule_id)
                rules.append(rule)
        return cls(rules=rules)

    def by_phase(self, phase: GamePhase) -> list[MacroRule]:
        out = [r for r in self.rules if r.phase is phase]
        return sorted(out, key=lambda r: -r.priority)

    def for_heroes(self, hero_ids: set[str]) -> list[MacroRule]:
        """rule ที่ผูกกับฮีโร่ที่ดราฟต์มา — ตอบคำถาม 'ดราฟต์ตัวนี้ต้องเล่นยังไง'"""
        out = [r for r in self.rules if r.heroes and set(r.heroes) & hero_ids]
        return sorted(out, key=lambda r: -r.priority)

    def audit(self) -> list[MacroRule]:
        """rule ที่ยังเป็นสมมติฐาน — ต้องเอามาโชว์ ไม่ใช่ซ่อน"""
        return [r for r in self.rules if r.source.type == "assumption"]

    def counts_by_source(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.rules:
            out[r.source.type] = out.get(r.source.type, 0) + 1
        return out
