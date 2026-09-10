"""ฐานข้อมูลคุณลักษณะฮีโร่ — Blueprint §38, §39

**สิ่งสำคัญที่สุดของไฟล์นี้**

ค่าเชิงคุณภาพ (engage, peel, scaling ฯลฯ) เป็นการประเมินของมนุษย์
ระบบ **ห้ามเดาค่าเหล่านี้เอง** และห้ามเติมค่ากลางให้อัตโนมัติ
ฮีโร่ที่ยังไม่ได้กรอกจะมีค่าเป็น null และ Composition Engine
จะปฏิเสธการให้คะแนน พร้อมบอกว่าขาดตัวไหน

เหตุผล: Blueprint §70 ข้อ 8 กำหนดว่าทุกคำแนะนำต้องมีเหตุผลจากข้อมูล
ถ้าเติมค่าเดาลงไป ระบบจะให้คำแนะนำที่ดูน่าเชื่อแต่ไม่มีฐานรองรับ
ซึ่งอันตรายกว่าการบอกตรง ๆ ว่ายังไม่รู้

ข้อมูลที่ระบบเติมเองได้ เพราะคำนวณจากแมตช์จริง อยู่ใน rov/draft/stats.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from rov.domain.enums import DamageType, HeroClass, LaneRole, MacroTag

Rating = int  # 0-100 เชิงสัมพัทธ์เทียบกับฮีโร่ทั้งหมด

# มิติที่ Composition Engine ต้องใช้ ถ้าขาดข้อใดข้อหนึ่งจะให้คะแนนไม่ได้
REQUIRED_UTILITY = (
    "engage", "disengage", "peel", "cc_hard", "cc_soft", "mobility",
    "poke", "sustain", "frontline", "objective", "waveclear", "splitpush",
)


class Scaling(BaseModel):
    """ความแข็งแกร่งสัมพัทธ์ตามช่วงเกม"""

    early: Rating | None = None
    mid: Rating | None = None
    late: Rating | None = None

    @property
    def filled(self) -> bool:
        return all(v is not None for v in (self.early, self.mid, self.late))


class Utility(BaseModel):
    engage: Rating | None = None
    disengage: Rating | None = None
    peel: Rating | None = None
    cc_hard: Rating | None = None
    cc_soft: Rating | None = None
    mobility: Rating | None = None
    poke: Rating | None = None
    sustain: Rating | None = None
    frontline: Rating | None = None
    objective: Rating | None = None
    waveclear: Rating | None = None
    splitpush: Rating | None = None

    def missing(self) -> list[str]:
        return [k for k in REQUIRED_UTILITY if getattr(self, k) is None]

    @property
    def filled(self) -> bool:
        return not self.missing()


class Damage(BaseModel):
    type: DamageType | None = None
    profile: Literal["burst", "sustained", "poke"] | None = None
    target: Literal["single", "aoe"] | None = None

    @property
    def filled(self) -> bool:
        return self.type is not None


class Hero(BaseModel):
    id: str
    name_en: str | None = None
    name_th: str | None = None

    # class ตามเกม กับ เลนที่เล่นจริง เป็นคนละเรื่อง (docs/08 §6)
    hero_class: list[HeroClass] = Field(default_factory=list)
    lane_roles: list[LaneRole] = Field(default_factory=list)

    damage: Damage = Field(default_factory=Damage)
    range: Literal["melee", "short", "long"] | None = None
    scaling: Scaling = Field(default_factory=Scaling)
    utility: Utility = Field(default_factory=Utility)
    macro_tags: list[MacroTag] = Field(default_factory=list)

    strong_against_traits: list[str] = Field(default_factory=list)
    weak_against_traits: list[str] = Field(default_factory=list)

    # ที่มาของค่าที่กรอก — บังคับให้ระบุ ตาม Blueprint §36
    filled_by: str | None = None
    filled_on: str | None = None
    notes: str | None = None

    # ชนิดของที่มา — ต้องอ่านด้วยเครื่องได้ ไม่ใช่ซ่อนอยู่ในข้อความ filled_by
    #
    #   human      คนที่รู้เกมประเมินเอง — น่าเชื่อที่สุด
    #   assistant  ผู้ช่วย AI ประเมินจากหลักฐานที่อ้างอิงได้ (ดู notes)
    #              ใช้ได้ แต่ต้องขึ้นคำเตือนทุกครั้งที่เอาไปคิดคะแนน
    #   derived    คำนวณจากข้อมูลแมตช์จริงหรือยกมาจาก Liquipedia ตรง ๆ
    #
    # เหตุผลที่ต้องมีช่องนี้: Composition Engine ต้องบอกผู้ใช้ได้ว่าคะแนนที่เห็น
    # ยืนอยู่บนอะไร ถ้าเก็บที่มาไว้เป็นข้อความอิสระ ระบบจะแยกไม่ออก
    # แล้วค่าที่ AI ประเมินจะดูเท่ากับค่าที่โค้ชกรอก ซึ่งไม่ควรเท่ากัน
    filled_kind: Literal["human", "assistant", "derived"] | None = None

    @model_validator(mode="after")
    def _check_ratings(self) -> Hero:
        for name, val in [
            *((k, getattr(self.utility, k)) for k in REQUIRED_UTILITY),
            ("scaling.early", self.scaling.early),
            ("scaling.mid", self.scaling.mid),
            ("scaling.late", self.scaling.late),
        ]:
            if val is not None and not (0 <= val <= 100):
                raise ValueError(f"{self.id}.{name} = {val} ต้องอยู่ในช่วง 0-100")
        return self

    # ------------------------------------------------------------------

    def missing_fields(self) -> list[str]:
        """รายการสิ่งที่ยังต้องกรอก — ว่างแปลว่าใช้กับ Composition Engine ได้"""
        out: list[str] = []
        if not self.lane_roles:
            out.append("lane_roles")
        if not self.damage.filled:
            out.append("damage.type")
        if self.range is None:
            out.append("range")
        if not self.scaling.filled:
            out.extend(
                f"scaling.{k}"
                for k in ("early", "mid", "late")
                if getattr(self.scaling, k) is None
            )
        out.extend(f"utility.{k}" for k in self.utility.missing())
        return out

    @property
    def complete(self) -> bool:
        return not self.missing_fields()

    def u(self, key: str) -> int:
        """อ่านค่า utility โดยบังคับว่าต้องกรอกแล้ว"""
        val = getattr(self.utility, key)
        if val is None:
            raise ValueError(
                f"ฮีโร่ {self.id} ยังไม่ได้กรอก utility.{key} — "
                "ระบบไม่เดาค่าให้ ต้องกรอกก่อนจึงจะคำนวณได้"
            )
        return val


class HeroDB(BaseModel):
    version: int = 1
    patch: str | None = None
    heroes: list[Hero] = Field(default_factory=list)

    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path = "configs/draft/heroes.yaml") -> HeroDB:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"ไม่พบไฟล์ฮีโร่: {p} — สร้างด้วย rov draft heroes-init"
            )
        with p.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls.model_validate(data)

    def save(self, path: str | Path = "configs/draft/heroes.yaml") -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(
                self.model_dump(mode="json", exclude_none=False),
                fh,
                allow_unicode=True,
                sort_keys=False,
            )

    # ------------------------------------------------------------------

    def get(self, hero_id: str) -> Hero | None:
        for h in self.heroes:
            if h.id == hero_id:
                return h
        return None

    def require(self, hero_id: str) -> Hero:
        h = self.get(hero_id)
        if h is None:
            raise KeyError(f"ไม่รู้จักฮีโร่: {hero_id}")
        return h

    @property
    def complete_heroes(self) -> list[Hero]:
        return [h for h in self.heroes if h.complete]

    @property
    def incomplete_heroes(self) -> list[Hero]:
        return [h for h in self.heroes if not h.complete]

    def completeness(self) -> dict:
        total = len(self.heroes)
        done = len(self.complete_heroes)
        return {
            "total": total,
            "complete": done,
            "incomplete": total - done,
            "fraction": done / total if total else 0.0,
        }

    def todo(self, priority: list[str] | None = None, limit: int = 30) -> list[Hero]:
        """ฮีโร่ที่ยังไม่ได้กรอก เรียงตามลำดับความสำคัญที่ส่งเข้ามา

        priority ควรมาจาก rov.draft.stats.hero_priority_order()
        ซึ่งเรียงตาม pick + ban จริงในระดับ pro
        ฮีโร่ที่ไม่เคยถูกหยิบหรือแบนแทบไม่มีผลต่อ draft engine
        """
        pending = self.incomplete_heroes
        if priority:
            rank = {h: i for i, h in enumerate(priority)}
            pending.sort(key=lambda h: rank.get(h.id, 10**6))
        return pending[:limit]
