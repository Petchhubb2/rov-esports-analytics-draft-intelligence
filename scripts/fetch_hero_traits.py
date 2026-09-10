"""ดึงข้อเท็จจริงของฮีโร่จากหน้า Liquipedia มาเก็บเป็นไฟล์หลักฐาน

ผลลัพธ์คือ data/hero_traits.json ซึ่งเป็น **หลักฐาน** ไม่ใช่คำตอบ
ใครจะแปลงเป็นคะแนน 0-100 ต้องทำแยกและลงชื่อกำกับ
ดู scripts/derive_hero_traits.py

    python scripts/fetch_hero_traits.py --top 30 --live

ไม่ใส่ --live จะอ่านจาก cache อย่างเดียว ปลอดภัยเสมอ
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "core"))

from rov.cli.console import setup_console  # noqa: E402
from rov.cli.main import _regions  # noqa: E402
from rov.draft.heroes import HeroDB  # noqa: E402
from rov.draft.importer.herotraits import parse_hero_page  # noqa: E402
from rov.draft.importer.liquipedia import (  # noqa: E402
    BASE_URL,
    LiquipediaClient,
    LiquipediaError,
)
from rov.draft.meta import pool  # noqa: E402

OUT = Path("data/hero_traits.json")


def page_params(title: str) -> dict:
    return {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": title,
        "format": "json",
        "formatversion": "2",
    }


def cached_wikitext(client: LiquipediaClient, title: str) -> str | None:
    entry = client.cache.get(BASE_URL, page_params(title))
    if entry is None:
        return None
    data = json.loads(entry.body)
    pages = data.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None
    try:
        return pages[0]["revisions"][0]["slots"]["main"]["content"]
    except (KeyError, IndexError):
        return None


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=30, help="กี่ตัวแรกตาม presence จริง")
    ap.add_argument("--live", action="store_true", help="ยิง request จริง")
    args = ap.parse_args()

    regions = _regions()
    if not regions:
        print("ยังไม่มีข้อมูลใน cache — รัน rov draft import ก่อน")
        return 1

    stats = pool(regions).stats
    db = HeroDB.load("configs/draft/heroes.yaml")
    names = {h.id: h.name_en for h in db.heroes}

    order = [h.hero_id for h in stats.ranked_by_presence()][: args.top]
    client = LiquipediaClient()

    if args.live:
        plan = client.plan(len(order))
        print(
            f"จะยิงได้มากสุด {plan['requests']} request "
            f"≈ {plan['estimated_seconds']} วินาที · โควตาเหลือ {plan['remaining_this_hour']}"
        )

    existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    fetched = skipped = failed = 0

    for hid in order:
        if hid in existing:
            skipped += 1
            continue
        title = names.get(hid) or hid.replace("_", " ").title()
        wt = cached_wikitext(client, title)
        if wt is None:
            if not args.live:
                print(f"  · ข้าม {hid} (ไม่มีใน cache — ใส่ --live)")
                skipped += 1
                continue
            try:
                wt = client.page_wikitext(title)
            except LiquipediaError as exc:
                print(f"  ✗ {hid} ({title}): {exc}")
                failed += 1
                continue
        traits = parse_hero_page(hid, title, wt)
        ev = traits.evidence()
        # เลนจากข้อมูลแมตช์ของเราเอง เชื่อได้กว่าหน้าวิกิ เพราะเป็นสิ่งที่เกิดจริง
        existing[hid] = ev
        fetched += 1
        print(
            f"  ✓ {hid:<16} {ev['damage_type'] or '—':<9} "
            f"lane={','.join(ev['lanes']) or '—':<18} "
            f"hardCC={len(ev['hard_cc'])} softCC={len(ev['soft_cc'])} "
            f"sustain={len(ev['sustain'])} mob={len(ev['mobility'])}"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(existing, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8",
    )
    print(f"\nเขียน {OUT} · ใหม่ {fetched} · ข้าม {skipped} · ล้มเหลว {failed}")
    print(f"รวมในไฟล์ {len(existing)} ตัว · สถิติ client {client.stats.as_dict()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
