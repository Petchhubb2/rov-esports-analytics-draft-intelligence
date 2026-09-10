"""ทดสอบ config: layout, zones, params"""

from __future__ import annotations

import numpy as np
import pytest
from rov.config.layout import IconSpec, Layout, MinimapConfig, RectModel, TeamColor
from rov.config.params import ObjectiveTiming, Params
from rov.config.zones import ZoneMap
from rov.domain.geometry import Rect

ZONE_FILE = "configs/zones/rov_map_v1.yaml"


# ------------------------------------------------------------------ layout


def _minimal_minimap() -> MinimapConfig:
    return MinimapConfig(
        roi=RectModel(x=18, y=16, w=186, h=186),
        icon=IconSpec(diameter_px=(16, 24)),
        teams={
            "blue": TeamColor(hue=(95, 125)),
            "red": TeamColor(hue=(170, 10)),
        },
    )


def test_red_hue_range_wraps():
    assert TeamColor(hue=(170, 10)).wraps
    assert not TeamColor(hue=(95, 125)).wraps


def test_hue_outside_opencv_scale_rejected():
    with pytest.raises(ValueError, match="0-179"):
        TeamColor(hue=(0, 300))


def test_teams_must_have_both_colors():
    with pytest.raises(ValueError, match="ขาดสี"):
        MinimapConfig(
            roi=RectModel(x=0, y=0, w=10, h=10),
            icon=IconSpec(diameter_px=(4, 8)),
            teams={"blue": TeamColor(hue=(95, 125))},
        )


def test_homography_requires_reference_points():
    with pytest.raises(ValueError, match="homography_src"):
        MinimapConfig(
            roi=RectModel(x=0, y=0, w=10, h=10),
            transform="homography",
            icon=IconSpec(diameter_px=(4, 8)),
            teams={"blue": TeamColor(hue=(95, 125)), "red": TeamColor(hue=(0, 10))},
        )


def test_unanswered_phase0_lists_fog_question():
    lay = Layout(id="t", source_resolution=(1280, 720), minimap=_minimal_minimap())
    missing = lay.unanswered_phase0
    joined = " ".join(missing)
    assert "fog_of_war" in joined, "ต้องเตือนว่ายังไม่ได้ตอบคำถาม G1"
    assert "clock" in joined


def test_scaling_720p_to_1080p():
    lay = Layout(id="t", source_resolution=(1280, 720), minimap=_minimal_minimap())
    big = lay.scaled_to(1920, 1080)

    assert big.minimap.roi.x == 27  # 18 * 1.5
    assert big.minimap.roi.w == 279  # 186 * 1.5
    # ขนาด icon ต้องขยายตามด้วย ไม่ใช่ค้างที่ค่าเดิม
    assert big.minimap.icon.diameter_px == (24, 36)
    assert lay.minimap.roi.x == 18, "ต้องไม่แก้ layout ตัวเดิม"


def test_scaling_rejects_different_aspect_ratio():
    lay = Layout(id="t", source_resolution=(1280, 720), minimap=_minimal_minimap())
    with pytest.raises(ValueError, match="อัตราส่วนภาพ"):
        lay.scaled_to(1280, 1024)


def test_icon_nominal_area_between_bounds():
    spec = IconSpec(diameter_px=(16, 24))
    lo, hi = spec.area_range
    assert lo < spec.nominal_area < hi


def test_rect_crop_and_scale():
    img = np.arange(100 * 100, dtype=np.uint8).reshape(100, 100)
    r = Rect(10, 20, 30, 40)
    assert r.crop(img).shape == (40, 30)
    assert r.scaled(2.0) == Rect(20, 40, 60, 80)
    assert r.contains(15, 25)
    assert not r.contains(5, 25)


# ------------------------------------------------------------------- zones


def test_zone_lookup_matches_expected_regions():
    zm = ZoneMap.load(ZONE_FILE)
    assert zm.zone_at(0.05, 0.95) == "BASE_BLUE"
    assert zm.zone_at(0.95, 0.05) == "BASE_RED"
    assert zm.zone_at(0.70, 0.70) == "DRAGON_PIT"
    assert zm.zone_at(0.30, 0.30) == "SLAYER_PIT"


def test_objective_pits_are_on_opposite_river_halves():
    """หลุมสองหลุมต้องอยู่คนละครึ่งแม่น้ำ (docs/16-map-guide.md)"""
    zm = ZoneMap.load(ZONE_FILE)
    assert zm.region_of("DRAGON_PIT") != zm.region_of("SLAYER_PIT")
    # แต่ละหลุมต้องมีแอ่งแม่น้ำและวงรอบหลุมอยู่ฝั่งเดียวกับตัวเอง
    for pit in ("SLAYER", "DRAGON"):
        assert zm.region_of(f"{pit}_PIT") == zm.region_of(f"{pit}_PIT_APPROACH")
        assert zm.region_of(f"{pit}_PIT") == zm.region_of(f"RIVER_{pit}")


