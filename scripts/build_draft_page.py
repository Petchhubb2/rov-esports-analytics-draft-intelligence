"""ฝังข้อมูล JSON ลงใน template แล้วได้หน้าเว็บที่เปิดได้เลย

    python scripts/export_draft_data.py     # สร้างข้อมูลก่อน
    python scripts/build_draft_page.py      # แล้วค่อยฝัง
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "core"))

from rov.cli.console import setup_console  # noqa: E402

TPL = Path("apps/web/draft_board.tpl.html")
DATA = Path("data/exports/draft_data.json")
OUT = Path("data/exports/draft_board.html")
ASSETS = Path("data/assets/heroes")
ZONE_MAP = Path("data/exports/zone_map.png")


def _pic_index(stems: list[str]) -> dict[str, str]:
    """ชื่อพ้อง -> ชื่อไฟล์

    ชื่อไฟล์มาจากหน้า Portal ซึ่งใช้ชื่อเต็ม เช่น lu_bu, ming_shiyin
    แต่ข้อมูลแมตช์ใช้ชื่อสั้น เช่น lubu, ming
    จึงต้องใช้ตัวจับคู่ชื่อพ้องชุดเดียวกับที่ใช้จับคู่ hero class
    """
    from rov.draft.importer.heroinfo import _aliases_for

    cand: dict[str, set[str]] = {}
    for stem in stems:
        for alias in _aliases_for(stem):
            cand.setdefault(alias, set()).add(stem)
    # ชื่อพ้องที่ชี้ไปหลายไฟล์ ทิ้งไป ดีกว่าจับคู่ผิด
    return {a: next(iter(v)) for a, v in cand.items() if len(v) == 1}


def local_assets() -> dict:
    """ผูกรูปเข้ากับข้อมูล ถ้ามีอยู่ในเครื่อง

    ใช้ path แบบสัมพัทธ์ ไม่ฝังรูปลงไฟล์ เพราะ
      1. หน้าเว็บจะเบา เปิดเร็ว
      2. รูปเป็นงานศิลป์ของ Garena/TiMi การฝังลงไฟล์เดียวเท่ากับทำสำเนา
         ซึ่งไม่ควรทำถ้าจะเอาไปเผยแพร่ (ดู data/assets/heroes/ATTRIBUTION.md)
    """
    extra: dict = {}
    if ASSETS.exists():
        by_stem = {
            f.stem: f"assets/heroes/{f.name}"
            for f in sorted(ASSETS.iterdir())
            if f.suffix.lower() in (".jpg", ".png")
        }
        if by_stem:
            index = _pic_index(list(by_stem))
            hero_ids = [h["id"] for h in json.loads(DATA.read_text(encoding="utf-8"))["heroes"]]
            pics = {}
            for hid in hero_ids:
                stem = by_stem.get(hid) and hid
                if stem is None:
                    match = index.get(hid) or index.get(hid.replace("_", ""))
                    stem = match
                if stem:
                    pics[hid] = by_stem[stem]
            extra["pics"] = pics
            extra["pics_missing"] = sorted(set(hero_ids) - set(pics))
    if ZONE_MAP.exists():
        extra["zone_map"] = ZONE_MAP.name
    return extra


def main() -> int:
    setup_console()
    for p in (TPL, DATA):
        if not p.exists():
            print(f"ไม่พบไฟล์: {p}")
            return 1

    tpl = TPL.read_text(encoding="utf-8")
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    payload.update(local_assets())
    # \/ กัน </script> ในข้อมูลไปปิด tag ก่อนเวลา — JSON ยอมรับ escape นี้
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<" + chr(92) + "/"
    )
    body = tpl.replace("__DATA__", raw)
    # ต้องห่อเป็นเอกสารเต็มพร้อม charset
    # template เป็นแค่ body fragment (รูปแบบที่ Artifact ต้องการ)
    # ถ้าเสิร์ฟดิบ ๆ เบราว์เซอร์จะเดา encoding แล้วอักษรไทยเพี้ยนทั้งหน้า
    out = "\n".join(
        [
            "<!doctype html>",
            '<html lang="th">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width,initial-scale=1">',
            "</head>",
            "<body>",
            body,
            "</body>",
            "</html>",
            "",
        ]
    )

    m = re.search(r'id="draft-data">(.*?)</script>', out, re.S)
    if m is None:
        print("ไม่พบช่องใส่ข้อมูลใน template")
        return 1
    d = json.loads(m.group(1))  # พังทันทีถ้าฝังผิด ดีกว่าไปพังบนหน้าเว็บ

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out, encoding="utf-8")
    print(f"เขียน {OUT} ({len(out.encode()) / 1024:.0f} KB)")
    print(f"  {d['total_games']} เกม · {len(d['heroes'])} ฮีโร่ · {len(d['matchups'])} matchup")
    miss = d.get("pics_missing", [])
    print(f"  รูปฮีโร่ {len(d.get('pics', {}))} · zone map {'มี' if d.get('zone_map') else 'ไม่มี'}")
    if miss:
        print(f"  ไม่มีรูป {len(miss)}: {', '.join(miss)}")

    # คัดลอกไฟล์ประกอบไปไว้ข้างหน้าเว็บ ให้เปิดจากโฟลเดอร์เดียวได้เลย
    if ASSETS.exists():
        dest = OUT.parent / "assets" / "heroes"
        dest.mkdir(parents=True, exist_ok=True)
        n = 0
        for f in ASSETS.iterdir():
            if f.suffix.lower() in (".jpg", ".png", ".md"):
                shutil.copy2(f, dest / f.name)
                n += 1
        print(f"  คัดลอกไฟล์ประกอบ {n} ไฟล์ไป {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
