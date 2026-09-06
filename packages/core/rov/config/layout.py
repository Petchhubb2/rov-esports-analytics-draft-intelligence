"""Layout config — ผลลัพธ์ของ Phase 0

หนึ่งไฟล์ต่อหนึ่ง broadcast layout เพราะแต่ละรายการแข่งวาง UI ไม่เหมือนกัน
ดู docs/04-vision-pipeline.md §1.4
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from rov.domain.geometry import Rect


class RectModel(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    w: int = Field(gt=0)
    h: int = Field(gt=0)

    def to_rect(self) -> Rect:
        return Rect(self.x, self.y, self.w, self.h)


class TeamColor(BaseModel):
    """ช่วงสีของวงแหวนรอบ hero icon ใน HSV

    hue ใช้สเกลของ OpenCV คือ 0-179 ไม่ใช่ 0-359
    """

    hue: tuple[int, int]
    sat_min: int = Field(ge=0, le=255, default=90)
    val_min: int = Field(ge=0, le=255, default=70)

    @field_validator("hue")
    @classmethod
    def _check_hue(cls, v: tuple[int, int]) -> tuple[int, int]:
        lo, hi = v
        if not (0 <= lo <= 179 and 0 <= hi <= 179):
            raise ValueError("hue ต้องอยู่ในช่วง 0-179 (สเกลของ OpenCV ไม่ใช่ 0-359)")
        return v

    @property
    def wraps(self) -> bool:
        """ช่วงสีแดงคร่อมจุด 0 เช่น (170, 10) ต้องใช้สอง mask รวมกัน"""
        return self.hue[0] > self.hue[1]


class IconSpec(BaseModel):
    diameter_px: tuple[int, int]
    ring_thickness_px: int = 2

    @property
    def radius_range(self) -> tuple[float, float]:
        return (self.diameter_px[0] / 2.0, self.diameter_px[1] / 2.0)

    @property
    def area_range(self) -> tuple[float, float]:
        import math

        r0, r1 = self.radius_range
        # เผื่อขอบ เพราะ icon ไม่ได้กลมสมบูรณ์และ morphology ทำให้ขนาดเพี้ยน
        return (math.pi * r0 * r0 * 0.55, math.pi * r1 * r1 * 1.45)

    @property
    def nominal_area(self) -> float:
        """พื้นที่ของ icon เดี่ยวโดยประมาณ

        ใช้ประเมินว่า blob หนึ่งก้อนมี icon กี่ตัวทับกันอยู่
        ต่างจาก area_range ที่เป็นขอบเขตการยอมรับ ซึ่งกว้างเกินกว่าจะใช้นับจำนวน
        """
        import math

        r0, r1 = self.radius_range
        r = (r0 + r1) / 2.0
        return math.pi * r * r


class ObjectiveMarks(BaseModel):
    """ตำแหน่ง mark ของ objective บน minimap

    เหลือง = มีชีวิต, เทา = เพิ่งถูกฆ่า (ดู docs/08-game-reference.md §4)
    ตัวนี้ให้ OBJECTIVE_TAKEN event โดยไม่ต้องแตะ main view เลย
    """

    dragon: RectModel | None = None
    slayer: RectModel | None = None
    sat_alive_min: int = 80


class MinimapConfig(BaseModel):
    roi: RectModel
    transform: Literal["affine", "homography"] = "affine"
    # G1 — คำถามที่บล็อกการออกแบบ tracking ทั้งหมด
    # None แปลว่ายังไม่ได้ตรวจ ต้องเปิดคลิปจริงแล้วนับ icon
    fog_of_war: bool | None = None
    # สีของ icon สื่อถึงฝ่าย หรือ มิตร/ศัตรู
    color_semantics: Literal["side", "ally_enemy"] | None = None
    icon: IconSpec
    teams: dict[str, TeamColor]
    objective_marks: ObjectiveMarks = Field(default_factory=ObjectiveMarks)
    tower_positions: list[RectModel] = Field(default_factory=list)
    # จุดอ้างอิง 4 จุดสำหรับ homography (ใช้เมื่อ transform == homography)
    homography_src: list[tuple[float, float]] | None = None
    homography_dst: list[tuple[float, float]] | None = None

    @model_validator(mode="after")
    def _check_homography(self) -> MinimapConfig:
        if self.transform == "homography":
            if not self.homography_src or not self.homography_dst:
                raise ValueError("transform=homography ต้องระบุ homography_src และ homography_dst")
            if len(self.homography_src) != 4 or len(self.homography_dst) != 4:
                raise ValueError("homography ต้องมีจุดอ้างอิงฝั่งละ 4 จุดพอดี")
        return self

    @model_validator(mode="after")
    def _check_teams(self) -> MinimapConfig:
        missing = {"blue", "red"} - set(self.teams)
        if missing:
            raise ValueError(f"teams ขาดสี: {sorted(missing)}")
        return self


class ClockConfig(BaseModel):
    roi: RectModel
    format: str = "MM:SS"


class HudSide(BaseModel):
    x: int
    y: int
    w: int
    h: int
    slots: int = 5

    def slot_rect(self, i: int) -> Rect:
        """ROI ของช่องที่ i โดยแบ่งความสูงเท่า ๆ กัน"""
        if not 0 <= i < self.slots:
            raise IndexError(f"slot {i} อยู่นอกช่วง 0-{self.slots - 1}")
        sh = self.h // self.slots
        return Rect(self.x, self.y + i * sh, self.w, sh)


class HudConfig(BaseModel):
    left: HudSide
    right: HudSide
    portrait_size_px: int = 48
    dead_indicator: Literal["grayscale", "countdown", "both"] = "grayscale"


class ReplayConfig(BaseModel):
    banner_roi: RectModel | None = None
    detect_by: list[str] = Field(
        default_factory=lambda: ["clock_regression", "minimap_missing"]
    )


class Layout(BaseModel):
    """ไฟล์ configs/layouts/<id>.yaml"""

    id: str
    source_resolution: tuple[int, int]
    verified_on: str | None = None
    verified_by: str | None = None
    minimap: MinimapConfig
    clock: ClockConfig | None = None
    hud: HudConfig | None = None
    scoreboard: RectModel | None = None
    replay: ReplayConfig = Field(default_factory=ReplayConfig)

    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path) -> Layout:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"ไม่พบไฟล์ layout: {p}")
        with p.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return cls.model_validate(data)

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(
                self.model_dump(mode="json"), fh, allow_unicode=True, sort_keys=False
            )

    def scaled_to(self, width: int, height: int) -> Layout:
        """ปรับ ROI ทั้งหมดตามความละเอียดจริงของคลิป

        ใช้เมื่อ layout ทำไว้ที่ 720p แต่คลิปเป็น 1080p
        คืนค่า layout ใหม่ ไม่แก้ตัวเดิม
        """
        sw, sh = self.source_resolution
        if (sw, sh) == (width, height):
            return self
        fx, fy = width / sw, height / sh
        if abs(fx - fy) > 0.01:
            raise ValueError(
                f"อัตราส่วนภาพไม่ตรงกัน layout {sw}x{sh} vs วิดีโอ {width}x{height} — "
                "ต้องทำ layout ใหม่ ปรับสเกลตรง ๆ ไม่ได้"
            )
        data = self.model_dump()
        _scale_rects(data, fx)
        data["source_resolution"] = [width, height]
        return Layout.model_validate(data)

    @property
    def unanswered_phase0(self) -> list[str]:
        """คำถาม Phase 0 ที่ยังไม่มีคำตอบในไฟล์นี้

        ใช้เตือนก่อนรัน pipeline เพราะการเดาคำตอบเหล่านี้
        ทำให้ผลลัพธ์ผิดแบบเงียบ ๆ
        """
        missing: list[str] = []
        if self.minimap.fog_of_war is None:
            missing.append("minimap.fog_of_war (G1 — เปิดคลิปแล้วนับ icon ตอนสองทีมแยกกัน)")
        if self.minimap.color_semantics is None:
            missing.append("minimap.color_semantics (สี = ฝ่าย หรือ มิตร/ศัตรู)")
        if self.clock is None:
            missing.append("clock.roi (G2 — ไม่มี game_clock จะเทียบข้ามแมตช์ไม่ได้)")
        if self.hud is None:
            missing.append("hud (G4 — สถานะตายต้องมาจาก HUD)")
        if self.minimap.objective_marks.dragon is None:
            missing.append("minimap.objective_marks.dragon (ทำให้ตรวจ OBJECTIVE_TAKEN ได้)")
        return missing


# ฟิลด์ที่เป็นขนาดเป็น pixel และต้องปรับสเกลด้วย แม้ไม่ได้อยู่ในรูป rect
_SCALAR_PX_FIELDS = ("portrait_size_px", "ring_thickness_px")
_TUPLE_PX_FIELDS = ("diameter_px",)


def _scale_rects(node: object, f: float) -> None:
    """เดินโครงสร้าง dict แล้วคูณสเกลทุกค่าที่มีหน่วยเป็น pixel"""
    if isinstance(node, dict):
        if {"x", "y", "w", "h"} <= set(node) and all(
            isinstance(node[k], int) for k in ("x", "y", "w", "h")
        ):
            for k in ("x", "y", "w", "h"):
                node[k] = round(node[k] * f)
            return
        for key, v in node.items():
            if key in _SCALAR_PX_FIELDS and isinstance(v, int):
                node[key] = max(1, round(v * f))
            elif key in _TUPLE_PX_FIELDS and isinstance(v, (list, tuple)):
                node[key] = [max(1, round(x * f)) for x in v]
            else:
                _scale_rects(v, f)
    elif isinstance(node, list):
        for v in node:
            _scale_rects(v, f)