def test_the_two_diagonals_divide_different_things():
    """y = x แบ่งฝั่งทีม · x + y = 1 แบ่งฝั่งเลน — เคยสลับกันมาแล้ว

    ฐานทั้งสองอยู่บนเส้น x + y = 1 พอดีเพราะเลนกลางเชื่อมมัน
    ถ้าใช้ x + y แบ่งฝั่งทีม ฐานจะตกอยู่ตรงเส้นแบ่งและจัดฝั่งไม่ได้
    """
    zm = ZoneMap.load(ZONE_FILE)
    # ป่าฝั่งน้ำเงินต้องอยู่ครึ่ง y > x ทั้งคู่
    for zid in ("JUNGLE_BLUE_SLAYER", "JUNGLE_BLUE_DRAGON"):
        z = zm.get(zid)
        assert z is not None, zid
        pts = [p for poly in z.parts for p in poly]
        inside = sum(1 for x, y in pts if y > x)
        assert inside > len(pts) * 0.7, f"{zid} ควรอยู่ครึ่ง y > x เป็นหลัก"
    # หลุม Dark Slayer ต้องอยู่ครึ่ง x + y < 1 ตามชื่อเลนของมัน
    ds = zm.get("SLAYER_PIT")
    pts = [p for poly in ds.parts for p in poly]
    assert sum(1 for x, y in pts if x + y < 1) > len(pts) * 0.9


def test_zone_out_of_bounds_is_none():
    zm = ZoneMap.load(ZONE_FILE)
    assert zm.zone_at(-0.1, 0.5) is None
    assert zm.zone_at(1.5, 0.5) is None


def test_edge_distance_is_larger_at_zone_centre():
    """หาจุดกึ่งกลางจาก raster จริง ไม่ผูกกับพิกัดที่เขียนตายตัว

    เพราะ polygon สร้างใหม่ได้จาก scripts/gen_zone_map.py
    การเขียนพิกัดตายตัวจะพังทุกครั้งที่รูปร่างแมพเปลี่ยน
    """
    import numpy as np
    from rov.config.zones import RASTER_SIZE

    zm = ZoneMap.load(ZONE_FILE)
    zm.build()
    idx = zm._names.index("DRAGON_PIT")
    ys, xs = np.nonzero(zm._raster == idx)
    cx, cy = xs.mean() / RASTER_SIZE, ys.mean() / RASTER_SIZE

    centre = zm.edge_distance(cx, cy)
    # ขยับไปทางขอบของ zone เดียวกัน
    near_edge = max(
        zm.edge_distance(x / RASTER_SIZE, cy)
        for x in (xs.min() + 2, xs.max() - 2)
    )
    assert centre > near_edge


def test_batch_lookup_matches_single_lookup():
    zm = ZoneMap.load(ZONE_FILE)
    xs = np.array([0.05, 0.70, 0.30, np.nan])
    ys = np.array([0.95, 0.70, 0.30, 0.5])
    batch = zm.zones_at_batch(xs, ys)
    assert batch == ["BASE_BLUE", "DRAGON_PIT", "SLAYER_PIT", None]


def test_zone_polygon_must_be_normalized():
    with pytest.raises(ValueError, match="normalized"):
        ZoneMap.model_validate(
            {
                "version": 1,
                "zones": [
                    {"id": "X", "kind": "lane", "polygon": [[0, 0], [50, 0], [50, 50]]}
                ],
            }
        )


def test_map_coverage_is_reasonable():
    zm = ZoneMap.load(ZONE_FILE)
    cov = zm.coverage_fraction()
    assert 0.7 < cov <= 1.0, f"zone ครอบคลุมแมพ {cov:.0%} — น่าจะวาดไม่ครบหรือทับซ้อน"


# ------------------------------------------------------------------ params


def test_objective_timing_before_first_spawn():
    """ยืนยันจากหน้าแนะนำแผนที่ในเกม — ทั้งคู่เกิดนาทีที่ 2"""
    t = ObjectiveTiming()
    assert t.next_dragon(0.0) == 120.0
    assert t.next_slayer(0.0) == 120.0


def test_objective_alive_when_never_killed():
    t = ObjectiveTiming()
    assert t.next_dragon(300.0) == 0.0


def test_objective_respawn_after_kill():
    t = ObjectiveTiming()
    # dragon ถูกฆ่าที่ 125 วินาที คูลดาวน์ 3 นาที
    assert t.next_dragon(130.0, last_killed=125.0) == pytest.approx(175.0)
    # เลยเวลาเกิดใหม่แล้ว
    assert t.next_dragon(320.0, last_killed=125.0) == 0.0


def test_dragon_and_slayer_share_the_same_cadence():
    """จากเกมจริง ทั้งคู่เกิดนาทีที่ 2 และคูลดาวน์ 3 นาทีเท่ากัน"""
    t = ObjectiveTiming()
    assert t.dragon_first == t.slayer_first == 120.0
    assert t.dragon_interval == t.slayer_interval == 180.0


def test_god_slayer_arrives_at_minute_15():
    t = ObjectiveTiming()
    assert t.next_god_slayer(0.0) == 900.0
    assert not t.god_slayer_active(890.0)
    assert t.god_slayer_active(900.0)
    # คูลดาวน์ 3 นาที 30 วินาที
    assert t.next_god_slayer(920.0, last_killed=910.0) == pytest.approx(200.0)


def test_objective_timings_are_now_verified():
    """อ่านจากหน้าแนะนำแผนที่ในเกมโดยตรง ไม่ใช่เว็บภายนอกแล้ว"""
    t = ObjectiveTiming()
    assert t.verified is True
    assert "แนะนำแผนที่" in t.verified_from


def test_config_hash_changes_with_params():
    a = Params()
    b = Params()
    assert a.config_hash() == b.config_hash()
    b.detect.residual_threshold += 1
    assert a.config_hash() != b.config_hash()
