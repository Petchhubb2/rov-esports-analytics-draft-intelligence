"""สุ่มเฟรมตาม PTS

กฎเหล็ก: ห้ามคำนวณเวลาจาก frame_index / fps
เพราะคลิปที่ตัดต่อมาอาจเป็น variable frame rate และ ffmpeg บางเวอร์ชัน
รายงาน fps เฉลี่ยไม่ตรงความจริง (ดู docs/04-vision-pipeline.md §2)
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import av
import numpy as np


@dataclass(slots=True)
class SampledFrame:
    frame_idx: int
    pts: float
    video_time: float
    image: np.ndarray  # BGR uint8 (เรียงแบบเดียวกับ OpenCV)


def iter_samples(
    path: str | Path,
    fps: float = 2.0,
    start: float = 0.0,
    end: float | None = None,
    dense_windows: list[tuple[float, float]] | None = None,
    dense_fps: float = 5.0,
) -> Iterator[SampledFrame]:
    """decode ตามลำดับแล้วเลือกเฟรมที่ถึงเวลาเป้าหมาย

    decode ตามลำดับเร็วกว่าการ seek ซ้ำ ๆ มากเมื่อต้องสุ่มหลายพันเฟรม
    และ seek ในไฟล์ที่ compress แบบ inter-frame ก็ไม่แม่นอยู่แล้ว

    dense_windows คือช่วงที่ต้องการสุ่มถี่ขึ้น เช่นรอบเวลาเกิด objective
    """
    interval = 1.0 / fps
    dense_interval = 1.0 / dense_fps
    windows = dense_windows or []

    def in_dense(t: float) -> bool:
        return any(a <= t <= b for a, b in windows)

    with av.open(str(path)) as container:
        st = container.streams.video[0]
        st.thread_type = "AUTO"  # ใช้หลาย thread ในการ decode

        if start > 0:
            # seek หยาบ ๆ ไปใกล้จุดเริ่ม แล้วปล่อยให้ decode ไล่มาเอง
            container.seek(int(start / av.time_base), backward=True)

        next_t = start
        idx = -1
        for frame in container.decode(video=0):
            if frame.pts is None:
                continue
            idx += 1
            t = float(frame.pts * st.time_base)

            if t < start:
                continue
            if end is not None and t > end:
                break
            if t + 1e-9 < next_t:
                continue

            img = frame.to_ndarray(format="bgr24")
            yield SampledFrame(frame_idx=idx, pts=t, video_time=t, image=img)

            step = dense_interval if in_dense(t) else interval
            # ตั้งเป้าถัดไปจากเวลาจริงของเฟรมนี้ ไม่ใช่จากเป้าเดิม
            # ป้องกันการสะสมความคลาดเคลื่อนเมื่อเฟรมมาไม่ตรงเวลา
            next_t = t + step


def read_frames_at(path: str | Path, times: list[float]) -> list[SampledFrame]:
    """ดึงเฟรมที่เวลาที่ระบุ — ใช้ตอน calibrate และ debug ไม่ใช่ตอนประมวลผลจริง"""
    if not times:
        return []
    wanted = sorted(times)
    out: list[SampledFrame] = []
    i = 0

    with av.open(str(path)) as container:
        st = container.streams.video[0]
        st.thread_type = "AUTO"
        idx = -1
        for frame in container.decode(video=0):
            if frame.pts is None:
                continue
            idx += 1
            t = float(frame.pts * st.time_base)
            while i < len(wanted) and t >= wanted[i]:
                out.append(
                    SampledFrame(
                        frame_idx=idx,
                        pts=t,
                        video_time=t,
                        image=frame.to_ndarray(format="bgr24"),
                    )
                )
                i += 1
            if i >= len(wanted):
                break
    return out


def spread_times(duration: float, n: int, skip_head: float = 0.05) -> list[float]:
    """เวลาที่กระจายทั่วคลิป สำหรับสร้าง background model และ calibrate

    ข้ามช่วงต้นคลิปตามสัดส่วน skip_head เพราะมักเป็น intro หรือหน้า draft
    """
    if n <= 0 or duration <= 0:
        return []
    lo = duration * skip_head
    hi = duration * 0.98
    if hi <= lo:
        lo, hi = 0.0, duration
    return list(np.linspace(lo, hi, n))
