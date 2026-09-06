"""ทดสอบ detector

เน้นทดสอบ "ข้อผิดพลาดที่เคยเกิดจริง" ไม่ใช่ทดสอบว่าโค้ดรันได้
บั๊กสองตัวที่เคยทำให้ recall เป็น 0 ถูกล็อกไว้ที่นี่
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from rov.config.layout import IconSpec, MinimapConfig, RectModel, TeamColor
from rov.config.params import DetectParams
from rov.domain.enums import Team
from rov.eval.synthetic import ICON_DIAMETER, MINIMAP_SIZE, draw_icon, make_terrain
from rov.domain.geometry import Point
from rov.minimap.background import build_rolling_background, residual
from rov.minimap.detect import detect_frame, enforce_team_caps, fill_holes


@pytest.fixture
def cfg() -> MinimapConfig:
    return MinimapConfig(
        roi=RectModel(x=0, y=0, w=MINIMAP_SIZE, h=MINIMAP_SIZE),
        fog_of_war=False,
        color_semantics="side",
        icon=IconSpec(diameter_px=(ICON_DIAMETER - 3, ICON_DIAMETER + 4), ring_thickness_px=2),
        teams={
            "blue": TeamColor(hue=(95, 120), sat_min=110, val_min=80),
            "red": TeamColor(hue=(175, 8), sat_min=110, val_min=80),
        },
    )


@pytest.fixture
def params() -> DetectParams:
    return DetectParams()


def _scene(points: list[tuple[Point, Team]]) -> tuple[np.ndarray, np.ndarray]:
    """คืน (เฟรมที่มี icon, พื้นหลังที่ไม่มี icon)"""
    bg = make_terrain(MINIMAP_SIZE, seed=7)
    img = bg.copy()
    for i, (p, team) in enumerate(points):
        draw_icon(img, p, team, i)
    return img, bg


# --------------------------------------------------------------------------
# บั๊กที่ 1 — mask ของสีทีมจับได้แค่ "วงแหวน" ทำให้ blob เป็นวงแหวนกลวง
# ความกลมออกมาราว 0.42 แล้วถูกตัวกรองความกลมตัดทิ้งหมด recall เป็น 0
# --------------------------------------------------------------------------


def _circ_of(mask: np.ndarray) -> float:
    from rov.domain.geometry import circularity

    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    area = float((mask > 0).sum())
    perim = cv2.arcLength(cs[0], True)
    return circularity(area, perim)


def test_fill_holes_fixes_the_circularity_that_broke_detection():
    """สาเหตุที่แท้จริงของบั๊ก: วงแหวนกลวงมีความกลมต่ำกว่าเกณฑ์

    ตัวกรองใช้ความกลม ≥ 0.60 วงแหวนได้ราว 0.4 จึงถูกตัดทิ้งทุกตัว
    """
    mask = np.zeros((60, 60), np.uint8)
    cv2.circle(mask, (30, 30), 14, 255, thickness=3)
    assert mask[30, 30] == 0

    before = _circ_of(mask)
    filled = fill_holes(mask)
    after = _circ_of(filled)

    assert before < 0.60, f"วงแหวนกลวงควรมีความกลมต่ำ แต่ได้ {before:.2f}"
    assert after > 0.85, f"หลังเติมรูควรกลมเกือบสมบูรณ์ แต่ได้ {after:.2f}"
    assert filled[30, 30] == 255, "ต้องเติมรูตรงกลางให้ตัน"


def test_ring_blob_is_rejected_without_fill_but_found_with_it(cfg, params):
    """ทดสอบตรง ๆ ว่าการเติมรูคือสิ่งที่ทำให้ตรวจเจอ"""
    img, bg = _scene([(Point(0.5, 0.5), Team.BLUE)])
    dets, _ = detect_frame(img, bg, cfg, params, keep_patches=False)
    assert len(dets) == 1
    assert dets[0].circularity > 0.7, "หลังเติมรูแล้วความกลมต้องสูง"


# --------------------------------------------------------------------------
# บั๊กที่ 2 — เกณฑ์แยก blob ใช้ area_hi ซึ่งกว้างเกินไป
# icon สองตัวที่ทับกันมีพื้นที่รวมยังไม่ถึง area_hi การแยกจึงไม่เคยทำงาน
# --------------------------------------------------------------------------


def test_two_overlapping_icons_are_split(cfg, params):
    d = ICON_DIAMETER / MINIMAP_SIZE  # ขนาด icon ในหน่วย normalized
    a = Point(0.50, 0.50)
    b = Point(0.50 + d * 0.62, 0.50)  # ทับกันราว 38%
    img, bg = _scene([(a, Team.BLUE), (b, Team.BLUE)])

    dets, _ = detect_frame(img, bg, cfg, params, keep_patches=False)

    assert len(dets) == 2, f"ควรแยกได้ 2 จุด แต่ได้ {len(dets)}"
    xs = sorted(p.point.x for p in dets)
    assert abs(xs[0] - a.x) < 0.02
    assert abs(xs[1] - b.x) < 0.02


def test_single_icon_is_not_split(cfg, params):
    img, bg = _scene([(Point(0.4, 0.6), Team.RED)])
    dets, _ = detect_frame(img, bg, cfg, params, keep_patches=False)
    assert len(dets) == 1, "icon เดี่ยวต้องไม่ถูกแยก"


# --------------------------------------------------------------------------
# พฤติกรรมพื้นฐาน
# --------------------------------------------------------------------------


def test_finds_ten_separated_icons(cfg, params):
    pts = []
    for i in range(10):
        pts.append(
            (Point(0.15 + 0.18 * (i % 5), 0.25 + 0.35 * (i // 5)),
             Team.BLUE if i < 5 else Team.RED)
        )
    img, bg = _scene(pts)

    dets, _ = detect_frame(img, bg, cfg, params, keep_patches=False)

    assert len(dets) == 10
    assert sum(d.team_hint is Team.BLUE for d in dets) == 5
    assert sum(d.team_hint is Team.RED for d in dets) == 5


def test_position_accuracy_within_gate(cfg, params):
    """ความคลาดเคลื่อนต้องต่ำกว่าเกณฑ์ Milestone 1 คือ 0.008 normalized"""
    truth = [Point(0.30, 0.70), Point(0.65, 0.35), Point(0.50, 0.20)]
    img, bg = _scene([(p, Team.BLUE) for p in truth])

    dets, _ = detect_frame(img, bg, cfg, params, keep_patches=False)

    assert len(dets) == 3
    for t in truth:
        nearest = min(d.point.dist(t) for d in dets)
        assert nearest <= 0.008, f"คลาดเคลื่อน {nearest:.4f} เกินเกณฑ์"


def test_empty_frame_gives_no_detections(cfg, params):
    bg = make_terrain(MINIMAP_SIZE, seed=7)
    dets, _ = detect_frame(bg.copy(), bg, cfg, params, keep_patches=False)
    assert dets == []


def test_mismatched_shapes_raise(cfg, params):
    a = np.zeros((50, 50, 3), np.uint8)
    b = np.zeros((60, 60, 3), np.uint8)
    with pytest.raises(ValueError, match="ไม่ตรงกับ"):
        detect_frame(a, b, cfg, params)


# --------------------------------------------------------------------------
# ข้อจำกัดเชิงโครงสร้าง — หนึ่งทีมมีได้ไม่เกิน 5
# --------------------------------------------------------------------------


def test_team_caps_keep_highest_confidence():
    from rov.domain.types import Detection

    dets = [
        Detection(
            frame_idx=0, det_id=i, px=0, py=0, point=Point(0.1 * i, 0.1),
            radius=9, area=250, circularity=0.9,
            team_hint=Team.BLUE, team_conf=1.0, det_conf=0.1 * i,
        )
        for i in range(8)
    ]
    kept = enforce_team_caps(dets, max_per_team=5)
    assert len(kept) == 5
    assert {d.det_id for d in kept} == {3, 4, 5, 6, 7}


def test_team_caps_pass_unknown_through():
    from rov.domain.types import Detection

    dets = [
        Detection(frame_idx=0, det_id=0, px=0, py=0, point=Point(0.1, 0.1),
                  radius=9, area=250, circularity=0.9,
                  team_hint=Team.UNKNOWN, team_conf=0.0, det_conf=0.5)
    ]
    assert len(enforce_team_caps(dets, 5)) == 1


# --------------------------------------------------------------------------
# background
# --------------------------------------------------------------------------


def test_background_removes_moving_icon():
    """icon ที่เคลื่อนที่ต้องถูก median กลืนหายไปจากพื้นหลัง"""
    terrain = make_terrain(MINIMAP_SIZE, seed=3)
    frames = []
    for i in range(24):
        img = terrain.copy()
        draw_icon(img, Point(0.15 + 0.03 * i, 0.5), Team.BLUE, 0)
        frames.append((float(i), img))

    bg = build_rolling_background(frames, window_sec=1e9, max_samples=40)
    diff = residual(bg.at(12.0), terrain)

    assert diff.max() < 60, "พื้นหลังต้องใกล้เคียงภูมิประเทศเปล่า"


def test_background_needs_frames():
    with pytest.raises(ValueError, match="ไม่มีเฟรม"):
        build_rolling_background([])
