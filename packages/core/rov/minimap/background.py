"""Background model ของ minimap

สิ่งที่วัดได้จริงบนชุดสังเคราะห์ (scripts/eval_synthetic.py)

1. หน้าต่างสั้นทำให้แย่ลง ไม่ใช่ดีขึ้น
   หน้าต่าง 75 วินาที  precision 0.919  recall(ไม่ทับ) 0.926
   หน้าต่างทั้งคลิป     precision 0.972  recall(ไม่ทับ) 0.969
   เพราะฮีโร่ที่อยู่นิ่งนานจะครองเวลาเกินครึ่งของหน้าต่างสั้น
   แล้วถูกนับเป็นพื้นหลังไปเลย ทำให้ detector มองไม่เห็นตัวเอง

   เดิมตั้งหน้าต่างสั้นเพราะกังวลว่าป้อมจางสีลงตลอดเกม
   แต่ป้อมเป็นสี่เหลี่ยมเล็กที่พื้นที่ต่ำกว่าเกณฑ์ขนาด icon
   ตัวกรองขนาดจึงจัดการได้อยู่แล้ว

2. ลองใช้ percentile ของความอิ่มสีแทน median แล้ว "แย่กว่า" ทุก seed
   (precision 0.89 vs 0.96) เพราะการเลือกทีละ pixel จากคนละเฟรม
   ทำให้ภาพพื้นหลังไม่กลมกลืน เกิด noise แล้ว residual สูงขึ้นทั้งภาพ
   อย่ากลับไปลองอีก

ยังคงโครงสร้าง rolling ไว้เผื่อ broadcast ที่เปลี่ยน overlay กลางเกม
แต่ค่าเริ่มต้นควรเป็นหน้าต่างยาว
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(slots=True)
class BackgroundSlice:
    t_center: float
    image: np.ndarray  # BGR uint8


class RollingBackground:
    """เก็บ background หลายช่วงเวลา แล้วเลือกช่วงที่ใกล้ที่สุดตอนใช้งาน

    คำนวณล่วงหน้าเป็นช่วง ๆ แทนการคำนวณใหม่ทุกเฟรม
    ที่หน้าต่าง 75 วินาที และคลิป 20 นาที จะได้ราว 16 ช่วง ซึ่งถูกมาก
    """

    def __init__(self, slices: list[BackgroundSlice]):
        if not slices:
            raise ValueError("ต้องมี background อย่างน้อยหนึ่งช่วง")
        self._slices = sorted(slices, key=lambda s: s.t_center)
        self._times = [s.t_center for s in self._slices]

    def at(self, t: float) -> np.ndarray:
        """background ที่ใกล้เวลา t ที่สุด"""
        i = bisect.bisect_left(self._times, t)
        if i == 0:
            return self._slices[0].image
        if i >= len(self._slices):
            return self._slices[-1].image
        before, after = self._times[i - 1], self._times[i]
        return self._slices[i - 1].image if (t - before) <= (after - t) else self._slices[i].image

    def __len__(self) -> int:
        return len(self._slices)

    @property
    def slices(self) -> list[BackgroundSlice]:
        return list(self._slices)


def build_rolling_background(
    frames: list[tuple[float, np.ndarray]],
    window_sec: float = 600.0,
    max_samples: int = 80,
    method: str = "median",
) -> RollingBackground:
    """สร้าง background เป็นช่วง ๆ จากเฟรมที่สุ่มมาแล้ว

    frames  รายการ (video_time, ภาพ minimap crop)
    window  ความยาวหน้าต่างเป็นวินาที

    median ทนต่อ outlier — hero icon ที่เคลื่อนที่จะถูกกรองออกโดยธรรมชาติ
    เพราะไม่มี icon ตัวใดอยู่พิกัดเดิมเกินครึ่งของหน้าต่าง
    """
    if not frames:
        raise ValueError("ไม่มีเฟรมสำหรับสร้าง background")

    frames = sorted(frames, key=lambda f: f[0])
    t0, t1 = frames[0][0], frames[-1][0]
    span = max(t1 - t0, 1e-6)
    n_windows = max(1, int(math.ceil(span / window_sec)))

    slices: list[BackgroundSlice] = []
    for w in range(n_windows):
        lo = t0 + w * window_sec
        hi = lo + window_sec
        chunk = [img for (t, img) in frames if lo <= t < hi]
        if len(chunk) < 3:
            # หน้าต่างนี้เฟรมน้อยเกินไป ขยายไปเอาเพื่อนบ้าน
            chunk = _nearest_n(frames, (lo + hi) / 2.0, max(8, len(chunk)))
        if not chunk:
            continue
        if len(chunk) > max_samples:
            step = len(chunk) / max_samples
            chunk = [chunk[int(i * step)] for i in range(max_samples)]
        stack = np.stack(chunk).astype(np.uint8)
        slices.append(
            BackgroundSlice(t_center=(lo + hi) / 2.0, image=_reduce(stack, method))
        )

    if not slices:
        stack = np.stack([img for _, img in frames[:max_samples]])
        slices = [BackgroundSlice(t_center=(t0 + t1) / 2.0, image=_reduce(stack, method))]

    return RollingBackground(slices)


def _reduce(stack: np.ndarray, method: str) -> np.ndarray:
    if method == "median":
        return np.median(stack, axis=0).astype(np.uint8)
    raise ValueError(f"วิธีสร้าง background ไม่รู้จัก: {method}")


def _nearest_n(frames: list[tuple[float, np.ndarray]], t: float, n: int) -> list[np.ndarray]:
    ordered = sorted(frames, key=lambda f: abs(f[0] - t))
    return [img for _, img in ordered[:n]]


def residual(frame: np.ndarray, background: np.ndarray) -> np.ndarray:
    """|frame - background| รวมเป็น grayscale

    ใช้ค่าสูงสุดของสามช่อง ไม่ใช่ค่าเฉลี่ย เพราะ icon ที่ต่างจากพื้นหลัง
    เพียงช่องเดียว (เช่น icon แดงบนหญ้าเขียว) ต้องไม่ถูกเฉลี่ยจนหาย
    """
    return cv2.absdiff(frame, background).max(axis=2)
