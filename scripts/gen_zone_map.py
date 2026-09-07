"""สร้าง zone polygon จากกฎเรขาคณิต แทนการเดาพิกัดด้วยมือ

ทำไมต้องสร้างจากกฎ
    polygon ชุดแรกเขียนพิกัดด้วยมือ พอ render ออกมาดูแล้วพบว่าทับกันมั่ว
    lane วาดทับ jungle จน zone ที่วาดทีหลังกลืนของเดิม และรูปร่างไม่เหมือนแมพจริง

วิธีนี้วาดเป็นภาพ label ตามกฎก่อน แล้วค่อยดึง contour ออกมาเป็น polygon
จึงรับประกันว่า zone ไม่ทับกัน และรูปร่างสอดคล้องกันทั้งแมพ

โครงสร้างที่ยืนยันแล้ว (docs/16-map-guide.md — จากหน้าแนะนำแผนที่ในเกม)
    3 เลน · แม่น้ำผ่ากลาง · ป่า 4 ส่วนต่อฝั่ง
    Dark Slayer กับ Abyssal Dragon อยู่คนละครึ่งแม่น้ำ
    God Slayer สุ่มไปแทนที่หลุมใดหลุมหนึ่ง ไม่มีหลุมของตัวเอง

⚠️ ทิศทางของแมพ (ฐานน้ำเงินมุมไหน เลนไหนอยู่บน) ยังต้องยืนยันกับ minimap จริง
   ถ้าผิด ให้แก้ค่าคงที่ด้านล่างแล้วรันใหม่ ไม่ต้องแก้ polygon ทีละจุด
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "core"))

from rov.cli.console import setup_console  # noqa: E402

N = 1024  # ความละเอียดตอนวาด ยิ่งสูง contour ยิ่งเรียบ

# ── ค่าที่กำหนดรูปร่างแมพ (หน่วย normalized) ────────────────────────────
LANE_W = 0.085      # ครึ่งความกว้างของเลน
RIVER_W = 0.075     # ครึ่งความกว้างของแม่น้ำ
BASE_R = 0.155      # รัศมีฐาน
PIT_R = 0.058       # รัศมีหลุม objective
APPROACH_R = 0.115  # รัศมีพื้นที่รอบหลุม
EDGE = 0.075        # ระยะจากขอบแมพถึงกึ่งกลางเลนริม

# ฐานน้ำเงินมุมซ้ายล่าง ฐานแดงมุมขวาบน
BLUE_BASE = (0.06, 0.94)
RED_BASE = (0.94, 0.06)

# หลุม objective อยู่ในแม่น้ำ คนละครึ่งกัน
#
# ยืนยันจากหน้าแนะนำแผนที่ในเกม (docs/16-map-guide.md)
#   Dark Slayer     เกิดนาทีที่ 2 คูลดาวน์ 3 นาที
#   Abyssal Dragon  เกิดนาทีที่ 2 คูลดาวน์ 3 นาที
#   God Slayer      เกิดนาทีที่ 15 แล้ว "สุ่มไปแทนที่" หลุมใดหลุมหนึ่งในสองหลุมนี้
#                   จึงไม่มีหลุมของตัวเอง
#
# ไม่มี Spirit Sentinel ในเกมปัจจุบัน — เอกสารเดิมอ้างจากเว็บภายนอกที่เก่ากว่า
# มอนสเตอร์ป่าใหญ่สองตัวคือ Might Golem (DMG) กับ Sage Golem (Recovery)
SLAYER_PIT = (0.30, 0.30)     # ครึ่งบนซ้ายของแม่น้ำ ฝั่งเดียวกับ DS lane
DRAGON_PIT = (0.70, 0.70)     # ครึ่งล่างขวา ฝั่งเดียวกับ Dragon lane
MIGHT_GOLEM = (0.40, 0.20)    # มอนสเตอร์ป่าใหญ่ ฝั่งเดียวกับ Slayer
SAGE_GOLEM = (0.60, 0.80)     # ฝั่งเดียวกับ Dragon

ZONES = [
    # (id, kind, region) — ลำดับสำคัญ วาดทีหลังทับของเดิม
    ("JUNGLE_BLUE_TOP", "jungle", "TOP_SIDE"),
    ("JUNGLE_BLUE_BOT", "jungle", "BOT_SIDE"),
    ("JUNGLE_RED_TOP", "jungle", "TOP_SIDE"),
    ("JUNGLE_RED_BOT", "jungle", "BOT_SIDE"),
    ("DS_LANE", "lane", "TOP_SIDE"),
    ("MID", "lane", "MID"),
    ("DRAGON_LANE", "lane", "BOT_SIDE"),
    ("RIVER_TOP", "river", "TOP_SIDE"),
    ("RIVER_BOTTOM", "river", "BOT_SIDE"),
    ("BASE_BLUE", "base", "BASE_BLUE"),
    ("BASE_RED", "base", "BASE_RED"),
    ("SLAYER_PIT_APPROACH", "approach", "TOP_SIDE"),
    ("DRAGON_PIT_APPROACH", "approach", "BOT_SIDE"),
    ("MIGHT_GOLEM", "objective", "TOP_SIDE"),
    ("SAGE_GOLEM", "objective", "BOT_SIDE"),
    ("SLAYER_PIT", "objective", "TOP_SIDE"),
    ("DRAGON_PIT", "objective", "BOT_SIDE"),
]
IDX = {z[0]: i + 1 for i, z in enumerate(ZONES)}


def build_labels() -> np.ndarray:
    """วาดภาพ label ตามกฎ — ค่าที่ทับทีหลังชนะ"""
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / (N - 1)
    lab = np.zeros((N, N), np.uint16)

    # เส้นแบ่งสองอย่าง
    #   mid      แนวทแยงจากซ้ายล่างไปขวาบน   x + y = 1
    #   river    แนวทแยงตรงข้าม              y - x = 0
    d_mid = np.abs(xx + yy - 1.0) / np.sqrt(2)
    d_river = np.abs(yy - xx) / np.sqrt(2)
    blue_half = (xx + yy) < 1.0          # ครึ่งของทีมน้ำเงิน
    top_half = yy < xx                   # ครึ่งบน (ฝั่ง DS lane)

    # ป่าสี่ส่วน แบ่งด้วยเส้นทแยงทั้งสอง
    lab[blue_half & top_half] = IDX["JUNGLE_BLUE_TOP"]
    lab[blue_half & ~top_half] = IDX["JUNGLE_BLUE_BOT"]
    lab[~blue_half & top_half] = IDX["JUNGLE_RED_TOP"]
    lab[~blue_half & ~top_half] = IDX["JUNGLE_RED_BOT"]

    # เลนริมสองเส้น เป็นรูปตัว L ตามขอบแมพ
    ds = np.minimum(np.abs(xx - EDGE), np.abs(yy - EDGE))
    dragon = np.minimum(np.abs(xx - (1 - EDGE)), np.abs(yy - (1 - EDGE)))
    lab[ds < LANE_W] = IDX["DS_LANE"]
    lab[dragon < LANE_W] = IDX["DRAGON_LANE"]
    lab[d_mid < LANE_W] = IDX["MID"]

    # แม่น้ำวาดทับเลน แล้วแบ่งครึ่งด้วยเส้น mid
    river = d_river < RIVER_W
    lab[river & top_half] = IDX["RIVER_TOP"]
    lab[river & ~top_half] = IDX["RIVER_BOTTOM"]

    # ฐานสองมุม
    for (cx, cy), key in ((BLUE_BASE, "BASE_BLUE"), (RED_BASE, "BASE_RED")):
        lab[((xx - cx) ** 2 + (yy - cy) ** 2) < BASE_R**2] = IDX[key]

    # พื้นที่รอบหลุม แล้วค่อยวาดหลุมทับ
    for (cx, cy), key in (
        (SLAYER_PIT, "SLAYER_PIT_APPROACH"),
        (DRAGON_PIT, "DRAGON_PIT_APPROACH"),
    ):
        lab[((xx - cx) ** 2 + (yy - cy) ** 2) < APPROACH_R**2] = IDX[key]
    for (cx, cy), key in (
        (MIGHT_GOLEM, "MIGHT_GOLEM"),
        (SAGE_GOLEM, "SAGE_GOLEM"),
        (SLAYER_PIT, "SLAYER_PIT"),
        (DRAGON_PIT, "DRAGON_PIT"),
    ):
        lab[((xx - cx) ** 2 + (yy - cy) ** 2) < PIT_R**2] = IDX[key]

    return lab


# ชิ้นที่เล็กกว่านี้ถือเป็นเศษจากการ rasterize ไม่ใช่ส่วนหนึ่งของ zone จริง
MIN_PART_FRACTION = 0.0008


def to_polygons(lab: np.ndarray) -> dict[str, list[list[list[float]]]]:
    """ดึง contour **ทุกชิ้น** ของแต่ละ zone แล้วลดจำนวนจุดลง

    ต้องเก็บทุกชิ้นเพราะเลนกลางถูกแม่น้ำตัดเป็นสองท่อน
    ถ้าเก็บแค่ชิ้นใหญ่สุดจะเสียครึ่งเลนไปเงียบ ๆ
    """
    out: dict[str, list[list[list[float]]]] = {}
    min_area = MIN_PART_FRACTION * N * N
    for zid, idx in IDX.items():
        mask = (lab == idx).astype(np.uint8)
        if not mask.any():
            continue
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        parts = []
        for c in sorted(cnts, key=cv2.contourArea, reverse=True):
            if cv2.contourArea(c) < min_area:
                continue
            eps = 0.004 * cv2.arcLength(c, True)
            poly = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
            if len(poly) < 3:
                continue
            parts.append([
                [round(float(x) / (N - 1), 4), round(float(y) / (N - 1), 4)]
                for x, y in poly
            ])
        if parts:
            out[zid] = parts
    return out


def main() -> int:
    setup_console()
    lab = build_labels()
    polys = to_polygons(lab)

    doc = {
        "version": 2,
        "verified": False,
        "generated_by": "scripts/gen_zone_map.py",
        "zones": [
            {
                "id": zid,
                "kind": kind,
                "region": region,
                "polygons": polys[zid],
            }
            for zid, kind, region in ZONES
            if zid in polys
        ],
    }
    for z in doc["zones"]:
        if z["id"].endswith("_PIT"):
            z["parent"] = None
    for z in doc["zones"]:
        if z["id"] == "SLAYER_PIT_APPROACH":
            z["parent"] = "SLAYER_PIT"
        if z["id"] == "DRAGON_PIT_APPROACH":
            z["parent"] = "DRAGON_PIT"
    for z in doc["zones"]:
        if z.get("parent") is None:
            z.pop("parent", None)

    out = Path("configs/zones/rov_map_v1.yaml")
    header = (
        "# Zone map ของ Antaris Battlefield (RoV 5v5)\n"
        "#\n"
        "# สร้างอัตโนมัติด้วย scripts/gen_zone_map.py — อย่าแก้ทีละจุดด้วยมือ\n"
        "# ถ้ารูปร่างไม่ตรงกับ minimap จริง ให้แก้ค่าคงที่ในสคริปต์แล้วรันใหม่\n"
        "#\n"
        "# ⚠️ verified: false — ยังไม่ได้เทียบกับ minimap จริงจากคลิปแข่ง\n"
        "#    ทิศทางที่สมมติไว้: ฐานน้ำเงินมุมซ้ายล่าง ฐานแดงมุมขวาบน\n"
        "#    แม่น้ำจากซ้ายบนไปขวาล่าง เลนกลางตัดขวางที่จุดกึ่งกลาง\n"
        "#\n"
        "# พิกัด normalized 0..1  (0,0) = ซ้ายบน  (1,1) = ขวาล่าง\n\n"
    )
    out.write_text(
        header + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )

    counts = {zid: int((lab == idx).sum()) for zid, idx in IDX.items()}
    total = N * N
    print(f"เขียน {out}")
    print(f"zone {len(doc['zones'])} · ครอบคลุม {sum(counts.values())/total:.1%}")
    print()
    for zid, _kind, _r in ZONES:
        parts = polys.get(zid, [])
        pts = sum(len(p) for p in parts)
        print(f"  {zid:<22} {counts.get(zid, 0)/total:>6.2%}  {len(parts)} ชิ้น {pts} จุด")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
