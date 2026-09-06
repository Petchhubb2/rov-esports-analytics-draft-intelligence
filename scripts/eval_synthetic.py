"""รัน detector บน minimap สังเคราะห์แล้ววัดผล

ใช้เป็นสนามทดสอบระหว่างรอคลิปจริง — ตรวจว่า "อัลกอริทึมถูก"
ไม่ใช่ตรวจว่า "พารามิเตอร์ถูกสำหรับคลิปจริง"

    python scripts/eval_synthetic.py
    python scripts/eval_synthetic.py --duration 300 --residual 24 --upscale 3
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "core"))

from rov.cli.console import setup_console  # noqa: E402
from rov.config.layout import IconSpec, MinimapConfig, RectModel, TeamColor  # noqa: E402
from rov.config.params import DetectParams  # noqa: E402
from rov.eval.detection import DetPoint, DetectionMetrics, GTIcon, match_frame  # noqa: E402
from rov.eval.synthetic import ICON_DIAMETER, MINIMAP_SIZE, SyntheticMatch  # noqa: E402
from rov.minimap.background import build_rolling_background  # noqa: E402
from rov.minimap.detect import detect_frame, enforce_team_caps  # noqa: E402


def synthetic_layout() -> MinimapConfig:
    """MinimapConfig ที่ตรงกับสีที่ตัวกำเนิดสังเคราะห์ใช้

    ค่าสีมาจาก _C_BLUE_RING = BGR(232,148,40) และ _C_RED_RING = BGR(48,52,226)
    แปลงเป็น HSV แล้วเผื่อช่วง
    """
    return MinimapConfig(
        roi=RectModel(x=0, y=0, w=MINIMAP_SIZE, h=MINIMAP_SIZE),
        transform="affine",
        fog_of_war=False,
        color_semantics="side",
        icon=IconSpec(diameter_px=(ICON_DIAMETER - 3, ICON_DIAMETER + 4), ring_thickness_px=2),
        teams={
            "blue": TeamColor(hue=(95, 120), sat_min=110, val_min=80),
            "red": TeamColor(hue=(175, 8), sat_min=110, val_min=80),
        },
    )


def run_eval(
    duration: float = 240.0,
    fps: float = 2.0,
    seed: int = 0,
    params: DetectParams | None = None,
    dump_dir: Path | None = None,
    quiet: bool = False,
):
    """รัน detector บนชุดสังเคราะห์แล้วคืน DetectionMetrics"""
    params = params or DetectParams()
    cfg = synthetic_layout()

    def say(msg: str) -> None:
        if not quiet:
            print(msg)

    say(f"สร้างเฟรมสังเคราะห์ {duration:.0f} วินาที ที่ {fps} fps ...")
    t0 = time.perf_counter()
    match = SyntheticMatch(duration=duration, fps=fps, seed=seed)
    frames = match.frames()
    say(f"  ได้ {len(frames)} เฟรม ใน {time.perf_counter() - t0:.1f} วินาที")

    say(f"สร้าง background (หน้าต่าง {params.bg_window_sec:.0f} วินาที) ...")
    bg = build_rolling_background(
        [(f.video_time, f.image) for f in frames],
        window_sec=params.bg_window_sec,
        max_samples=params.bg_samples,
    )
    say(f"  ได้ {len(bg)} ช่วง")

    say("ตรวจจับ ...")
    t0 = time.perf_counter()
    metrics = DetectionMetrics()
    if dump_dir:
        dump_dir.mkdir(parents=True, exist_ok=True)

    for f in frames:
        dets, _ = detect_frame(
            f.image, bg.at(f.video_time), cfg, params,
            frame_idx=f.frame_idx, keep_patches=False,
        )
        dets = enforce_team_caps(dets, params.max_per_team)
        gt = [GTIcon(point=i.point, team=i.team, occluded=i.occluded, slot=i.slot)
              for i in f.truth]
        pred = [DetPoint(point=d.point, team=d.team_hint, conf=d.det_conf) for d in dets]
        match_frame(gt, pred, max_dist=0.02, metrics=metrics)
        if dump_dir and f.frame_idx % 40 == 0:
            _dump(dump_dir, f, dets)

    elapsed = time.perf_counter() - t0
    say(f"  เสร็จใน {elapsed:.1f} วินาที "
        f"({len(frames) / max(elapsed, 1e-9):.0f} เฟรม/วินาที)\n")
    return metrics


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=600.0)
    ap.add_argument("--fps", type=float, default=2.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--residual", type=int, default=None)
    ap.add_argument("--upscale", type=int, default=None)
    ap.add_argument("--circularity", type=float, default=None)
    ap.add_argument("--bg-window", type=float, default=None)
    ap.add_argument("--single-bg", action="store_true",
                    help="ใช้ median ครั้งเดียวทั้งเกม เพื่อเทียบกับ rolling")
    ap.add_argument("--bg-method", type=str, default="median", choices=["median"])
    ap.add_argument("--dump", type=str, default=None, help="เขียนภาพ overlay ลงโฟลเดอร์นี้")
    args = ap.parse_args()

    params = DetectParams()
    if args.residual is not None:
        params.residual_threshold = args.residual
    if args.upscale is not None:
        params.upscale = args.upscale
    if args.circularity is not None:
        params.min_circularity = args.circularity
    if args.bg_window is not None:
        params.bg_window_sec = args.bg_window
    if args.single_bg:
        params.bg_window_sec = 1e9

    metrics = run_eval(
        duration=args.duration,
        fps=args.fps,
        seed=args.seed,
        params=params,
        dump_dir=Path(args.dump) if args.dump else None,
    )
    print(metrics.report())
    return 0 if metrics.passed else 1


def _dump(out_dir: Path, frame, dets) -> None:
    import cv2

    img = cv2.resize(frame.image, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
    s = MINIMAP_SIZE * 3
    for icon in frame.truth:
        cv2.drawMarker(
            img, (int(icon.point.x * s), int(icon.point.y * s)),
            (255, 255, 255), cv2.MARKER_CROSS, 10, 1,
        )
    for d in dets:
        cv2.circle(img, (int(d.point.x * s), int(d.point.y * s)), 12, (0, 255, 0), 1)
    cv2.imwrite(str(out_dir / f"f{frame.frame_idx:05d}.png"), img)


if __name__ == "__main__":
    raise SystemExit(main())
