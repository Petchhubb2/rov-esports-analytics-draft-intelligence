"""ตรวจจับ hero icon บน minimap

ท่อ (ดู docs/04-vision-pipeline.md §4.2):

    crop -> upscale -> residual จาก background
                    -> team color mask
         -> รวม mask -> morphology -> connected components
         -> กรองด้วยขนาด/ความกลม -> แยก blob ที่ติดกัน -> ระบุทีม

ผลลัพธ์ยังไม่มี identity ใด ๆ การผูก slot เป็นหน้าที่ของ tracking เท่านั้น
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from rov.config.layout import MinimapConfig, TeamColor
from rov.config.params import DetectParams
from rov.domain.enums import Team
from rov.domain.geometry import Point, circularity
from rov.domain.types import Detection


@dataclass(slots=True)
class DetectDebug:
    """ข้อมูลระหว่างทาง สำหรับจูน threshold — เก็บเฉพาะเมื่อเปิดโหมด debug"""

    residual: np.ndarray | None = None
    team_mask: np.ndarray | None = None
    combined: np.ndarray | None = None
    rejected: list[tuple[float, float, str]] | None = None


def team_color_mask(hsv: np.ndarray, color: TeamColor) -> np.ndarray:
    """mask ของช่วงสีหนึ่งทีม — รองรับช่วง hue ที่คร่อมจุด 0 (สีแดง)"""
    lo_h, hi_h = color.hue
    if color.wraps:
        m1 = cv2.inRange(hsv, (lo_h, color.sat_min, color.val_min), (179, 255, 255))
        m2 = cv2.inRange(hsv, (0, color.sat_min, color.val_min), (hi_h, 255, 255))
        return cv2.bitwise_or(m1, m2)
    return cv2.inRange(hsv, (lo_h, color.sat_min, color.val_min), (hi_h, 255, 255))


def fill_holes(mask: np.ndarray) -> np.ndarray:
    """เติมรูในแต่ละ blob ให้ตัน

    จำเป็นเพราะ team color mask จับได้เฉพาะ "วงแหวน" รอบนอกของ icon
    ส่วนเนื้อในคือ portrait ของฮีโร่ซึ่งเป็นสีอะไรก็ได้
    ผลคือ blob ออกมาเป็นวงแหวนที่มีความกลม (circularity) ราว 0.4
    แล้วถูกตัวกรองความกลมตัดทิ้งทั้งหมด

    หลังเติมรูแล้ว วงแหวนกลายเป็นวงกลมตัน ความกลมขึ้นไปราว 0.9
    และพื้นที่ตรงกับขนาด icon จริง
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return mask
    filled = np.zeros_like(mask)
    cv2.drawContours(filled, contours, -1, 255, thickness=cv2.FILLED)
    return filled


def detect_frame(
    crop: np.ndarray,
    background: np.ndarray,
    cfg: MinimapConfig,
    params: DetectParams,
    frame_idx: int = 0,
    keep_patches: bool = True,
    debug: bool = False,
) -> tuple[list[Detection], DetectDebug]:
    """ตรวจ hero icon ในหนึ่งเฟรม

    crop และ background ต้องมีขนาดเท่ากันและเป็น BGR uint8
    """
    if crop.shape != background.shape:
        raise ValueError(
            f"ขนาด crop {crop.shape} ไม่ตรงกับ background {background.shape}"
        )

    up = max(1, params.upscale)
    if up > 1:
        # ขยายก่อนตรวจ เพราะ icon ที่ 18 px แทบไม่มีรายละเอียดให้ contour ใช้
        # INTER_CUBIC ให้ขอบที่เรียบกว่า INTER_LINEAR ซึ่งช่วยเรื่องความกลม
        crop_u = cv2.resize(crop, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC)
        bg_u = cv2.resize(background, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC)
    else:
        crop_u, bg_u = crop, background

    res = cv2.absdiff(crop_u, bg_u).max(axis=2)
    res_mask = (res >= params.residual_threshold).astype(np.uint8) * 255

    hsv = cv2.cvtColor(crop_u, cv2.COLOR_BGR2HSV)
    blue_m = team_color_mask(hsv, cfg.teams["blue"])
    red_m = team_color_mask(hsv, cfg.teams["red"])
    team_m = cv2.bitwise_or(blue_m, red_m)

    combined = cv2.bitwise_and(res_mask, team_m)

    k_open = np.ones((params.morph_open, params.morph_open), np.uint8)
    k_close = np.ones((params.morph_close, params.morph_close), np.uint8)
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, k_open)
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, k_close)
    combined = fill_holes(combined)

    # ตัดพื้นที่ป้อมออก เพราะป้อมมีสีทีมเหมือนกันและจางลงตลอดเกม
    if cfg.tower_positions:
        for t in cfg.tower_positions:
            r = t.to_rect().scaled(up)
            combined[r.y : r.y2, r.x : r.x2] = 0

    dets = _blobs_to_detections(
        combined, crop_u, cfg, params, frame_idx, up, keep_patches, debug
    )

    dbg = DetectDebug()
    if debug:
        dbg.residual = res
        dbg.team_mask = team_m
        dbg.combined = combined
    return dets, dbg


