"""ดึงรายชื่อฮีโร่และ class จาก Liquipedia

class ของฮีโร่เป็นข้อเท็จจริงสาธารณะที่ตรวจสอบได้ ไม่ใช่การประเมิน
จึงดึงอัตโนมัติได้ ต่างจากค่าอย่าง engage หรือ peel ที่ต้องให้คนกรอก

โครงสร้างจริงของหน้า Portal:Heroes/Arena of Valor

    <section begin="Included Assasin" />   <gallery> ... </gallery>
    <section begin="included Warrior" />   <gallery> ... </gallery>
    <section begin="included Mage" />      <gallery> ... </gallery>
    <section begin="included Marksman" />  <gallery> ... </gallery>
    <section begin="included Support" />   <gallery> ... </gallery>
    <section begin="included Tank" />      <gallery> ... </gallery>
    <section begin="All Champions" />      <gallery> ... </gallery>   <- ทุกตัว
    <section begin="Removed" />            <gallery> ... </gallery>   <- ถอดออกแล้ว

ต้องยึด section marker ไม่ใช่หัวข้อ <big> เพราะ gallery "All Champions"
อยู่ต่อจาก Tank ทำให้การนับด้วย <big> ดูดฮีโร่ทุกตัวเข้าไปเป็น Tank
(เคยเกิดจริง: Tank ได้ 132 จาก 133 ตัว)
"""

from __future__ import annotations

import re

from rov.domain.enums import HeroClass
from rov.draft.importer.parser import normalize_hero_id

PORTAL_PAGE = "Portal:Heroes/Arena of Valor"

# Liquipedia สะกด Assassin ผิดเป็น Assasin จึงรับทั้งสองแบบ
_CLASS_ALIASES = {
    "assassin": HeroClass.ASSASSIN,
    "assasin": HeroClass.ASSASSIN,
    "mage": HeroClass.MAGE,
    "marksman": HeroClass.MARKSMAN,
    "support": HeroClass.SUPPORT,
    "tank": HeroClass.TANK,
    "warrior": HeroClass.WARRIOR,
}

_SECTION = re.compile(r'<section\s+begin\s*=\s*"([^"]+)"')
_GALLERY = re.compile(r"<gallery[^>]*>(.*?)</gallery>", re.DOTALL)
_LINK = re.compile(r"\|\s*link=([^|\]\n]+)")

ALL_SECTION = "all champions"
REMOVED_SECTION = "removed"


def _section_class(name: str) -> HeroClass | None:
    """แปลงชื่อ section เป็น class — คืน None ถ้าไม่ใช่ section ของ class"""
    words = name.strip().lower().replace("included", "").split()
    for w in words:
        if (k := _CLASS_ALIASES.get(w)) is not None:
            return k
    return None


def _heroes_in(block: str) -> list[str]:
    names = []
    for m in _LINK.finditer(block):
        n = m.group(1).strip()
        if n and not n.startswith("File:"):
            names.append(n)
    return names


def parse_hero_classes(wikitext: str) -> tuple[dict[str, dict], set[str]]:
    """คืน ({hero_id: {name_en, hero_class}}, ชื่อฮีโร่ที่ถูกถอดออกจากเกม)

    จับคู่แต่ละ gallery กับ section ที่อยู่ก่อนหน้าที่ใกล้ที่สุด
    """
    sections = [(m.start(), m.group(1)) for m in _SECTION.finditer(wikitext)]
    out: dict[str, dict] = {}
    removed: set[str] = set()

    for gm in _GALLERY.finditer(wikitext):
        prior = [s for s in sections if s[0] < gm.start()]
        if not prior:
            continue
        section_name = prior[-1][1].strip().lower()
        names = _heroes_in(gm.group(1))

        if section_name.startswith(REMOVED_SECTION):
            removed.update(normalize_hero_id(n) for n in names)
            continue

        klass = _section_class(section_name)
        for n in names:
            hid = normalize_hero_id(n)
            entry = out.setdefault(hid, {"name_en": n, "hero_class": []})
            # section "All Champions" ไม่มี class จึงบันทึกแค่ชื่อ
            if klass is not None and klass not in entry["hero_class"]:
                entry["hero_class"].append(klass)

    return out, removed


def fetch_hero_classes(client) -> tuple[dict[str, dict], set[str]]:
    """ดึงและแยกข้อมูล class — ใช้หนึ่ง request"""
    return parse_hero_classes(client.page_wikitext(PORTAL_PAGE))


# --------------------------------------------------------------- alias

_PAREN = re.compile(r"_?\([^)]*\)")


def _aliases_for(hero_id: str) -> list[str]:
    """ชื่อพ้องที่เป็นไปได้ของฮีโร่หนึ่งตัว

    หน้า Portal ใช้ชื่อเต็มและมีวงเล็บแก้กำกวม ส่วนหน้าแมตช์ใช้ชื่อสั้น
    ตัวอย่างที่พบจริงในข้อมูล

        max_(arena_of_valor_hero)  ->  max
        yue_(aov_hero)             ->  yue
        ming_shiyin                ->  ming
        wiro_sableng               ->  wiro
        lu_bu                      ->  lubu
    """
    out = {hero_id}
    bare = _PAREN.sub("", hero_id).strip("_")
    out.add(bare)
    out.add(bare.replace("_", ""))
    if "_" in bare:
        out.add(bare.split("_")[0])
    return [a for a in out if a]


def build_alias_index(info: dict[str, dict]) -> dict[str, str]:
    """ชื่อพ้อง -> id หลัก

    ชื่อพ้องที่ชี้ไปฮีโร่มากกว่าหนึ่งตัวจะถูกทิ้ง เพื่อไม่ให้จับคู่ผิด
    ดีกว่าจับคู่ผิดแบบเงียบ ๆ
    """
    candidates: dict[str, set[str]] = {}
    for hid in info:
        for alias in _aliases_for(hid):
            candidates.setdefault(alias, set()).add(hid)
    return {a: next(iter(ids)) for a, ids in candidates.items() if len(ids) == 1}


def resolve(hero_id: str, index: dict[str, str]) -> str | None:
    """หา id หลักของฮีโร่จากชื่อที่พบในหน้าแมตช์"""
    if hero_id in index:
        return index[hero_id]
    return index.get(hero_id.replace("_", ""))
