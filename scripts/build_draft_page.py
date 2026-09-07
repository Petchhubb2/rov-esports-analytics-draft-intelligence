"""ฝังข้อมูล JSON ลงใน template แล้วได้หน้าเว็บที่เปิดได้เลย

    python scripts/export_draft_data.py     # สร้างข้อมูลก่อน
    python scripts/build_draft_page.py      # แล้วค่อยฝัง
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "core"))

from rov.cli.console import setup_console  # noqa: E402

TPL = Path("apps/web/draft_board.tpl.html")
DATA = Path("data/exports/draft_data.json")
OUT = Path("data/exports/draft_board.html")


def main() -> int:
    setup_console()
    for p in (TPL, DATA):
        if not p.exists():
            print(f"ไม่พบไฟล์: {p}")
            return 1

    tpl = TPL.read_text(encoding="utf-8")
    # \/ กัน </script> ในข้อมูลไปปิด tag ก่อนเวลา — JSON ยอมรับ escape นี้
    raw = DATA.read_text(encoding="utf-8").replace("</", "<" + chr(92) + "/")
    out = tpl.replace("__DATA__", raw)

    m = re.search(r'id="draft-data">(.*?)</script>', out, re.S)
    if m is None:
        print("ไม่พบช่องใส่ข้อมูลใน template")
        return 1
    d = json.loads(m.group(1))  # พังทันทีถ้าฝังผิด ดีกว่าไปพังบนหน้าเว็บ

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out, encoding="utf-8")
    print(f"เขียน {OUT} ({len(out.encode()) / 1024:.0f} KB)")
    print(f"  {d['total_games']} เกม · {len(d['heroes'])} ฮีโร่ · {len(d['matchups'])} matchup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
