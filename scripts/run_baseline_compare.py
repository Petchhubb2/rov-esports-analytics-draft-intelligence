"""เทียบ Draft Engine กับ baseline สามแบบ — PHASE M0.5

    python scripts/run_baseline_compare.py
    python scripts/run_baseline_compare.py --drafts 200 --cutoff 2026-05-09

⚠️ **ห้ามใช้ผลจากสคริปต์นี้ปรับน้ำหนัก** (PHASE M0.5 ข้อ 8)
รอบนี้มีไว้ตอบคำถามเดียว: "ระบบปัจจุบันเก่งกว่า baseline จริงหรือไม่"
การ fit น้ำหนักจากชุด evaluation เดียวกันคือการ overfit ที่มองไม่เห็น
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
from rov.draft.recommend import recommend  # noqa: E402
from rov.draft.scouting import date_range  # noqa: E402
from rov.draft.state import DraftFormat  # noqa: E402
from rov.eval.baselines import default_rankers  # noqa: E402
from rov.eval.benchmark import compare_rankers, split_by_time  # noqa: E402
from rov.eval.rankmetrics import significant_difference  # noqa: E402

EVAL_DAYS = 120


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoff", help="วันที่เริ่มชุด evaluation")
    ap.add_argument("--eval-end", help="วันที่สิ้นสุดของชุด evaluation (ไม่รวมวันนี้)")
    ap.add_argument("--legacy", action="store_true", help="เทียบกับ engine ก่อนแก้ ban")
    ap.add_argument("--by-action", action="store_true", help="แสดงเฉพาะตาราง ban/pick")
    ap.add_argument("--drafts", type=int, default=10**6, help="ค่าเริ่มต้น = ทั้งหมด")
    ap.add_argument("--min-games", type=int, default=5)
    args = ap.parse_args()

    regions = _regions()
    if not regions:
        print("ยังไม่มีข้อมูลใน cache — รัน rov draft import ก่อน")
        return 1
    all_series = [s for r in regions for s in r.series]

    lo, hi = date_range(all_series)
    cutoff = (
        date.fromisoformat(args.cutoff) if args.cutoff else hi - timedelta(days=EVAL_DAYS)
    )
    train, ev = split_by_time(all_series, cutoff)
    print(f"ข้อมูล {lo} ถึง {hi} · cutoff {cutoff}")
    print(f"train {len(train)} ซีรีส์ · eval {len(ev)} ซีรีส์\n")
    if not ev:
        print("ชุด evaluation ว่าง")
        return 1

    # ทุกอย่างที่ ranker ใช้ ต้องคำนวณจาก train เท่านั้น
    evidence = slot_evidence(train, _hero_classes())
    lu = (
        {h: {x.value: n for x, n in c.most_common()} for h, c in lane_usage(train).items()}
        if evidence["passes"]
        else {}
    )
    lanes = [x.value for x in SLOT_LANES] if evidence["passes"] else []
    lmu = compute_lane_matchups(train) if evidence["passes"] else {}

    hero_file = Path("configs/draft/heroes.yaml")
    db = HeroDB.load(hero_file) if hero_file.exists() else None

    rankers = default_rankers(recommend, include_legacy=args.legacy)
    cmp_ = compare_rankers(
        train, ev, DraftFormat.load(), rankers,
        lane_usage=lu, lanes=lanes, lane_matchups=lmu, hero_db=db,
        min_games=args.min_games, max_drafts=args.drafts,
    )
    if args.by_action:
        # แสดงเฉพาะตาราง ban/pick ซึ่งเป็นแกนของ M0.75
        print(cmp_.report_for("ประเภทตา"))
    else:
        print(cmp_.report())

    print("\n  ── engine เทียบทีละ baseline (top-1) ──\n")
    engine = cmp_.overall[rankers[0].name]
    for r in rankers[1:]:
        b = cmp_.overall[r.name]
        ea, ba = engine.top1_acc or 0.0, b.top1_acc or 0.0
        verdict = significant_difference(engine, b, "top1_acc")
        arrow = "ชนะ" if ea > ba else ("แพ้" if ea < ba else "เสมอ")
        print(
            f"  vs {r.name:<22} engine {ea:.3f} · baseline {ba:.3f} "
            f"· ต่าง {ea - ba:+.3f} · {arrow} · {verdict}"
        )

    print("\n  ── ข้อจำกัดของแต่ละตัว ──")
    for r in rankers:
        print(f"\n  {r.name}")
        print(f"    {r.description}")
        print(f"    ข้อจำกัด: {r.limitations}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
