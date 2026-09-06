"""Zone map — polygon ในพิกัด normalized + raster lookup แบบ O(1)

ดู docs/04-vision-pipeline.md §6

การทดสอบ point-in-polygon ทีละจุดช้าเกินไปที่ระดับข้อมูลหลักล้านแถว
จึง rasterize ครั้งเดียวตอนโหลด แล้ว lookup ด้วยการ index array
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
import yaml
from pydantic import BaseModel, Field, field_validator

ZoneKind = Literal["lane", "jungle", "river", "objective", "approach", "base"]

# ความละเอียดของ raster — 512x512 ให้ความละเอียดราว 0.002 normalized
# ซึ่งละเอียดกว่าความแม่นของ detector (เป้าหมาย 0.008) หลายเท่า
RASTER_SIZE = 512

NO_ZONE = 0  # index 0 สงวนไว้สำหรับ "ไม่อยู่ใน zone ใดเลย"


class ZoneDef(BaseModel):
    id: str
    kind: ZoneKind
    polygon: list[tuple[float, float]] = Field(min_length=3)
    parent: str | None = None
    # macro region ใช้ตัดสินว่าการย้าย zone นับเป็น rotation หรือไม่
    # การเดินภายใน region เดียวกันไม่ใช่ rotation
    region: str | None = None

    @field_validator("polygon")
    @classmethod
    def _check_bounds(cls, v: list[tuple[float, float]]) -> list[tuple[float, float]]:
        for x, y in v:
            if not (-0.05 <= x <= 1.05 and -0.05 <= y <= 1.05):
                raise ValueError(
                    f"จุด ({x}, {y}) อยู่นอกพิกัด normalized — polygon ต้องอยู่ในช่วง 0..1"
                )
        return v


class ZoneMap(BaseModel):
    version: int
    zones: list[ZoneDef]

    _raster: np.ndarray | None = None
    _names: list[str] | None = None
    _dist: np.ndarray | None = None

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def load(cls, path: str | Path) -> ZoneMap:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"ไม่พบไฟล์ zone: {p}")
        with p.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        obj = cls.model_validate(data)
        obj.build()
        return obj

    # ------------------------------------------------------------------

    def build(self) -> None:
        """rasterize polygon ทั้งหมดเป็นภาพ label + ระยะถึงขอบ zone

        เรียกครั้งเดียวตอนโหลด ผลลัพธ์ cache ไว้ในอ็อบเจกต์
        """
        import cv2

        names = [""] + [z.id for z in self.zones]
        raster = np.zeros((RASTER_SIZE, RASTER_SIZE), dtype=np.uint16)

        # วาดตามลำดับในไฟล์ zone ที่อยู่ท้ายทับ zone ที่อยู่ต้น
        # จึงควรเรียง zone กว้าง (lane) ไว้ต้น และ zone แคบ (objective) ไว้ท้าย
        for idx, z in enumerate(self.zones, start=1):
            pts = np.array(
                [[round(x * (RASTER_SIZE - 1)), round(y * (RASTER_SIZE - 1))] for x, y in z.polygon],
                dtype=np.int32,
            )
            cv2.fillPoly(raster, [pts], color=int(idx))

        # ระยะจากแต่ละ pixel ถึงขอบของ zone ที่ตัวเองอยู่
        # ใช้ทำ margin ใน hysteresis เพื่อไม่ให้ zone กระพริบตอนเดินเลียบขอบ
        dist = np.zeros((RASTER_SIZE, RASTER_SIZE), dtype=np.float32)
        for idx in range(1, len(names)):
            mask = (raster == idx).astype(np.uint8)
            if not mask.any():
                continue
            d = cv2.distanceTransform(mask, cv2.DIST_L2, 3)
            dist = np.maximum(dist, d)
        dist /= RASTER_SIZE  # แปลงเป็นหน่วย normalized

        self._raster = raster
        self._names = names
        self._dist = dist

    # ------------------------------------------------------------------

    def _ensure_built(self) -> None:
        if self._raster is None:
            self.build()

    def zone_at(self, x: float, y: float) -> str | None:
        """lookup O(1) — คืน None เมื่ออยู่นอกทุก zone"""
        self._ensure_built()
        assert self._raster is not None and self._names is not None
        if not (0.0 <= x < 1.0 and 0.0 <= y < 1.0):
            return None
        ix = int(x * (RASTER_SIZE - 1))
        iy = int(y * (RASTER_SIZE - 1))
        idx = int(self._raster[iy, ix])
        return self._names[idx] if idx != NO_ZONE else None

    def edge_distance(self, x: float, y: float) -> float:
        """ระยะถึงขอบ zone ในหน่วย normalized — 0 เมื่ออยู่นอก zone"""
        self._ensure_built()
        assert self._dist is not None
        if not (0.0 <= x < 1.0 and 0.0 <= y < 1.0):
            return 0.0
        ix = int(x * (RASTER_SIZE - 1))
        iy = int(y * (RASTER_SIZE - 1))
        return float(self._dist[iy, ix])

    def zones_at_batch(self, xs: np.ndarray, ys: np.ndarray) -> list[str | None]:
        """lookup แบบเวกเตอร์ สำหรับข้อมูลจำนวนมาก"""
        self._ensure_built()
        assert self._raster is not None and self._names is not None
        valid = (xs >= 0) & (xs < 1) & (ys >= 0) & (ys < 1) & ~np.isnan(xs) & ~np.isnan(ys)
        ix = np.clip((np.nan_to_num(xs) * (RASTER_SIZE - 1)).astype(np.int32), 0, RASTER_SIZE - 1)
        iy = np.clip((np.nan_to_num(ys) * (RASTER_SIZE - 1)).astype(np.int32), 0, RASTER_SIZE - 1)
        idx = self._raster[iy, ix]
        idx = np.where(valid, idx, NO_ZONE)
        return [self._names[i] if i != NO_ZONE else None for i in idx]

    # ------------------------------------------------------------------

    def get(self, zone_id: str) -> ZoneDef | None:
        for z in self.zones:
            if z.id == zone_id:
                return z
        return None

    def region_of(self, zone_id: str | None) -> str | None:
        """macro region ของ zone — ใช้ตัดสินว่าเป็น rotation จริงหรือแค่เดินในพื้นที่เดิม"""
        if zone_id is None:
            return None
        z = self.get(zone_id)
        if z is None:
            return None
        return z.region or z.id

    def coverage_fraction(self) -> float:
        """สัดส่วนของแมพที่ถูก zone ครอบคลุม — ใช้ตรวจว่าวาด polygon ครบหรือยัง"""
        self._ensure_built()
        assert self._raster is not None
        return float((self._raster != NO_ZONE).mean())
