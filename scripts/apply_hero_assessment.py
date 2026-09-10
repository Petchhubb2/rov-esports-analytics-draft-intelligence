"""รวมค่าที่ประเมินไว้ใน hero_assessment.yaml เข้า heroes.yaml

แยกไฟล์กันเพราะสองไฟล์นี้มีเจ้าของต่างกัน
    heroes.yaml            เครื่องสร้าง (rov draft heroes-init) ทับได้
    hero_assessment.yaml   คนหรือผู้ช่วยเขียน ห้ามเครื่องทับ

สคริปต์นี้เป็นสะพานทางเดียว: assessment -> heroes.yaml เท่านั้น

**ไม่ทับค่าที่คนกรอกเอง** ฮีโร่ที่ filled_kind เป็น human อยู่แล้ว
จะถูกข้ามทั้งตัว เพื่อไม่ให้ค่าที่ผู้ช่วยประเมินไปลบงานของคนที่รู้เกมจริง

    python scripts/apply_hero_assessment.py            ดูว่าจะเปลี่ยนอะไร
    python scripts/apply_hero_assessment.py --write    เขียนจริง
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "core"))

from rov.cli.console import setup_console  # noqa: E402
from rov.domain.enums import DamageType, LaneRole, MacroTag  # noqa: E402
from rov.draft.heroes import Damage, HeroDB, Scaling, Utility  # noqa: E402

ASSESSMENT = Path("configs/draft/hero_assessment.yaml")
HEROES = Path("configs/draft/heroes.yaml")


def main() -> int:
    setup_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="เขียนไฟล์จริง")
    ap.add_argument("--heroes", default=str(HEROES))
    ap.add_argument("--assessment", default=str(ASSESSMENT))
    args = ap.parse_args()

    doc = yaml.safe_load(Path(args.assessment).read_text(encoding="utf-8"))
    entries = doc.get("heroes") or {}
    who = doc.get("assessed_by") or "unknown"
    when = doc.get("assessed_on")
    evidence = doc.get("evidence")

    db = HeroDB.load(args.heroes)
    index = {h.id: h for h in db.heroes}

    applied = skipped_human = missing = 0
    for hid, spec in entries.items():
        hero = index.get(hid)
        if hero is None:
            print(f"  ✗ ไม่มี {hid} ใน {args.heroes} — ข้าม")
            missing += 1
            continue
        if hero.filled_kind == "human":
            print(f"  · ข้าม {hid} เพราะมีคนกรอกไว้แล้ว")
            skipped_human += 1
            continue

        hero.lane_roles = [LaneRole(v) for v in spec["lane_roles"]]
        hero.range = spec["range"]

        d = spec["damage"]
        hero.damage = Damage(
            type=DamageType(d["type"]), profile=d.get("profile"), target=d.get("target")
        )
        hero.scaling = Scaling(**spec["scaling"])
        hero.utility = Utility(**spec["utility"])
        hero.macro_tags = [MacroTag(t) for t in spec.get("macro_tags", [])]

        hero.filled_by = who
        hero.filled_on = when
        hero.filled_kind = "assistant"
        note = (spec.get("notes") or "").strip()
        hero.notes = f"{note} [หลักฐาน: {evidence}]" if evidence else note

        miss = hero.missing_fields()
        if miss:
            print(f"  ✗ {hid} ยังขาด {miss} — ตรวจ {args.assessment}")
        else:
            applied += 1

    cs = db.completeness()
    print("")
    print(f"ประเมินโดย   {who} ({when})")
    print(f"เติมครบ      {applied} ตัว")
    if skipped_human:
        print(f"ข้ามของคน    {skipped_human} ตัว")
    if missing:
        print(f"ไม่พบในไฟล์  {missing} ตัว")
    print(f"รวมทั้งไฟล์   {cs['complete']}/{cs['total']} ({cs['fraction']:.0%})")

    # ครอบคลุมเมตาแค่ไหน — สำคัญกว่าจำนวนตัวดิบ เพราะฮีโร่หางแถวแทบไม่ถูกใช้
    try:
        from rov.cli.main import _regions
        from rov.draft.meta import pool

        st = pool(_regions()).stats
        done = {h.id for h in db.complete_heroes}
        tot = sum(s.presence for s in st.heroes.values())
        cov = sum(s.presence for hid, s in st.heroes.items() if hid in done)
        print(f"ครอบคลุม pick+ban จริง {cov / tot:.0%} ของทั้งหมด")
    except Exception as exc:  # noqa: BLE001
        print(f"(คำนวณความครอบคลุมไม่ได้: {exc})")

    if args.write:
        db.save(args.heroes)
        print(f"\nเขียน {args.heroes}")
    else:
        print("\nยังไม่ได้เขียน — ใส่ --write เพื่อบันทึก")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
