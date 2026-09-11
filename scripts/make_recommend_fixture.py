"""สร้าง regression fixture ของ Draft Engine จากข้อมูลแมตช์จริง

    python scripts/make_recommend_fixture.py            ดูว่าจะได้อะไร
    python scripts/make_recommend_fixture.py --write    เขียนไฟล์

⚠️ **รันใหม่เมื่อไร**

รันใหม่ได้เฉพาะเมื่อ (ก) ดึงข้อมูลแมตช์เพิ่ม หรือ (ข) ตั้งใจเปลี่ยน behavior
แล้วยืนยันว่าผลใหม่ถูกต้อง **ห้ามรันใหม่เพื่อให้เทสต์ที่ fail กลับมาผ่าน** —
นั่นคือการลบหลักฐานว่าพฤติกรรมเปลี่ยน ซึ่งเป็นสิ่งเดียวที่ fixture นี้มีไว้จับ
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "core"))

from rov.cli.console import setup_console  # noqa: E402
from rov.cli.main import _regions  # noqa: E402
from rov.draft.lanes import SLOT_LANES, lane_usage, slot_evidence  # noqa: E402
from rov.draft.meta import pool  # noqa: E402
from rov.draft.recommend import recommend  # noqa: E402
from rov.draft.state import DraftFormat  # noqa: E402
from rov.eval.draftbench import (  # noqa: E402
    pick_drafts,
    pooled_to_dict,
    replay_draft,
    save_fixture,
)

OUT = Path("tests/fixtures/recommend_regression.json")

# 12 ดราฟต์ × 18 ตา = 216 ตา ซึ่งพอจะจับการเปลี่ยนแปลงได้ทุกเฟส
# และยังทำให้เทสต์รันจบในไม่กี่วินาที
N_DRAFTS = 12
TOP_K = 5


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--drafts", type=int, default=N_DRAFTS)
    args = ap.parse_args()

    regions = _regions()
    if not regions:
        print("ยังไม่มีข้อมูลใน cache — รัน rov draft import ก่อน")
        return 1

    all_series = [s for r in regions for s in r.series]
    pooled = pool(regions)

    classes = {h.id: [c.value for c in h.hero_class] for h in _hero_db()}
    evidence = slot_evidence(all_series, classes)
    if not evidence["passes"]:
        print("⚠️ หลักฐานช่อง-เลนไม่ผ่านเกณฑ์ — fixture จะไม่มีข้อมูลเลน")
    lu = (
        {
            hero: {ln.value: n for ln, n in cnt.most_common()}
            for hero, cnt in lane_usage(all_series).items()
        }
        if evidence["passes"]
        else {}
    )
    lanes = [ln.value for ln in SLOT_LANES] if evidence["passes"] else []

    drafts = pick_drafts(all_series, args.drafts)
    fmt = DraftFormat.load()

    fixture = {
        "note": (
            "regression fixture ของ Draft Engine — สร้างจากแมตช์จริง "
            "ห้ามสร้างใหม่เพื่อให้เทสต์ที่ fail กลับมาผ่าน"
        ),
        "top_k": TOP_K,
        "lanes": lanes,
        "pool": pooled_to_dict(pooled, lu),
        "drafts": drafts,
        "expected": {},
    }

    turns = 0
    for d in drafts:
        for t in replay_draft(d, fmt, pooled, lu, lanes, recommend, top_k=TOP_K):
            fixture["expected"][t.key] = t.top
            turns += 1

    print(f"ดราฟต์ {len(drafts)} เกม · {turns} ตา")
    print(f"ฮีโร่ {len(fixture['pool']['heroes'])} ตัว · "
          f"matchup {len(fixture['pool']['matchups'])} คู่ · "
          f"synergy {len(fixture['pool']['synergies'])} คู่")
    empty = [k for k, v in fixture["expected"].items() if not v]
    if empty:
        print(f"⚠️ มี {len(empty)} ตาที่ไม่มีคำแนะนำเลย")

    if args.write:
        save_fixture(OUT, fixture)
        print(f"\nเขียน {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")
    else:
        print("\nยังไม่ได้เขียน — ใส่ --write")
    return 0


def _hero_db():
    from rov.draft.heroes import HeroDB

    p = Path("configs/draft/heroes.yaml")
    return HeroDB.load(p).heroes if p.exists() else []


if __name__ == "__main__":
    raise SystemExit(main())
