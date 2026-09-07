"""Phase 0 — หาตำแหน่ง minimap และ HUD จากคลิปจริง

วิธีที่ออกแบบไว้ใน docs/04-vision-pipeline.md §1.2

    บริเวณ main view    ค่าเบี่ยงเบนมาตรฐานข้ามเฟรมสูงมาก เพราะกล้องเคลื่อน
    บริเวณ minimap      ต่ำกว่า เพราะพื้นหลังนิ่ง มีแค่ icon ขยับ
    บริเวณ HUD คงที่    ต่ำที่สุด

จึงหา minimap ได้จากการมองหาสี่เหลี่ยมจัตุรัสที่ SD ต่ำ ในมุมที่คาดหวัง

**ผลลัพธ์เป็นข้อเสนอ ไม่ใช่คำตอบสุดท้าย** ต้องให้คนดูภาพยืนยันเสมอ
การเดา ROI ผิดทำให้ทุกอย่างหลังจากนั้นผิดตามแบบเงียบ ๆ
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from rov.domain.geometry import Rect
from rov.ingest.probe import VideoMeta, probe
from rov.ingest.sampler import read_frames_at, spread_times


@dataclass(slots=True)
class Candidate:
    rect: Rect
    mean_sd: float
    squareness: float
    score: float

    @property
    def summary(self) -> str:
        return (
            f"x={self.rect.x} y={self.rect.y} w={self.rect.w} h={self.rect.h} "
            f"· SD {self.mean_sd:.1f} · จัตุรัส {self.squareness:.2f} "
            f"· คะแนน {self.score:.3f}"
        )


@dataclass
class CalibrationScan:
    meta: VideoMeta
    frames: list[np.ndarray]
    sd_map: np.ndarray
    candidates: list[Candidate]

    def report(self) -> str:
        lines = [
            "═══ สแกนหา minimap ═══",
            f"คลิป      {self.meta.summary()}",
            f"เฟรมที่ใช้ {len(self.frames)}",
            f"SD ทั้งภาพ ต่ำสุด {self.sd_map.min():.1f} · "
            f"กลาง {np.median(self.sd_map):.1f} · สูงสุด {self.sd_map.max():.1f}",
            "",
            "ผู้สมัครที่เป็นไปได้ (เรียงตามคะแนน)",
        ]
        if not self.candidates:
            lines.append("  ไม่พบบริเวณที่เข้าเกณฑ์ — ลองเพิ่มจำนวนเฟรมหรือปรับ threshold")
        for i, c in enumerate(self.candidates, 1):
            lines.append(f"  {i}. {c.summary}")
        lines += [
            "",
            "⚠ ตัวเลขเหล่านี้เป็นข้อเสนอ ต้องเปิดภาพ overlay ดูด้วยตาก่อนใช้",
        ]
        return "\n".join(lines)


def sd_map(frames: list[np.ndarray]) -> np.ndarray:
    """ค่าเบี่ยงเบนมาตรฐานต่อ pixel ข้ามเฟรม"""
    stack = np.stack([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]).astype(np.float32)
    return stack.std(axis=0)


def find_minimap(
    sd: np.ndarray,
    min_side_frac: float = 0.10,
    max_side_frac: float = 0.32,
    limit: int = 5,
) -> list[Candidate]:
    """หาสี่เหลี่ยมที่ SD ต่ำและมีสัดส่วนใกล้จัตุรัส

    minimap มักอยู่มุมบนซ้ายหรือบนขวา แต่ไม่ล็อกไว้
    เพราะแต่ละ broadcast วาง UI ไม่เหมือนกัน
    """
    h, w = sd.shape
    # ทำให้เรียบก่อน กัน noise ระดับ pixel
    smooth = cv2.GaussianBlur(sd, (0, 0), 3)
    thr = float(np.percentile(smooth, 35))
    quiet = (smooth < thr).astype(np.uint8)

    # ปิดรูเล็ก ๆ ที่เกิดจาก icon ขยับ
    k = np.ones((9, 9), np.uint8)
    quiet = cv2.morphologyEx(quiet, cv2.MORPH_CLOSE, k)
    quiet = cv2.morphologyEx(quiet, cv2.MORPH_OPEN, k)

    n, _, stats, _ = cv2.connectedComponentsWithStats(quiet, connectivity=8)
    lo, hi = min_side_frac * min(h, w), max_side_frac * min(h, w)

    out: list[Candidate] = []
    for i in range(1, n):
        x, y, cw, ch, area = stats[i]
        if not (lo <= cw <= hi and lo <= ch <= hi):
            continue
        squareness = min(cw, ch) / max(cw, ch)
        if squareness < 0.75:
            continue
        fill = area / (cw * ch)
        if fill < 0.55:
            continue
        region = smooth[y : y + ch, x : x + cw]
        mean_sd = float(region.mean())
        # อยากได้ SD ต่ำ รูปใกล้จัตุรัส และเต็มกรอบ
        score = squareness * fill / (1.0 + mean_sd / 10.0)
        out.append(Candidate(Rect(int(x), int(y), int(cw), int(ch)), mean_sd, squareness, score))

    out.sort(key=lambda c: c.score, reverse=True)
    return out[:limit]


def scan(path: str | Path, n_frames: int = 40) -> CalibrationScan:
    """สุ่มเฟรมจากทั้งคลิป แล้ววิเคราะห์หา minimap"""
    meta = probe(path)
    times = spread_times(meta.duration, n_frames)
    sampled = read_frames_at(path, times)
    if len(sampled) < 5:
        raise ValueError(f"ดึงเฟรมได้แค่ {len(sampled)} เฟรม ไม่พอสำหรับวิเคราะห์")
    frames = [s.image for s in sampled]
    sd = sd_map(frames)
    return CalibrationScan(meta=meta, frames=frames, sd_map=sd, candidates=find_minimap(sd))


# ---------------------------------------------------------------- ภาพผลลัพธ์


def write_inspection(
    scan_result: CalibrationScan,
    out_dir: str | Path,
    n_full: int = 6,
    zoom: int = 4,
) -> list[Path]:
    """เขียนภาพให้คนดู — นี่คือสิ่งที่ตัดสิน Phase 0 จริง ๆ

    ออกมาสามชุด
        frame_*.png     เฟรมเต็ม
        sdmap.png       แผนที่ความแปรปรวน ใช้ดูว่าอะไรนิ่งอะไรขยับ
        minimap_*.png   บริเวณที่สงสัยว่าเป็น minimap ขยายให้เห็นชัด
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    step = max(1, len(scan_result.frames) // n_full)
    for i, frame in enumerate(scan_result.frames[::step][:n_full]):
        img = frame.copy()
        for j, c in enumerate(scan_result.candidates):
            col = (0, 255, 0) if j == 0 else (0, 165, 255)
            r = c.rect
            cv2.rectangle(img, (r.x, r.y), (r.x2, r.y2), col, 2)
            cv2.putText(img, f"#{j + 1}", (r.x, max(14, r.y - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)
        p = out / f"frame_{i:02d}.png"
        cv2.imwrite(str(p), img)
        written.append(p)

    sd = scan_result.sd_map
    norm = cv2.normalize(sd, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    p = out / "sdmap.png"
    cv2.imwrite(str(p), cv2.applyColorMap(norm, cv2.COLORMAP_INFERNO))
    written.append(p)

    mid = scan_result.frames[len(scan_result.frames) // 2]
    for j, c in enumerate(scan_result.candidates[:3]):
        crop = c.rect.crop(mid)
        if crop.size == 0:
            continue
        big = cv2.resize(crop, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_NEAREST)
        p = out / f"minimap_{j + 1}.png"
        cv2.imwrite(str(p), big)
        written.append(p)

    return written


def write_frames(
    path: str | Path,
    out_dir: str | Path,
    times: list[float] | None = None,
    n: int = 8,
    crop: Rect | None = None,
    zoom: int = 1,
) -> list[Path]:
    """ตัดเฟรมออกมาเป็นภาพ ตามเวลาที่ระบุหรือกระจายทั้งคลิป"""
    meta = probe(path)
    if times is None:
        times = spread_times(meta.duration, n)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for s in read_frames_at(path, times):
        img = crop.crop(s.image) if crop else s.image
        if zoom > 1:
            img = cv2.resize(img, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_NEAREST)
        p = out / f"t{s.video_time:08.2f}.png"
        cv2.imwrite(str(p), img)
        written.append(p)
    return written
