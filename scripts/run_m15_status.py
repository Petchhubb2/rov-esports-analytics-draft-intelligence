"""สถานะของ engine และความรู้ทั้งหมด — PHASE M1.5

    python scripts/run_m15_status.py

⚠️ **สคริปต์นี้วัดอย่างเดียว ไม่ตัดสินใจอะไร**
ห้ามใช้ผลจากหน้าต่างสะอาดไปเลือก rule ปรับน้ำหนัก หรือจูน threshold
(rov/eval/cleanwindow.py บังคับกติกานี้ไว้ในโค้ดแล้ว)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "core"))

from rov.cli.console import setup_console  # noqa: E402
from rov.cli.main import _regions  # noqa: E402
from rov.draft import knowledgecoverage as kc  # noqa: E402
from rov.draft.counterknowledge import CounterBook, quality_report  # noqa: E402
from rov.draft.heroes import HeroDB  # noqa: E402
from rov.draft.meta import pool  # noqa: E402
from rov.eval import cleanwindow as cw  # noqa: E402
from rov.eval import version  # noqa: E402


def main() -> int:
    setup_console()
    regions = _regions()
    if not regions:
        print("ยังไม่มีข้อมูลใน cache")
        return 1

    print(version.report())

    series = [s for r in regions for s in r.series]
    _seen, window = cw.split_clean(series)
    print()
    print(cw.report(window))

    pooled = pool(regions)
    book = CounterBook.load()
    db = HeroDB.load("configs/draft/heroes.yaml")

    print()
    cov = kc.build(db, pooled.stats, book)
    print(kc.report(cov, top=15))

    print()
    print(quality_report(book))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
