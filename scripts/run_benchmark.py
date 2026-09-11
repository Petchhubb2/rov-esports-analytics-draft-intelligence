"""วัดผล Draft Engine บนดราฟต์จริง — PHASE B · Q8

    python scripts/run_benchmark.py
    python scripts/run_benchmark.py --cutoff 2026-05-09 --drafts 60

แบ่ง train/eval ตามเวลา ไม่ใช่สุ่ม เพราะเมตาเปลี่ยนตามเวลา
ดูเหตุผลเต็มใน rov/eval/benchmark.py และ docs/20 §11
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "core"))

from rov.cli.console import setup_console  # noqa: E402
from rov.cli.main import _hero_classes, _regions  # noqa: E402
from rov.draft.heroes import HeroDB  # noqa: E402
from rov.draft.lanes import (  # noqa: E402
    SLOT_LANES,
    compute_lane_matchups,
    lane_usage,
    slot_evidence,
)
from rov.draft.recommend import EXTRA_WEIGHTS, recommend  # noqa: E402
from rov.draft.scouting import date_range  # noqa: E402
from rov.draft.state import DraftFormat  # noqa: E402
from rov.eval import benchmark  # noqa: E402

# ช่วง evaluation ย้อนจากแมตช์ล่าสุดที่แข่งจริง ไม่ใช่จากวันนี้
EVAL_DAYS = 120


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoff", help="วันที่เริ่มชุด evaluation เช่น 2026-05-09")
    ap.add_argument("--drafts", type=int, default=60, help="จำนวนดราฟต์ที่ทดสอบ")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument(
        "--weights", help='เปิดน้ำหนักชั่วคราว เช่น composition=0.5,lane_counter=0.3'
    )
    args = ap.parse_args()

    regions = _regions()
    if not regions:
        print("ยังไม่มีข้อมูลใน cache — รัน rov draft import ก่อน")
        return 1
    all_series = [s for r in regions for s in r.series]

    lo, hi = date_range(all_series)
    cutoff = (
        date.fromisoformat(args.cutoff)
        if args.cutoff
        else (hi - timedelta(days=EVAL_DAYS))
    )
    train, ev = benchmark.split_by_time(all_series, cutoff)
    print(f"ข้อมูลทั้งหมด {lo} ถึง {hi}")
    print(f"cutoff {cutoff} · train {len(train)} ซีรีส์ · eval {len(ev)} ซีรีส์\n")
    if not ev:
        print("ชุด evaluation ว่าง — ลองเลื่อน --cutoff ให้เก่ากว่านี้")
        return 1

    # ข้อมูลเลนคำนวณจาก train เท่านั้น เหมือนสถิติอื่น ๆ
    evidence = slot_evidence(train, _hero_classes())
    lu = (
        {h: {ln.value: n for ln, n in c.most_common()} for h, c in lane_usage(train).items()}
        if evidence["passes"]
        else {}
    )
    lanes = [ln.value for ln in SLOT_LANES] if evidence["passes"] else []
    lmu = compute_lane_matchups(train) if evidence["passes"] else {}

    hero_file = Path("configs/draft/heroes.yaml")
    db = HeroDB.load(hero_file) if hero_file.exists() else None

    extra = dict(EXTRA_WEIGHTS)
    if args.weights:
        for part in args.weights.split(","):
            k, _, v = part.partition("=")
            extra[k.strip()] = float(v)
        print(f"⚠ เปิดน้ำหนักชั่วคราว: {args.weights}\n")

    def rec(*a, **kw):
        return recommend(*a, extra_weights=extra, **kw)

    bm = benchmark.run(
        train, ev, DraftFormat.load(), rec,
        lane_usage=lu, lanes=lanes, lane_matchups=lmu, hero_db=db,
        top_k=args.top_k, max_drafts=args.drafts,
    )
    if args.weights:
        bm.notes.append(f"เปิดน้ำหนัก {args.weights} — ไม่ใช่ค่าเริ่มต้นของระบบ")
    print(bm.report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
