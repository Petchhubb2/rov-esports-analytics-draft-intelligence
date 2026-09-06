"""อ่าน metadata ของไฟล์วิดีโอด้วย PyAV

ใช้ PyAV แทน cv2.VideoCapture เพราะเข้าถึง PTS จริงได้
ซึ่งจำเป็นสำหรับ G2 (game clock alignment) และไฟล์ที่เป็น variable frame rate
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path

import av


@dataclass(slots=True)
class VideoMeta:
    path: str
    width: int
    height: int
    fps: float
    duration: float
    n_frames_est: int
    codec: str
    pix_fmt: str | None
    time_base: str
    variable_fps: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def resolution(self) -> tuple[int, int]:
        return (self.width, self.height)

    def summary(self) -> str:
        vfr = " (VFR)" if self.variable_fps else ""
        return (
            f"{self.width}x{self.height} @ {self.fps:.2f}fps{vfr} · "
            f"{self.duration / 60:.1f} นาที · {self.codec}"
        )


def probe(path: str | Path) -> VideoMeta:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์วิดีโอ: {p}")

    with av.open(str(p)) as container:
        if not container.streams.video:
            raise ValueError(f"ไฟล์นี้ไม่มี video stream: {p}")
        st = container.streams.video[0]

        avg = st.average_rate
        base = st.base_rate
        fps = float(avg) if avg else (float(base) if base else 0.0)

        # average_rate ต่างจาก base_rate อย่างมีนัยสำคัญ = variable frame rate
        # ต้องรู้ เพราะการคำนวณเวลาจาก frame_index จะผิด
        vfr = bool(avg and base and abs(float(avg) - float(base)) > 0.01)

        duration = 0.0
        if st.duration is not None and st.time_base:
            duration = float(st.duration * st.time_base)
        elif container.duration is not None:
            duration = container.duration / av.time_base

        n_frames = st.frames or (int(duration * fps) if fps else 0)

        tb: Fraction | None = st.time_base
        return VideoMeta(
            path=str(p.resolve()),
            width=st.codec_context.width,
            height=st.codec_context.height,
            fps=fps,
            duration=duration,
            n_frames_est=n_frames,
            codec=st.codec_context.name,
            pix_fmt=st.codec_context.pix_fmt,
            time_base=str(tb) if tb else "",
            variable_fps=vfr,
        )
