"""ทดสอบการดึงภาพประกอบ และ zone ที่มีหลายชิ้น"""

from __future__ import annotations

import pytest
from rov.config.zones import ZoneDef, ZoneMap
from rov.draft.importer.assets import _write_attribution, safe_filename

ZONE_FILE = "configs/zones/rov_map_v1.yaml"


# ------------------------------------------------------------- ชื่อไฟล์


def test_slash_in_hero_id_does_not_become_a_folder():
    """บั๊กจริง: ลิงก์หน้าย่อย Flowborn/Mage ทำให้เขียนไฟล์ไม่ได้"""
    assert "/" not in safe_filename("flowborn/mage")
    assert "\\" not in safe_filename("flowborn\\mage")
    assert safe_filename("flowborn/mage") == "flowborn_mage"


def test_apostrophe_and_space_are_replaced():
    assert safe_filename("eland'orr") == "eland_orr"
    assert safe_filename("bolt baron") == "bolt_baron"


def test_plain_id_is_unchanged():
    """id ปกติต้องไม่ถูกแตะ ไม่งั้นจะจับคู่กับข้อมูลไม่ได้"""
    for hid in ("elandorr", "sinestrea", "bolt_baron", "ybneth"):
        assert safe_filename(hid) == hid


def test_dangerous_paths_are_neutralised():
    for bad in ("../../etc/passwd", "..", "C:\\Windows\\system32"):
        out = safe_filename(bad)
        assert "/" not in out and "\\" not in out
        assert out not in ("", ".", "..")


def test_empty_id_gets_a_placeholder():
    assert safe_filename("///") == "unknown"


# ------------------------------------------------------------- attribution


def test_attribution_states_the_art_is_not_liquipedias(tmp_path):
    """ไฟล์ที่มาต้องบอกชัดว่าภาพเป็นของ Garena ไม่ใช่ CC-BY-SA"""
    _write_attribution(tmp_path)
    text = (tmp_path / "ATTRIBUTION.md").read_text(encoding="utf-8")
    assert "Garena" in text
    assert "CC-BY-SA" in text
    assert "เผยแพร่บนเว็บสาธารณะ" in text


# --------------------------------------------------------- zone หลายชิ้น


def test_zone_accepts_multiple_parts():
    z = ZoneDef(
        id="X", kind="lane",
        polygons=[
            [(0.0, 0.0), (0.2, 0.0), (0.2, 0.2)],
            [(0.8, 0.8), (1.0, 0.8), (1.0, 1.0)],
        ],
    )
    assert len(z.parts) == 2


def test_single_polygon_still_works():
    z = ZoneDef(id="X", kind="lane", polygon=[(0.0, 0.0), (0.2, 0.0), (0.2, 0.2)])
    assert len(z.parts) == 1


def test_zone_without_any_shape_is_rejected():
    with pytest.raises(ValueError, match="ต้องมี polygon"):
        ZoneDef(id="X", kind="lane")


def test_part_with_too_few_points_is_rejected():
    with pytest.raises(ValueError, match="น้อยกว่า 3"):
        ZoneDef(id="X", kind="lane", polygons=[[(0.0, 0.0), (0.1, 0.1)]])


def test_out_of_range_point_is_rejected():
    with pytest.raises(ValueError, match="normalized"):
        ZoneDef(id="X", kind="lane", polygons=[[(0.0, 0.0), (5.0, 0.0), (5.0, 5.0)]])


def test_both_halves_of_a_split_lane_are_rasterised():
    """เลนกลางถูกแม่น้ำตัดเป็นสองท่อน ทั้งสองท่อนต้องอยู่ใน raster

    ถ้าเก็บแค่ชิ้นใหญ่สุดจะเสียครึ่งเลนไปเงียบ ๆ
    """
    zm = ZoneMap.load(ZONE_FILE)
    mid = zm.get("MID")
    assert mid is not None
    assert len(mid.parts) >= 2, "MID ควรมีอย่างน้อยสองชิ้น"

    import numpy as np

    zm.build()
    idx = zm._names.index("MID")
    ys, xs = np.nonzero(zm._raster == idx)
    # ทั้งสองท่อนอยู่คนละฝั่งของจุดกึ่งกลาง
    assert xs.min() / zm._raster.shape[1] < 0.35
    assert xs.max() / zm._raster.shape[1] > 0.65


def test_generated_map_matches_confirmed_game_facts():
    """หลุม Dark Slayer กับ Abyssal Dragon อยู่คนละครึ่งแม่น้ำ

    ยืนยันจากหน้าแนะนำแผนที่ในเกม (docs/16-map-guide.md)
    ไม่มี Spirit Sentinel ในเกมปัจจุบัน — มอนสเตอร์ป่าใหญ่คือ
    Might Golem (DMG) กับ Sage Golem (Recovery)
    """
    zm = ZoneMap.load(ZONE_FILE)
    assert zm.region_of("DRAGON_PIT") != zm.region_of("SLAYER_PIT")
    assert zm.get("SPIRIT_SENTINEL") is None, "Spirit Sentinel ไม่มีในเกมปัจจุบัน"
    assert zm.get("MIGHT_GOLEM") is not None
    assert zm.get("SAGE_GOLEM") is not None


def test_generated_map_covers_almost_everything():
    zm = ZoneMap.load(ZONE_FILE)
    assert zm.coverage_fraction() > 0.98, "แมพที่สร้างจากกฎควรครอบคลุมเกือบทั้งหมด"


def test_map_is_marked_unverified():
    """ยังไม่ได้เทียบกับ minimap จริง ต้องไม่อ้างว่ายืนยันแล้ว"""
    import yaml

    doc = yaml.safe_load(open(ZONE_FILE, encoding="utf-8"))
    assert doc.get("verified") is False
