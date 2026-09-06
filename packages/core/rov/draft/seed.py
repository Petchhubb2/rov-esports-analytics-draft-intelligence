"""สร้างและอัปเดตไฟล์ฮีโร่จากแหล่งข้อมูลจริง

เติมได้เฉพาะสิ่งที่ตรวจสอบได้
    id           จากฮีโร่ที่ปรากฏจริงในรายการแข่ง
    name_en      จากหน้า Portal ของ Liquipedia
    hero_class   จากหน้า Portal ของ Liquipedia

**ไม่เติม** ค่าเชิงคุณภาพอย่าง engage, peel, scaling
เพราะเป็นการประเมินของมนุษย์ ระบบเดาให้ไม่ได้ และการเดาจะทำให้
คำแนะนำดูน่าเชื่อโดยไม่มีฐานรองรับ ซึ่งอันตรายกว่าการบอกว่ายังไม่รู้

ลำดับของฮีโร่ในไฟล์เรียงตาม presence (pick + ban) จริง
เพื่อให้คนที่มากรอกทำตัวที่สำคัญที่สุดก่อน
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rov.draft.heroes import Hero, HeroDB
from rov.draft.importer.heroinfo import build_alias_index, resolve
from rov.draft.stats import DraftStats


@dataclass
class SeedResult:
    total: int = 0
    created: int = 0
    class_filled: int = 0
    unmapped: list[str] = field(default_factory=list)
    preserved: int = 0

    def report(self) -> str:
        lines = [
            f"ฮีโร่ในไฟล์        {self.total}",
            f"เพิ่มใหม่          {self.created}",
            f"เติม class ได้     {self.class_filled}",
            f"เก็บค่าเดิมไว้      {self.preserved}",
        ]
        if self.unmapped:
            lines.append("")
            lines.append(
                f"จับคู่ class ไม่ได้ {len(self.unmapped)} ตัว ต้องกรอกเอง: "
                + ", ".join(self.unmapped)
            )
        return "\n".join(lines)


def seed_hero_db(
    stats: DraftStats,
    portal_info: dict[str, dict],
    existing: HeroDB | None = None,
    patch: str | None = None,
) -> tuple[HeroDB, SeedResult]:
    """สร้างไฟล์ฮีโร่ใหม่ หรืออัปเดตของเดิมโดยไม่ทับค่าที่คนกรอกไว้แล้ว

    การไม่ทับค่าเดิมสำคัญมาก เพราะการกรอก attribute ใช้เวลาหลายวัน
    การรัน seed ซ้ำแล้วลบงานทิ้งจะทำให้ไม่มีใครกล้ารันอีก
    """
    index = build_alias_index(portal_info)
    old = {h.id: h for h in existing.heroes} if existing else {}

    db = HeroDB(version=1, patch=patch or (existing.patch if existing else None))
    result = SeedResult()

    for stat in stats.ranked_by_presence():
        hid = stat.hero_id
        hero = old.get(hid)
        if hero is None:
            hero = Hero(id=hid)
            result.created += 1
        elif hero.complete or any(hero.missing_fields()) != any(Hero(id=hid).missing_fields()):
            result.preserved += 1

        canonical = resolve(hid, index)
        info = portal_info.get(canonical) if canonical else None
        if info and info.get("hero_class"):
            # เติม class เฉพาะเมื่อยังว่าง ไม่ทับของที่คนแก้ไว้
            if not hero.hero_class:
                hero.hero_class = list(info["hero_class"])
            if not hero.name_en:
                hero.name_en = info["name_en"]
            result.class_filled += 1
        else:
            result.unmapped.append(hid)
            if not hero.name_en:
                hero.name_en = hid.replace("_", " ").title()

        db.heroes.append(hero)

    # ฮีโร่ที่เคยมีในไฟล์แต่ไม่ปรากฏในสถิติ ให้คงไว้ ไม่ลบทิ้ง
    seen = {h.id for h in db.heroes}
    for hid, hero in old.items():
        if hid not in seen:
            db.heroes.append(hero)

    result.total = len(db.heroes)
    return db, result
