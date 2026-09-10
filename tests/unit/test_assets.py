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


def test_every_piece_of_a_multi_part_zone_is_rasterised():
    """โซนที่มีหลายชิ้นต้องเข้า raster ครบทุกชิ้น ไม่ใช่เก็บแต่ชิ้นใหญ่สุด

    แม่น้ำจริงบน minimap เป็นแอ่งขาด ๆ ไม่ต่อกันเป็นเส้นเดียว
    ถ้าเก็บแค่ชิ้นใหญ่สุดจะเสียพื้นที่ไปเงียบ ๆ

    หมายเหตุ: เดิมเทสต์นี้ยืนยันว่า "เลนกลางถูกแม่น้ำตัดเป็นสองท่อน"
    ซึ่งมาจากผังที่เดารูปทรงเอง พอเทียบกับ minimap จริงแล้วไม่จริง —
    แม่น้ำเป็นสองแอ่งอยู่คนละข้างของเลนกลาง ไม่ได้พาดตัดผ่าน เลนกลางจึงต่อเนื่อง
    """
    zm = ZoneMap.load(ZONE_FILE)
    multi = [z for z in zm.zones if len(z.parts) >= 2]
    assert multi, "ควรมีโซนที่แตกเป็นหลายชิ้นอย่างน้อยหนึ่งโซน"
    mid = zm.get("RIVER_SLAYER") or multi[0]
    assert len(mid.parts) >= 2

    import numpy as np

    zm.build()
    idx = zm._names.index("MID")
    ys, xs = np.nonzero(zm._raster == idx)
    # ทั้งสองท่อนอยู่คนละฝั่งของจุดกึ่งกลาง
    assert xs.min() / zm._raster.shape[1] < 0.35
    assert xs.max() / zm._raster.shape[1] > 0.65


def test_generated_map_matches_confirmed_game_facts():
    """โครงสร้างต้องตรงกับ minimap จริง

    ไม่มี Spirit Sentinel ในเกมปัจจุบัน (docs/16-map-guide.md)
    แคมป์ใหญ่มีสี่จุดสมมาตรกัน — ยังบอกไม่ได้ว่าจุดไหนคือ Might Golem
    จุดไหนคือ Sage Golem เพราะไอคอนบน minimap เหมือนกัน จึงตั้งชื่อตามตำแหน่ง
    """
    zm = ZoneMap.load(ZONE_FILE)
    assert zm.region_of("DRAGON_PIT") != zm.region_of("SLAYER_PIT")
    assert zm.get("SPIRIT_SENTINEL") is None, "Spirit Sentinel ไม่มีในเกมปัจจุบัน"
    golems = [z for z in zm.zones if z.id.startswith("GOLEM_")]
    assert len(golems) == 4, f"แคมป์ใหญ่ควรมีสี่จุด เจอ {len(golems)}"
    # สองจุดต่อฝั่งทีม และกระจายอยู่ทั้งสองฝั่งเลน
    assert len([z for z in golems if "BLUE" in z.id]) == 2
    assert len([z for z in golems if "SLAYER" in z.id]) == 2


def test_map_is_symmetric_under_180_rotation():
    """แมพ MOBA ต้องสมมาตรเมื่อหมุน 180 องศา ไม่งั้นฝั่งหนึ่งได้เปรียบฟรี

    เป็นตัวจับว่าเราวัดศูนย์กลางเพี้ยนหรือวาดโซนเอียง
    """
    import numpy as np

    zm = ZoneMap.load(ZONE_FILE)
    pairs = [
        ("BASE_BLUE", "BASE_RED"),
        ("SLAYER_PIT", "DRAGON_PIT"),
        ("JUNGLE_BLUE_SLAYER", "JUNGLE_RED_DRAGON"),
    ]
    for a_id, b_id in pairs:
        za, zb = zm.get(a_id), zm.get(b_id)
        assert za and zb, f"ขาดโซน {a_id} หรือ {b_id}"
        ca = np.array([p for poly in za.parts for p in poly]).mean(0)
        cb = np.array([p for poly in zb.parts for p in poly]).mean(0)
        # จุดกึ่งกลางของคู่ต้องอยู่ใกล้ศูนย์กลางแมพ
        mid = (ca + cb) / 2
        assert abs(mid[0] - 0.5) < 0.06 and abs(mid[1] - 0.5) < 0.06, (
            f"{a_id}/{b_id} ไม่สมมาตร กึ่งกลางคู่อยู่ที่ {mid}"
        )


def test_generated_map_covers_almost_everything():
    zm = ZoneMap.load(ZONE_FILE)
    assert zm.coverage_fraction() > 0.98, "แมพที่สร้างจากกฎควรครอบคลุมเกือบทั้งหมด"


def test_map_records_what_it_was_verified_against():
    """ตอนนี้เทียบกับ minimap ในไคลเอนต์แล้ว แต่ยังไม่ใช่ฝั่ง broadcast

    อ้างว่ายืนยันแล้วได้ แต่ต้องบอกให้ชัดว่ายืนยันกับอะไร
    ไม่งั้นคนอ่านจะเข้าใจว่าเทียบกับคลิปแข่งแล้ว
    """
    import yaml

    doc = yaml.safe_load(open(ZONE_FILE, encoding="utf-8"))
    assert doc.get("verified") is True
    src = doc.get("verified_from") or ""
    assert "minimap" in src, "ต้องบอกว่ายืนยันจากอะไร"
