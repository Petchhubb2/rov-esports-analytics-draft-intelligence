"""สร้างผังโซนจาก minimap จริง

**ต่างจากเวอร์ชันก่อนตรงไหน**

เวอร์ชันก่อนสร้างรูปทรงจากกฎล้วน ๆ โดยเดาว่าแมพหน้าตาแบบไหน
เวอร์ชันนี้ยึดจากค่าที่ **วัดได้จริง** บน minimap ในเกม
(scripts/build_minimap.py -> data/assets/map/minimap_meta.json)

    ศูนย์กลางสนาม   หาจากความสมมาตร 180 องศาของป้อมสองฝั่ง
    ฐานทั้งสอง      จากตำแหน่งแกนกลางที่ตรวจเจอ
    หลุมทั้งสอง     Dark Slayer (0.334, 0.286)  Abyssal Dragon (0.661, 0.715)
                    ยืนยันกันเองด้วยความสมมาตร ต่างกันแค่ 0.005
    แม่น้ำ          ใช้ **หน้ากากจากภาพจริง** ไม่ใช่รูปทรงที่สมมติขึ้น
    เส้นเลน         ลากผ่านตำแหน่งป้อมที่ตรวจเจอ

**เรขาคณิตของแมพที่วัดได้**

    ฐานน้ำเงินมุมซ้ายล่าง (0.093, 0.916)   ฐานแดงมุมขวาบน (0.907, 0.102)
    เลนกลางวางตัวตามแนวทแยง x + y = 1  (เชื่อมสองฐาน)
    แม่น้ำวางตัวตามแนวทแยง y = x  (ตั้งฉากกับเลนกลาง) แบ่งเป็นสองแอ่ง
    เลนข้างเป็นรูปตัว L เลียบขอบแมพ ไม่ใช่เส้นทแยง

**สองแนวทแยงนี้แบ่งคนละเรื่องกัน — เคยสับสนตรงนี้มาแล้ว**

    y = x       แบ่ง "ฝั่งทีม"  ทีมน้ำเงิน y > x   ทีมแดง y < x
    x + y = 1   แบ่ง "ฝั่งเลน"  ฝั่ง Dark Slayer x+y < 1   ฝั่ง Dragon x+y > 1

ฐานทั้งสองอยู่บนเส้น x + y = 1 พอดี เพราะเลนกลางเชื่อมมันโดยตรง
จะใช้ x + y เป็นตัวแบ่งฝั่งทีมไม่ได้เด็ดขาด ต้องใช้ y - x
ยืนยันจากหลุม — Dark Slayer อยู่ที่ x+y = 0.62 (ฝั่ง DS lane)
Abyssal Dragon อยู่ที่ x+y = 1.38 (ฝั่ง Dragon lane) ตรงกับชื่อเลนพอดี

วิธีทำ: วาด label ลง raster ตามลำดับความสำคัญ แล้วดึง contour ออกมาเป็น polygon
ทำให้ polygon ของแม่น้ำมีรูปร่างตามของจริง ไม่ใช่สี่เหลี่ยมที่สมมติเอา

รัน:  python scripts/gen_zone_map.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

META = Path("data/assets/map/minimap_meta.json")
RIVER_MASK = Path("data/exports/mapwork/board_river.png")
OUT = Path("configs/zones/rov_map_v1.yaml")
N = 900  # ความละเอียดที่ใช้วาด

# ── ค่าที่ปรับได้ ทั้งหมดเป็นสัดส่วนของด้านแมพ ──
#
# ค่าชุดก่อนตั้งกว้างเกินจริงมาก เลนข้างสองเลนกินไป 33% ของแมพ
# ป่าเหลือแค่ 5-6% ต่อส่วน ทั้งที่บน minimap จริงป่าเป็นพื้นที่ส่วนใหญ่
# รอบนี้แคบลงและ LANE_INSET คำนวณจากตำแหน่งป้อมจริงแทนการตั้งเอง
MID_HALF_WIDTH = 0.058      # ครึ่งความกว้างของเลนกลาง วัดตั้งฉากกับแนวทแยง
LANE_HALF_WIDTH = 0.046     # ครึ่งความกว้างของเลนข้าง
LANE_INSET_FALLBACK = 0.045  # ใช้เมื่อหาป้อมริมขอบไม่เจอ
BASE_RADIUS = 0.140         # รัศมีเขตฐาน ครอบแกนกลางกับป้อมฐานพอดี
PIT_RADIUS = 0.062          # รัศมีหลุม objective
APPROACH_RADIUS = 0.115     # รัศมีวงรอบหลุม ใช้จับการเซ็ตอัพ
EDGE_BAND = 0.13            # ป้อมที่อยู่ในแถบนี้จากขอบ ถือว่าเป็นป้อมริมขอบ

ZONES: list[tuple[str, str, str]] = [
    # id, kind, region
    ("BASE_BLUE", "base", "BASE_BLUE"),
    ("BASE_RED", "base", "BASE_RED"),
    ("SLAYER_PIT", "objective", "SLAYER_SIDE"),
    ("DRAGON_PIT", "objective", "DRAGON_SIDE"),
    ("SLAYER_PIT_APPROACH", "approach", "SLAYER_SIDE"),
    ("DRAGON_PIT_APPROACH", "approach", "DRAGON_SIDE"),
    ("RIVER_SLAYER", "river", "SLAYER_SIDE"),
    ("RIVER_DRAGON", "river", "DRAGON_SIDE"),
    ("MID", "lane", "MID"),
    ("DS_LANE", "lane", "SLAYER_SIDE"),
    ("DRAGON_LANE", "lane", "DRAGON_SIDE"),
    ("GOLEM_BLUE_SLAYER", "objective", "SLAYER_SIDE"),
    ("GOLEM_BLUE_DRAGON", "objective", "DRAGON_SIDE"),
    ("GOLEM_RED_SLAYER", "objective", "SLAYER_SIDE"),
    ("GOLEM_RED_DRAGON", "objective", "DRAGON_SIDE"),
    ("JUNGLE_BLUE_SLAYER", "jungle", "SLAYER_SIDE"),
    ("JUNGLE_BLUE_DRAGON", "jungle", "DRAGON_SIDE"),
    ("JUNGLE_RED_SLAYER", "jungle", "SLAYER_SIDE"),
    ("JUNGLE_RED_DRAGON", "jungle", "DRAGON_SIDE"),
]

GOLEM_RADIUS = 0.055


def lane_inset(meta: dict) -> float:
    """ระยะจากขอบแมพถึงเส้นกลางเลนข้าง วัดจากป้อมที่ตั้งอยู่ริมขอบจริง

    ป้อมตั้งอยู่บนเลนพอดี จึงเป็นตัวชี้เส้นเลนที่แม่นที่สุดที่เรามี
    ดีกว่าตั้งค่าเองแล้วมาปรับตาทีหลัง
    """
    d = []
    for key in ("structures_blue", "structures_red"):
        for c in meta.get(key) or []:
            x, y = c["x"], c["y"]
            for v in (x, 1 - x, y, 1 - y):
                if v <= EDGE_BAND:
                    d.append(v)
    if not d:
        return LANE_INSET_FALLBACK
    return float(np.median(d))


def _grid() -> tuple[np.ndarray, np.ndarray]:
    a = (np.arange(N) + 0.5) / N
    return np.meshgrid(a, a)  # xs, ys


def build_labels(meta: dict) -> np.ndarray:
    xs, ys = _grid()
    idx = {z[0]: i + 1 for i, z in enumerate(ZONES)}
    lab = np.zeros((N, N), np.uint16)

    def put(name: str, mask: np.ndarray) -> None:
        lab[(lab == 0) & mask] = idx[name]

    def anchor(key: str, fallback: tuple[float, float]) -> tuple[float, float]:
        items = meta.get(key) or []
        if not items:
            return fallback
        big = max(items, key=lambda d: d["area"])
        return big["x"], big["y"]

    slayer = anchor("slayer_pit", (0.334, 0.286))
    dragon = anchor("dragon_pit", (0.661, 0.715))

    # ฐาน — เอาแกนกลาง (ก้อนใหญ่สุด) ของแต่ละฝั่ง
    def base_of(key: str, fallback: tuple[float, float]) -> tuple[float, float]:
        items = meta.get(key) or []
        if not items:
            return fallback
        big = max(items, key=lambda d: d["area"])
        return big["x"], big["y"]

    bb = base_of("structures_blue", (0.093, 0.916))
    br = base_of("structures_red", (0.907, 0.102))

    def disc(cx: float, cy: float, r: float) -> np.ndarray:
        return (xs - cx) ** 2 + (ys - cy) ** 2 <= r * r

    # ระยะเชิงเส้นถึงแนวทแยงสองเส้น (หารด้วย sqrt(2) ให้เป็นระยะจริง)
    d_mid = np.abs(xs + ys - 1.0) / np.sqrt(2.0)   # 0 = อยู่บนเลนกลาง
    d_river = np.abs(ys - xs) / np.sqrt(2.0)       # 0 = อยู่บนแนวแม่น้ำ

    # ตัวแบ่งสองแบบที่ห้ามสลับกัน (ดู docstring ด้านบน)
    blue_half = ys > xs          # ฝั่งทีมน้ำเงิน แบ่งด้วยแม่น้ำ
    slayer_half = xs + ys < 1.0  # ฝั่ง Dark Slayer แบ่งด้วยเลนกลาง

    # ── ลำดับสำคัญ: ฐาน > หลุม > แม่น้ำจริง > รอบหลุม > เลน > ป่า ──
    put("BASE_BLUE", disc(*bb, BASE_RADIUS))
    put("BASE_RED", disc(*br, BASE_RADIUS))
    put("SLAYER_PIT", disc(*slayer, PIT_RADIUS))
    put("DRAGON_PIT", disc(*dragon, PIT_RADIUS))

    # แม่น้ำจากภาพจริง แบ่งสองแอ่งด้วยแนวเลนกลาง
    if RIVER_MASK.exists():
        rm = cv2.imread(str(RIVER_MASK), cv2.IMREAD_GRAYSCALE)
        rm = cv2.resize(rm, (N, N), interpolation=cv2.INTER_NEAREST) > 127
        print(f"ใช้หน้ากากแม่น้ำจากภาพจริง ({100*rm.mean():.1f}% ของแมพ)")
    else:
        # สำรอง ถ้ายังไม่ได้รัน build_minimap.py
        rm = d_river <= 0.085
        print("ไม่พบหน้ากากแม่น้ำ ใช้แถบตามแนวทแยงแทน")
    put("RIVER_SLAYER", rm & slayer_half)
    put("RIVER_DRAGON", rm & ~slayer_half)

    # แคมป์ใหญ่วาดก่อนวงรอบหลุมและก่อนเลน
    # ถ้าวาดทีหลังจะโดนกลืนหายไปทั้งก้อน เพราะบางจุดอยู่ชิดทั้งสองอย่าง
    for c in meta.get("big_camps") or []:
        cxx, cyy = c["x"], c["y"]
        side = "BLUE" if cyy > cxx else "RED"
        half = "SLAYER" if cxx + cyy < 1.0 else "DRAGON"
        put(f"GOLEM_{side}_{half}", disc(cxx, cyy, GOLEM_RADIUS))

    put("SLAYER_PIT_APPROACH", disc(*slayer, APPROACH_RADIUS))
    put("DRAGON_PIT_APPROACH", disc(*dragon, APPROACH_RADIUS))

    # เลนกลาง — แถบตามแนวทแยงที่เชื่อมสองฐาน
    put("MID", d_mid <= MID_HALF_WIDTH)

    # เลนข้างเป็นรูปตัว L เลียบขอบ ไม่ใช่เส้นทแยง
    inset = lane_inset(meta)
    print(f"เส้นกลางเลนข้างห่างจากขอบ {inset:.3f} (วัดจากป้อมริมขอบ)")
    near_left = np.abs(xs - inset) <= LANE_HALF_WIDTH
    near_top = np.abs(ys - inset) <= LANE_HALF_WIDTH
    near_bot = np.abs(ys - (1 - inset)) <= LANE_HALF_WIDTH
    near_right = np.abs(xs - (1 - inset)) <= LANE_HALF_WIDTH
    put("DS_LANE", near_left | near_top)
    put("DRAGON_LANE", near_bot | near_right)

    # ป่าสี่ส่วน แบ่งด้วยสองแนวทแยง
    put("JUNGLE_BLUE_SLAYER", blue_half & slayer_half)
    put("JUNGLE_BLUE_DRAGON", blue_half & ~slayer_half)
    put("JUNGLE_RED_SLAYER", ~blue_half & slayer_half)
    put("JUNGLE_RED_DRAGON", ~blue_half & ~slayer_half)
    return lab


def contours_of(lab: np.ndarray, i: int) -> list[list[list[float]]]:
    m = (lab == i).astype(np.uint8) * 255
    if not m.any():
        return []
    # ลบเศษเล็ก ๆ ที่เกิดจากขอบชนกัน
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    polys = []
    for c in cnts:
        if cv2.contourArea(c) < N * N * 0.0008:  # เล็กกว่านี้ไม่มีความหมาย
            continue
        eps = 0.004 * cv2.arcLength(c, True)
        ap = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
        if len(ap) < 3:
            continue
        polys.append([[round(float(p[0]) / N, 4), round(float(p[1]) / N, 4)] for p in ap])
    return polys


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if not META.exists():
        print(f"ไม่พบ {META} — รัน scripts/build_minimap.py ก่อน")
        return 1
    meta = json.loads(META.read_text(encoding="utf-8"))

    lab = build_labels(meta)
    cov = float((lab > 0).mean())
    print(f"ครอบคลุมแมพ {cov:.1%}")

    zones = []
    for i, (zid, kind, region) in enumerate(ZONES, start=1):
        polys = contours_of(lab, i)
        if not polys:
            print(f"  ⚠️ {zid} ไม่มีพื้นที่เหลือ")
            continue
        area = float((lab == i).mean())
        print(f"  {zid:22s} {kind:9s} {len(polys)} ชิ้น  {area:6.2%}")
        zones.append({"id": zid, "kind": kind, "region": region, "polygons": polys})

    doc = {
        "version": 3,
        "verified": True,
        "verified_from": (
            "minimap จากในเกม (data/assets/map/source/IMG_0419.PNG) "
            "ผ่าน scripts/build_minimap.py"
        ),
        "generated_by": "scripts/gen_zone_map.py",
        "zones": zones,
    }
    header = (
        "# Zone map ของ Antaris Battlefield (RoV 5v5)\n"
        "#\n"
        "# สร้างอัตโนมัติด้วย scripts/gen_zone_map.py — อย่าแก้ทีละจุดด้วยมือ\n"
        "# ถ้ารูปร่างไม่ตรง ให้แก้ค่าคงที่ในสคริปต์แล้วรันใหม่\n"
        "#\n"
        "# ยึดจากค่าที่วัดได้บน minimap จริงในเกม ไม่ใช่รูปทรงที่เดาขึ้น\n"
        "#   ฐานน้ำเงินมุมซ้ายล่าง ฐานแดงมุมขวาบน\n"
        "#   เลนกลางตามแนวทแยง x + y = 1 เชื่อมสองฐาน\n"
        "#   แม่น้ำตามแนวทแยง y = x แบ่งเป็นสองแอ่ง รูปร่างมาจากหน้ากากภาพจริง\n"
        "#   เลนข้างเป็นรูปตัว L เลียบขอบแมพ\n"
        "#\n"
        "# ⚠️ verified: true หมายถึงตรงกับ minimap ในไคลเอนต์เกม\n"
        "#    ยังไม่ได้เทียบกับ minimap ฝั่ง broadcast ซึ่งอาจเรนเดอร์ต่างกัน\n"
        "#\n"
        "# พิกัด normalized 0..1  (0,0) = ซ้ายบน  (1,1) = ขวาล่าง\n\n"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        header + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    print(f"เขียน {OUT} · {len(zones)} zone")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
