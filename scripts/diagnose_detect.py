"""วิเคราะห์ว่า detector พลาดตรงไหนและทำไม

ตอบสามคำถาม:
  1. false positive มาจากอะไร (ping / minion / การแยก blob เกินจริง)
  2. icon ที่ตรวจไม่พบ อยู่ในสภาพแบบใด (ทับกันแค่ไหน อยู่บนพื้นอะไร)
  3. enforce_team_caps ทิ้งของจริงไปกี่ตัว
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "core"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_synthetic import synthetic_layout  # noqa: E402
from rov.cli.console import setup_console  # noqa: E402
from rov.config.params import DetectParams  # noqa: E402
from rov.eval.synthetic import SyntheticMatch  # noqa: E402
from rov.minimap.background import build_rolling_background  # noqa: E402
from rov.minimap.detect import detect_frame, enforce_team_caps  # noqa: E402

MAX_D = 0.02


def pair(gt, pred):
    """คืน (คู่ที่จับได้, index ของ gt ที่พลาด, index ของ pred ที่เกิน)"""
    if not gt or not pred:
        return [], list(range(len(gt))), list(range(len(pred)))
    cost = np.full((len(gt), len(pred)), 1e6)
    for i, g in enumerate(gt):
        for j, p in enumerate(pred):
            d = g.point.dist(p.point)
            if d <= MAX_D:
                cost[i, j] = d
    rows, cols = linear_sum_assignment(cost)
    matched = [(i, j) for i, j in zip(rows, cols, strict=True) if cost[i, j] < 1e6]
    mg = {i for i, _ in matched}
    mp = {j for _, j in matched}
    return matched, [i for i in range(len(gt)) if i not in mg], [
        j for j in range(len(pred)) if j not in mp
    ]


def main() -> None:
    setup_console()
    params = DetectParams()
    cfg = synthetic_layout()
    match = SyntheticMatch(duration=200.0, fps=2.0, seed=0)
    frames = match.frames()
    bg = build_rolling_background(
        [(f.video_time, f.image) for f in frames], params.bg_window_sec, params.bg_samples
    )

    caps_lost_tp = 0
    fp_reasons: Counter[str] = Counter()
    miss_by_neighbours: Counter[int] = Counter()
    miss_in_fight = 0
    miss_out_fight = 0
    raw_counts: list[int] = []
    fp_conf: list[float] = []
    tp_conf: list[float] = []

    for f in frames:
        raw, _ = detect_frame(
            f.image, bg.at(f.video_time), cfg, params, f.frame_idx, keep_patches=False
        )
        capped = enforce_team_caps(raw, params.max_per_team)
        raw_counts.append(len(raw))

        # caps ทิ้งของจริงไปกี่ตัว
        dropped = [d for d in raw if d not in capped]
        for d in dropped:
            if any(t.point.dist(d.point) <= MAX_D for t in f.truth):
                caps_lost_tp += 1

        matched, missed, extra = pair(f.truth, capped)
        for _, j in matched:
            tp_conf.append(capped[j].det_conf)

        in_fight = match._in_fight(f.video_time)
        for i in missed:
            g = f.truth[i]
            nb = sum(
                1 for o in f.truth if o.slot != g.slot and o.point.dist(g.point) < 0.077
            )
            miss_by_neighbours[nb] += 1
            if in_fight:
                miss_in_fight += 1
            else:
                miss_out_fight += 1

        for j in extra:
            d = capped[j]
            fp_conf.append(d.det_conf)
            nearest = min((t.point.dist(d.point) for t in f.truth), default=9.9)
            if nearest < 0.05:
                fp_reasons["ใกล้ icon จริง (แยก blob เกินจริง)"] += 1
            elif d.radius < 4:
                fp_reasons["blob เล็ก (minion?)"] += 1
            else:
                fp_reasons["อื่น ๆ"] += 1

    print("═══ วินิจฉัย Detector ═══\n")
    print(f"detection ดิบเฉลี่ยต่อเฟรม   {np.mean(raw_counts):.2f}  (ควรใกล้ 10)")
    print(f"                    สูงสุด   {max(raw_counts)}")
    print(f"caps ทิ้ง true positive ไป   {caps_lost_tp}")
    print()
    print("── สาเหตุของ false positive ──")
    for k, v in fp_reasons.most_common():
        print(f"  {v:5d}  {k}")
    print()
    print("── icon ที่พลาด แยกตามจำนวนเพื่อนบ้านที่ทับ ──")
    for nb in sorted(miss_by_neighbours):
        print(f"  เพื่อนบ้าน {nb} ตัว : {miss_by_neighbours[nb]:5d}")
    print(f"\n  พลาดในช่วง teamfight  {miss_in_fight}")
    print(f"  พลาดนอกช่วง fight     {miss_out_fight}")
    print()
    if tp_conf and fp_conf:
        print("── การกระจายของ det_conf ──")
        print(f"  TP  mean {np.mean(tp_conf):.3f}  p10 {np.percentile(tp_conf, 10):.3f}")
        print(f"  FP  mean {np.mean(fp_conf):.3f}  p90 {np.percentile(fp_conf, 90):.3f}")
        for thr in (0.3, 0.4, 0.5, 0.6):
            keep_tp = sum(1 for c in tp_conf if c >= thr)
            keep_fp = sum(1 for c in fp_conf if c >= thr)
            prec = keep_tp / max(keep_tp + keep_fp, 1)
            print(
                f"  ถ้าตัดที่ conf>={thr:.1f} : เหลือ TP {keep_tp}/{len(tp_conf)} "
                f"FP {keep_fp}/{len(fp_conf)}  precision={prec:.4f}"
            )


if __name__ == "__main__":
    main()
