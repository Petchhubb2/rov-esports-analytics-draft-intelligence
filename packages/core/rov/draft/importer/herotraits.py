"""ดึง "ข้อเท็จจริง" ของฮีโร่จากหน้า Liquipedia — ไม่ใช่การประเมิน

**เส้นแบ่งที่โมดูลนี้ยึด**

หน้าฮีโร่ของ Liquipedia มีข้อมูลที่ตรวจสอบได้อยู่จริง และไม่ใช่ความเห็นใคร

    |lane1 = roamaov          ตำแหน่งที่เกมกำหนด
    |role1 = supportaov       class ที่เกมกำหนด
    |dmg  = mgc               สกิลนี้ทำดาเมจเวทหรือกายภาพ
    |type = {{SkillTextID|red|Knock Back}}   สกิลนี้มีผลอะไร

สามอย่างแรกคือข้อเท็จจริงตรง ๆ ส่วน `type` คือ **รายการผลของสกิล**
ซึ่งก็เป็นข้อเท็จจริง ("Rouie มีสกิลที่ Knock Back") ไม่ใช่การให้คะแนน
("Rouie peel ได้ 80 เต็ม 100")

โมดูลนี้หยุดที่ข้อเท็จจริง **ไม่แปลงเป็นคะแนน 0-100 ให้**
การแปลงเป็นคะแนนคือการประเมิน ซึ่งต้องมีคนรับผิดชอบและต้องบอกว่าใครทำ
ดู scripts/derive_hero_traits.py ว่าใครเป็นคนแปลงและใช้เกณฑ์อะไร

**ทำไมถึงคุ้มที่จะดึง**

Composition Engine ต้องการ 18 ช่องต่อฮีโร่ ในจำนวนนั้นมี 3 ช่อง
(lane_roles, damage.type, range) ที่ดึงอัตโนมัติได้ถูกต้อง 100%
ส่วนอีก 12 ช่องที่เหลือ การมีรายการ CC และ heal อยู่ตรงหน้า
ทำให้คนกรอกทำงานเร็วขึ้นมากและกรอกได้สม่ำเสมอกว่าเดิม
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rov.domain.enums import DamageType

# ---------------------------------------------------------------- infobox

_FIELD = re.compile(r"\|\s*([a-z0-9_]+)\s*=\s*([^\n|]*)")

# ค่าใน lane1/lane2 ของ Liquipedia -> เลนของเรา
#
# คำที่ใส่ไว้ตรงนี้เป็นคำที่ **พบจริง** ในหน้าฮีโร่ที่ดึงมาแล้ว
# ไม่ใช่คำที่เดาว่าน่าจะมี ถ้าเจอคำใหม่ parse_hero_page จะทิ้งไปเงียบ ๆ
# ซึ่งปลอดภัยกว่าการเดา — และจะเห็นได้จากช่อง lanes ที่ว่างในไฟล์หลักฐาน
#
# นับจากหน้าที่ดึงมา 30 หน้า: darkslayer 12, jungleaov 12, abyssaldragon 7,
# roamaov 6, midaov 5, roam 1
LANE_WORDS: dict[str, str] = {
    "darkslayer": "ds",
    "darkslayeraov": "ds",
    "jungleaov": "jungle",
    "junglaov": "jungle",
    "midaov": "mid",
    "abyssaldragon": "dragon",
    "abyssaldragonaov": "dragon",
    "roam": "support",
    "roamaov": "support",
    "supportaov": "support",
}

# ---------------------------------------------------------------- skill card

_SKILLTEXT = re.compile(r"\{\{SkillTextID\|[a-z]+\|([^}|]+)\}\}", re.I)


def _templates(wikitext: str, name: str) -> list[str]:
    """คืนเนื้อในของเทมเพลตชื่อหนึ่ง โดยนับวงเล็บปีกกาให้สมดุล

    ใช้การนับแทน regex เพราะเทมเพลตของ Liquipedia **ซ้อนกัน**
    การ์ดสกิลหนึ่งใบมี {{SkillTextID|...}} อยู่ข้างใน ถ้าใช้ regex
    แบบ non-greedy หา `}}` ตัวแรก มันจะไปจบที่วงเล็บของ SkillTextID
    ทำให้ได้การ์ดที่ขาดครึ่ง ส่วนถ้าบังคับว่าต้องเป็น `\\n}}` ก็จะพลาด
    การ์ดที่เขียนรวบบรรทัดเดียว ซึ่งมีจริงในบางหน้า
    """
    out: list[str] = []
    needle = "{{" + name
    low = wikitext.lower()
    target = needle.lower()
    i = 0
    while True:
        start = low.find(target, i)
        if start == -1:
            return out
        depth = 0
        j = start
        while j < len(wikitext) - 1:
            pair = wikitext[j : j + 2]
            if pair == "{{":
                depth += 1
                j += 2
                continue
            if pair == "}}":
                depth -= 1
                j += 2
                if depth == 0:
                    out.append(wikitext[start + len(needle) : j - 2])
                    break
                continue
            j += 1
        else:
            return out  # วงเล็บไม่ปิด — หยุดแทนที่จะเดา
        i = j

# dmg= ในการ์ดสกิล
_DMG_WORDS = {
    "mgc": DamageType.MAGICAL,
    "magic": DamageType.MAGICAL,
    "magical": DamageType.MAGICAL,
    "phy": DamageType.PHYSICAL,
    "physical": DamageType.PHYSICAL,
    "true": DamageType.TRUE,
}

# ป้ายผลสกิลที่สนใจ จัดกลุ่มตามความหมายทาง macro
#
# hard CC = ทำให้ศัตรูควบคุมตัวละครไม่ได้เลยชั่วขณะ
# soft CC = ยังเดินได้แต่ถูกลดความสามารถ
#
# แยกสองกลุ่มนี้สำคัญ เพราะคอมพ์ที่ engage ต้องการ hard CC
# ส่วน poke comp ใช้ soft CC ก็พอ ดู docs/06-draft-engine.md §3
HARD_CC = {
    "stun", "knock up", "knockup", "airborne", "knock back", "knockback",
    "suppress", "suppression", "taunt", "petrify", "freeze", "immobilize",
    "sleep", "charm", "fear", "terrify", "root", "snare", "entangle",
}
SOFT_CC = {
    "slow", "silence", "blind", "disarm", "weaken", "wither", "cripple",
}
SUSTAIN_TAGS = {"heal", "healing", "regen", "regeneration", "lifesteal", "shield", "barrier"}
MOBILITY_TAGS = {
    "dash", "blink", "teleport", "leap", "jump", "movement speed", "speed up",
    "flight", "flash", "charge",
}
SHIELD_TAGS = {"shield", "barrier", "damage reduction", "immunity", "invincible"}


@dataclass
class HeroTraits:
    """สิ่งที่อ่านได้จากหน้าฮีโร่ตรง ๆ — ทุกช่องคือข้อเท็จจริง"""

    hero_id: str
    page_title: str
    name: str | None = None
    lanes: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    damage_types: list[DamageType] = field(default_factory=list)
    skill_effects: list[str] = field(default_factory=list)
    n_skills: int = 0

    # ------------------------------------------------------------------

    @property
    def damage_type(self) -> DamageType | None:
        """ชนิดดาเมจหลัก — hybrid เมื่อมีทั้งเวทและกายภาพในสกิลเดียวกัน

        คืน None เมื่อไม่มีสกิลไหนระบุ dmg= เลย (เช่นซัพพอร์ตที่ไม่ทำดาเมจ)
        ผู้เรียกต้องตัดสินใจเอง ไม่เดาแทน
        """
        kinds = {d for d in self.damage_types if d is not DamageType.TRUE}
        if len(kinds) > 1:
            return DamageType.HYBRID
        if kinds:
            return next(iter(kinds))
        if DamageType.TRUE in self.damage_types:
            return DamageType.TRUE
        return None

    def _matching(self, vocab: set[str]) -> list[str]:
        """หาป้ายที่ตรงกับคำในคลัง โดยเทียบแบบขอบคำ

        ต้องเทียบแบบขอบคำ ไม่ใช่เท่ากันเป๊ะ เพราะ Liquipedia เขียนป้าย
        ยาวกว่าคำเดียวอยู่บ่อย ๆ เช่น "Self Damage Reduction" ของ Toro
        และ "Movement Speed Boost" ซึ่งถ้าเทียบเป๊ะจะหลุดหมด

        และต้องเป็นขอบคำ ไม่ใช่ substring ลอย ๆ มิฉะนั้น "Discharge"
        จะไปเข้าเงื่อนไข "charge" แล้วนับเป็น mobility ทั้งที่ไม่ใช่
        """
        out = []
        for e in self.skill_effects:
            low = e.strip().lower()
            for word in vocab:
                if re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", low):
                    out.append(e.strip())
                    break
        return sorted(set(out))

    @property
    def hard_cc(self) -> list[str]:
        return self._matching(HARD_CC)

    @property
    def soft_cc(self) -> list[str]:
        return self._matching(SOFT_CC)

    @property
    def sustain(self) -> list[str]:
        return self._matching(SUSTAIN_TAGS)

    @property
    def mobility(self) -> list[str]:
        return self._matching(MOBILITY_TAGS)

    @property
    def shields(self) -> list[str]:
        return self._matching(SHIELD_TAGS)

    def evidence(self) -> dict:
        """สรุปหลักฐานเป็น dict — ใช้เขียนลงไฟล์ให้คนกรอกอ่าน"""
        return {
            "page": self.page_title,
            "name": self.name,
            "lanes": self.lanes,
            "roles": self.roles,
            "damage_type": self.damage_type.value if self.damage_type else None,
            "n_skills": self.n_skills,
            "hard_cc": self.hard_cc,
            "soft_cc": self.soft_cc,
            "sustain": self.sustain,
            "mobility": self.mobility,
            "shields": self.shields,
            "all_effects": sorted(set(e.strip() for e in self.skill_effects)),
        }


def parse_hero_page(hero_id: str, title: str, wikitext: str) -> HeroTraits:
    """แยกข้อเท็จจริงออกจาก wikitext ของหน้าฮีโร่หนึ่งหน้า"""
    t = HeroTraits(hero_id=hero_id, page_title=title)

    for box in _templates(wikitext, "infobox hero"):
        for key, val in _FIELD.findall(box):
            val = val.strip()
            if not val:
                continue
            if key == "name":
                t.name = val
            elif key.startswith("lane"):
                lane = LANE_WORDS.get(val.lower())
                if lane and lane not in t.lanes:
                    t.lanes.append(lane)
            elif key.startswith("role"):
                t.roles.append(val.lower())

    for card in _templates(wikitext, "SkillCard"):
        t.n_skills += 1
        for key, val in _FIELD.findall(card):
            if key == "dmg":
                d = _DMG_WORDS.get(val.strip().lower())
                if d:
                    t.damage_types.append(d)
        # type= อาจมีหลาย SkillTextID ในบรรทัดเดียว จึงต้องหาทั้งการ์ด
        for tm in re.finditer(r"\|\s*type\s*=\s*([^\n]*)", card, re.I):
            t.skill_effects.extend(_SKILLTEXT.findall(tm.group(1)))

    return t


def fetch_hero_traits(client, hero_id: str, title: str) -> HeroTraits:
    """ดึงหนึ่งหน้า — หนึ่ง request (หรือศูนย์ถ้ามีใน cache)"""
    return parse_hero_page(hero_id, title, client.page_wikitext(title))