def _blobs_to_detections(
    mask: np.ndarray,
    crop_u: np.ndarray,
    cfg: MinimapConfig,
    params: DetectParams,
    frame_idx: int,
    up: int,
    keep_patches: bool,
    debug: bool,
) -> list[Detection]:
    h, w = mask.shape
    up2 = up * up
    area_lo, area_hi = cfg.icon.area_range
    area_lo *= up2
    area_hi *= up2
    single_area = cfg.icon.nominal_area * up2

    n, labels, stats, cents = cv2.connectedComponentsWithStats(mask, connectivity=8)
    out: list[Detection] = []
    det_id = 0

    for i in range(1, n):
        area = float(stats[i, cv2.CC_STAT_AREA])
        if area < area_lo * 0.5:
            continue

        comp = (labels == i).astype(np.uint8)

        # นับว่า blob นี้มี icon กี่ตัวทับกันอยู่ โดยใช้สองสัญญาณ
        #   พื้นที่   — icon มีขนาดสม่ำเสมอ พื้นที่จึงบอกจำนวนได้ตรง ๆ
        #   ยอดเขา   — distance transform เห็น "ก้อน" ที่ยังแยกกันได้
        # ใช้ค่าที่มากกว่า เพราะ icon ที่ทับกันมากทำให้พื้นที่ประเมินต่ำไป
        k_area = int(round(area / single_area))
        # ยอดสองยอดที่ใกล้กว่ารัศมี icon คือ icon ตัวเดียวกัน
        min_sep = 0.80 * float(np.sqrt(single_area / np.pi))
        peak_centers = _peak_centers(comp, min_sep=min_sep)
        k = max(1, min(params.max_per_team * 2, max(k_area, len(peak_centers))))

        if k == 1:
            centers = [(float(cents[i][0]), float(cents[i][1]))]
        elif len(peak_centers) == k:
            # ยอดเขาจาก distance transform ให้จุดศูนย์กลางที่ดีกว่า k-means
            # เพราะ k-means ดึงจุดศูนย์กลางเข้าหากันเมื่อวงกลมทับกัน
            centers = peak_centers
        else:
            centers = _split_blob(comp, k)

        if not centers:
            continue

        contours, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        perim = cv2.arcLength(contours[0], True) if contours else 0.0
        circ = circularity(area, perim) if len(centers) == 1 else 1.0

        if len(centers) == 1 and circ < params.min_circularity:
            continue

        per_area = area / len(centers)
        if not (area_lo * 0.5 <= per_area <= area_hi * 1.6):
            continue

        radius = float(np.sqrt(single_area / np.pi))

        for cx, cy in centers:
            team, tconf = _classify_team(crop_u, cx, cy, radius, cfg)
            patch = _extract_patch(crop_u, cx, cy, radius) if keep_patches else None
            out.append(
                Detection(
                    frame_idx=frame_idx,
                    det_id=det_id,
                    px=cx / up,
                    py=cy / up,
                    point=Point(x=(cx / up) / (w / up), y=(cy / up) / (h / up)),
                    radius=radius / up,
                    area=per_area / (up * up),
                    circularity=circ,
                    team_hint=team,
                    team_conf=tconf,
                    det_conf=_score(circ, per_area, area_lo, area_hi, tconf),
                    patch=patch,
                )
            )
            det_id += 1

    return out


def _peak_centers(
    comp: np.ndarray, min_sep: float, rel_thresh: float = 0.55
) -> list[tuple[float, float]]:
    """หาจุดศูนย์กลางของ icon แต่ละตัวใน blob ด้วย distance transform

    วงกลมที่ทับกันจะยังคงมี "ยอดเขา" คนละยอดใน distance transform
    ตราบใดที่ยังไม่ทับกันเกินราวครึ่งหนึ่ง

    หาด้วย local maxima (เทียบกับผลของ dilate) แทนการ threshold ค่าเดียว
    เพราะ threshold เดียวจะกลืนยอดที่เตี้ยกว่าเข้ากับยอดที่สูงกว่า

    min_sep  ระยะขั้นต่ำระหว่างยอด ยอดที่ใกล้กว่านี้ถือเป็นยอดเดียวกัน
             จำเป็นเพราะ distance transform ของ blob เล็กมักมีที่ราบ
             ทำให้เกิดยอดปลอมติดกันหลายยอด แล้วแยก blob เกินจริง
    """
    dist = cv2.distanceTransform(comp, cv2.DIST_L2, 5)
    dmax = float(dist.max())
    if dmax <= 0:
        return []

    k = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(dist, k)
    peaks = ((dist >= dilated - 1e-6) & (dist >= rel_thresh * dmax)).astype(np.uint8)

    n, _, _, cents = cv2.connectedComponentsWithStats(peaks, connectivity=8)
    raw = [(float(c[0]), float(c[1])) for c in cents[1:n]]
    if len(raw) <= 1:
        return raw

    # เรียงตามความสูงของยอด แล้วเก็บเฉพาะยอดที่ห่างจากยอดที่เก็บไว้แล้วพอ
    def height(p: tuple[float, float]) -> float:
        y = int(np.clip(p[1], 0, dist.shape[0] - 1))
        x = int(np.clip(p[0], 0, dist.shape[1] - 1))
        return float(dist[y, x])

    kept: list[tuple[float, float]] = []
    for p in sorted(raw, key=height, reverse=True):
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 >= min_sep**2 for q in kept):
            kept.append(p)
    return kept


