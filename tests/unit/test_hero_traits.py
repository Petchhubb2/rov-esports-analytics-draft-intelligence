"""ทดสอบการดึงข้อเท็จจริงจากหน้าฮีโร่ และความสอดคล้องของไฟล์ประเมิน

wikitext ตัวอย่างในไฟล์นี้ตัดมาจากหน้าจริงของ Liquipedia
(Rouie, Toro, Capheny) เพื่อให้เทสต์เจอบั๊กแบบเดียวกับข้อมูลจริง
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from rov.domain.enums import DamageType, LaneRole, MacroTag
from rov.draft.heroes import REQUIRED_UTILITY, HeroDB
from rov.draft.importer.herotraits import parse_hero_page

ROUIE = """{{Hero Tabs}}
{{infobox hero
|name = Rouie
|title = Light of Veda
|lane1 = roamaov
|role1 = supportaov
}}
==Skills==
===Skill 1: Holy Light===
{{SkillCard
|name=Holy Light
|skill=Skill 1
|type={{SkillTextID|red|Silence}}
|dmg=mgc
|desc=Rouie deals damage over time.
}}
===Skill 1: Holy Wings===
{{SkillCard
|name=Holy Wings
|skill=Skill 1
|type={{SkillTextID|red|Knock Back}}
|dmg=mgc
|desc=knocks back enemies.
}}
===Skill 2: Void Portal===
{{SkillCard
|name=Void Portal
|skill=Skill 2
|type={{SkillTextID|yellow|Teleport}} {{SkillTextID|green|Heal}}
|desc=teleports all friendly heroes back.
}}
"""

TORO = """{{infobox hero
|name = Toro
|lane1 = roamaov
|lane2 = darkslayer
|role1 = tankaov
|role2 = supportaov
}}
{{SkillCard
|name=Ram
|type={{SkillTextID|red|Knockup}} {{SkillTextID|red|Slow}}
|dmg=phy
}}
{{SkillCard
|name=Guard
|type={{SkillTextID|yellow|Self Damage Reduction}}
}}
"""

HYBRID = """{{infobox hero
|name = Skud
|lane1 = darkslayer
|role1 = warrioraov
}}
{{SkillCard|name=A|type={{SkillTextID|red|Knock Back}}|dmg=phy}}
{{SkillCard|name=B|type={{SkillTextID|yellow|Movement Speed}}|dmg=mgc}}
"""

NO_DAMAGE = """{{infobox hero
|name = Nobody
|role1 = supportaov
}}
{{SkillCard|name=A|type={{SkillTextID|green|Heal}}}}
"""


# ------------------------------------------------------------------ infobox


def test_reads_name_lane_and_role_from_infobox():
    t = parse_hero_page("rouie", "Rouie", ROUIE)
    assert t.name == "Rouie"
    assert t.lanes == ["support"]
    assert t.roles == ["supportaov"]


def test_reads_second_lane():
    """Toro มี lane1 กับ lane2 ต้องได้ทั้งคู่ ไม่ใช่แค่อันแรก"""
    t = parse_hero_page("toro", "Toro", TORO)
    assert t.lanes == ["support", "ds"]


def test_unknown_lane_word_is_dropped_not_guessed():
    wt = "{{infobox hero\n|name = X\n|lane1 = someNewLaneAov\n}}\n"
    assert parse_hero_page("x", "X", wt).lanes == []


# ------------------------------------------------------------------ ดาเมจ


def test_damage_type_from_skill_tags():
    assert parse_hero_page("rouie", "Rouie", ROUIE).damage_type is DamageType.MAGICAL
    assert parse_hero_page("toro", "Toro", TORO).damage_type is DamageType.PHYSICAL


def test_mixed_physical_and_magical_is_hybrid():
    assert parse_hero_page("skud", "Skud", HYBRID).damage_type is DamageType.HYBRID


def test_no_damage_tag_returns_none_not_a_guess():
    """ซัพพอร์ตที่ไม่มี dmg= เลย ต้องได้ None ห้ามเดาเป็น physical"""
    assert parse_hero_page("n", "Nobody", NO_DAMAGE).damage_type is None


# ------------------------------------------------------------------ ป้ายสกิล


def test_hard_and_soft_cc_are_separated():
    t = parse_hero_page("rouie", "Rouie", ROUIE)
    assert t.hard_cc == ["Knock Back"]
    assert t.soft_cc == ["Silence"]


def test_multi_word_tag_still_matches():
    """'Self Damage Reduction' ต้องเข้าเงื่อนไข shield

    เทียบแบบเท่ากันเป๊ะจะหลุด ซึ่งเป็นบั๊กที่เจอตอนดึงข้อมูล Toro จริง
    """
    t = parse_hero_page("toro", "Toro", TORO)
    assert "Self Damage Reduction" in t.shields


def test_word_boundary_prevents_false_positives():
    """'Discharge' ต้องไม่ถูกนับเป็น 'charge' ของ mobility"""
    wt = "{{infobox hero\n|name=X\n}}\n{{SkillCard|name=A|type={{SkillTextID|red|Discharge}}}}\n"
    assert parse_hero_page("x", "X", wt).mobility == []


def test_several_tags_in_one_type_field_all_captured():
    t = parse_hero_page("rouie", "Rouie", ROUIE)
    assert "Teleport" in t.mobility
    assert "Heal" in t.sustain


def test_counts_every_skill_card():
    assert parse_hero_page("rouie", "Rouie", ROUIE).n_skills == 3


def test_evidence_is_json_friendly():
    ev = parse_hero_page("toro", "Toro", TORO).evidence()
    assert ev["damage_type"] == "physical"
    assert isinstance(ev["all_effects"], list)
    assert all(isinstance(x, str) for x in ev["all_effects"])


# ------------------------------------------- ไฟล์ประเมินต้องสอดคล้องกับสคีมา

ASSESSMENT = Path("configs/draft/hero_assessment.yaml")


@pytest.fixture(scope="module")
def assessment() -> dict:
    if not ASSESSMENT.exists():
        pytest.skip("ยังไม่มีไฟล์ประเมิน")
    return yaml.safe_load(ASSESSMENT.read_text(encoding="utf-8"))


def test_assessment_records_who_assessed_it(assessment):
    """ไฟล์ที่ไม่บอกว่าใครประเมิน ใช้ไม่ได้ตาม Blueprint §36"""
    assert assessment.get("assessed_by")
    assert assessment.get("assessed_on")


def test_every_entry_has_all_twelve_utility_fields(assessment):
    for hid, spec in assessment["heroes"].items():
        missing = [k for k in REQUIRED_UTILITY if k not in spec["utility"]]
        assert not missing, f"{hid} ขาด {missing}"


def test_every_rating_is_in_range(assessment):
    for hid, spec in assessment["heroes"].items():
        for k, v in list(spec["utility"].items()) + list(spec["scaling"].items()):
            assert 0 <= v <= 100, f"{hid}.{k} = {v}"


def test_enum_values_are_valid(assessment):
    for hid, spec in assessment["heroes"].items():
        for lane in spec["lane_roles"]:
            LaneRole(lane)
        DamageType(spec["damage"]["type"])
        for tag in spec.get("macro_tags", []):
            MacroTag(tag)
        assert spec["range"] in ("melee", "short", "long"), hid


def test_every_entry_explains_itself(assessment):
    """ทุกตัวต้องมี notes บอกเหตุผล ไม่ใช่ตัวเลขลอย ๆ"""
    for hid, spec in assessment["heroes"].items():
        assert (spec.get("notes") or "").strip(), f"{hid} ไม่มี notes"


# ---------------------------------------- heroes.yaml ต้องกำกับที่มาไว้ครบ


def test_filled_heroes_all_declare_where_the_numbers_came_from():
    db = HeroDB.load("configs/draft/heroes.yaml")
    for h in db.complete_heroes:
        assert h.filled_kind in ("human", "assistant", "derived"), h.id
        assert h.filled_by, h.id


def test_assistant_filled_heroes_are_traceable():
    """ค่าที่ AI ประเมินต้องชี้กลับไปที่หลักฐานได้เสมอ"""
    db = HeroDB.load("configs/draft/heroes.yaml")
    ai = [h for h in db.heroes if h.filled_kind == "assistant"]
    if not ai:
        pytest.skip("ยังไม่มีตัวที่ AI ประเมิน")
    for h in ai:
        assert h.notes and "hero_traits.json" in h.notes, h.id
