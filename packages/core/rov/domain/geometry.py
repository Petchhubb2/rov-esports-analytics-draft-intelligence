"""เรขาคณิตในพิกัด normalized 0..1

ทุกตำแหน่งในระบบใช้พิกัด normalized เพื่อรองรับ 720p/1080p/1440p ด้วยโค้ดชุดเดียว
ดู docs/01-assessment.md และแผนเดิม §18
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class Point:
    """จุดในพิกัด normalized 0..1"""

    x: float
    y: float

    def dist(self, other: Point) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass(frozen=True, slots=True)
class Rect:
    """สี่เหลี่ยมในพิกัด pixel — ใช้กับ ROI ในไฟล์ layout"""

    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    def crop(self, img: np.ndarray) -> np.ndarray:
        """ตัดภาพตาม ROI — คืน view ไม่ได้ copy"""
        return img[self.y : self.y2, self.x : self.x2]

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px < self.x2 and self.y <= py < self.y2

    def scaled(self, factor: float) -> Rect:
        """ปรับ ROI ตามอัตราส่วนความละเอียด เช่น 720p -> 1080p ใช้ factor 1.5"""
        return Rect(
            x=round(self.x * factor),
            y=round(self.y * factor),
            w=round(self.w * factor),
            h=round(self.h * factor),
        )


def normalize_point(px: float, py: float, roi: Rect) -> Point:
    """pixel ในเฟรมเต็ม -> normalized 0..1 ภายใน ROI

    ไม่ clamp โดยเจตนา ค่าที่หลุดออกนอก 0..1 แปลว่า detection อยู่นอก minimap
    ซึ่งเป็นสัญญาณว่า calibration ผิด และควรเห็นมัน ไม่ใช่ซ่อนมัน
    """
    return Point(x=(px - roi.x) / roi.w, y=(py - roi.y) / roi.h)


def denormalize_point(p: Point, roi: Rect) -> tuple[float, float]:
    """normalized 0..1 -> pixel ในเฟรมเต็ม"""
    return (roi.x + p.x * roi.w, roi.y + p.y * roi.h)


def circularity(area: float, perimeter: float) -> float:
    """4*pi*A / P^2 — วงกลมสมบูรณ์ได้ 1.0

    ใช้กรอง hero icon (กลม) ออกจาก minion และ marker ที่รูปร่างต่างออกไป
    """
    if perimeter <= 0:
        return 0.0
    return float(4.0 * math.pi * area / (perimeter * perimeter))


def point_in_polygon(x: float, y: float, poly: np.ndarray) -> bool:
    """ray casting — ใช้ตอน rasterize zone เท่านั้น

    ห้ามเรียกใน hot path ที่มีข้อมูลหลักล้านแถว
    ให้ใช้ zone raster lookup แทน (rov.mapping.zones)
    """
    n = len(poly)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            x_cross = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def pairwise_distances(points: list[Point | None]) -> np.ndarray:
    """เมทริกซ์ระยะ NxN — ช่องที่มี None เป็น NaN

    NaN โดยเจตนา เพื่อให้การเผลอเอาไปคำนวณต่อพังเสียงดัง
    แทนที่จะได้ตัวเลขที่ดูสมเหตุสมผลแต่ผิด
    """
    n = len(points)
    out = np.full((n, n), np.nan, dtype=np.float32)
    for i in range(n):
        pi = points[i]
        if pi is None:
            continue
        out[i, i] = 0.0
        for j in range(i + 1, n):
            pj = points[j]
            if pj is None:
                continue
            d = pi.dist(pj)
            out[i, j] = d
            out[j, i] = d
    return out


def centroid(points: list[Point]) -> Point | None:
    if not points:
        return None
    return Point(
        x=sum(p.x for p in points) / len(points),
        y=sum(p.y for p in points) / len(points),
    )