def _split_blob(comp: np.ndarray, k: int) -> list[tuple[float, float]]:
    """แยก blob ที่ icon ทับกันออกเป็น k จุด ด้วย k-means บนพิกัด pixel

    ใช้เมื่อ distance transform ให้จำนวนยอดไม่ตรงกับที่พื้นที่บอก
    k-means ดึงจุดศูนย์กลางเข้าหากันเล็กน้อยเมื่อวงกลมทับกัน จึงเป็นทางเลือกรอง
    """
    ys, xs = np.nonzero(comp)
    if len(xs) == 0:
        return []
    if len(xs) < k:
        return [(float(xs.mean()), float(ys.mean()))]

    pts = np.column_stack([xs, ys]).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
    _, _, centers = cv2.kmeans(pts, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    return [(float(c[0]), float(c[1])) for c in centers]


def _classify_team(
    img: np.ndarray, cx: float, cy: float, radius: float, cfg: MinimapConfig
) -> tuple[Team, float]:
    """ระบุทีมจากสีวงแหวนรอบนอกของ icon

    ใช้เฉพาะวงแหวน ไม่ใช้เนื้อในทั้งหมด เพราะเนื้อในคือ portrait ของฮีโร่
    ซึ่งมีสีอะไรก็ได้ และจะทำให้การแยกทีมพลาด
    """
    h, w = img.shape[:2]
    r = max(2, int(round(radius)))
    x0, x1 = max(0, int(cx) - r), min(w, int(cx) + r + 1)
    y0, y1 = max(0, int(cy) - r), min(h, int(cy) + r + 1)
    if x1 <= x0 or y1 <= y0:
        return Team.UNKNOWN, 0.0

    patch = img[y0:y1, x0:x1]
    ring = np.zeros(patch.shape[:2], np.uint8)
    pc = ((x1 - x0) // 2, (y1 - y0) // 2)
    cv2.circle(ring, pc, r, 255, -1)
    cv2.circle(ring, pc, max(1, r - cfg.icon.ring_thickness_px), 0, -1)

    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    scores: dict[Team, float] = {}
    for name, team in (("blue", Team.BLUE), ("red", Team.RED)):
        m = cv2.bitwise_and(team_color_mask(hsv, cfg.teams[name]), ring)
        scores[team] = float(m.sum()) / 255.0

    total = sum(scores.values())
    if total <= 0:
        return Team.UNKNOWN, 0.0
    best = max(scores, key=lambda k: scores[k])
    return best, scores[best] / total


def _extract_patch(img: np.ndarray, cx: float, cy: float, radius: float) -> np.ndarray | None:
    """ตัด patch รอบ icon ไว้ทำ appearance matching ตอน tracking"""
    r = max(3, int(round(radius * 1.25)))
    h, w = img.shape[:2]
    x0, y0 = int(cx) - r, int(cy) - r
    x1, y1 = int(cx) + r + 1, int(cy) + r + 1
    if x0 < 0 or y0 < 0 or x1 > w or y1 > h:
        return None
    return img[y0:y1, x0:x1].copy()


def _score(circ: float, area: float, lo: float, hi: float, tconf: float) -> float:
    """คะแนนรวมของ detection — ยังไม่ calibrate เป็นความน่าจะเป็น

    ดู docs/01-assessment.md G10 — ต้องผ่าน reliability diagram ก่อน
    จึงจะเรียกตัวเลขนี้ว่า probability ได้
    """
    mid = (lo + hi) / 2.0
    area_fit = 1.0 - min(1.0, abs(area - mid) / max(mid, 1e-6))
    return float(np.clip(0.45 * circ + 0.30 * area_fit + 0.25 * tconf, 0.0, 1.0))


def enforce_team_caps(dets: list[Detection], max_per_team: int = 5) -> list[Detection]:
    """หนึ่งทีมมีได้ไม่เกิน 5 ตัว — ข้อจำกัดเชิงโครงสร้างที่แรงที่สุดที่เรามี

    เก็บตัวที่คะแนนสูงสุด ตัวที่เหลือทิ้ง
    ตัวที่ทีมยังไม่ชัด (UNKNOWN) ปล่อยผ่าน ให้ tracker ตัดสินจากบริบท
    """
    out: list[Detection] = []
    for team in (Team.BLUE, Team.RED):
        group = sorted(
            (d for d in dets if d.team_hint is team),
            key=lambda d: d.det_conf,
            reverse=True,
        )
        out.extend(group[:max_per_team])
    out.extend(d for d in dets if d.team_hint is Team.UNKNOWN)
    return sorted(out, key=lambda d: d.det_id)
