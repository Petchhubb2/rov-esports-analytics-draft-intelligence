"""สกัด minimap จริงจากภาพในเกม แล้ววัดตำแหน่งทุกองค์ประกอบ

ที่มา: data/assets/map/source/IMG_0419.PNG — ภาพ minimap ที่ผู้ใช้แคปมาจากเกม
เป็นมุมมองบนลงล่างอยู่แล้ว ไม่ต้อง warp เหมือนภาพ isometric ใน mapdetal.mp4
จึงเป็นแหล่งอ้างอิงที่ตรงกับสิ่งที่ vision pipeline จะเห็นจริง

**วิธีหาศูนย์กลางสนาม**

ไม่ได้หาจากขอบภาพ เพราะขอบแมพกับพื้นหลังเกมสีใกล้กันจนแยกไม่ขาด
ใช้ความสมมาตรแทน — แมพ MOBA สมมาตรเมื่อหมุน 180 องศา ป้อมน้ำเงินทุกตัว
จึงมีป้อมแดงคู่กัน จุดกึ่งกลางของคู่คือศูนย์กลางสนาม
วิธีนี้ไม่ต้องรู้ขอบเลยและทนต่อการครอบภาพที่ไม่เท่ากัน

**ค่าสีที่วัดจากภาพจริง** (ดู docs/16-map-guide.md §10)

    พื้นเทา    H 105-118  S  50-115  V  60-140
    แม่น้ำ     H  88-104  S 110+     V  95+
    พุ่ม/ผนัง  H 100-125  S 130-160  V  20- 55
    นอกสนาม   H 110-118  S 150-215  V  60-140

พุ่มกับพื้นหลังนอกสนามอิ่มสีพอ ๆ กัน แยกได้ด้วยความสว่างเท่านั้น

รัน:  python scripts/build_minimap.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

SRC = Path("data/assets/map/source/IMG_0419.PNG")
OUT = Path("data/assets/map")
WORK = Path("data/exports/mapwork")
SIZE = 900  # ขนาดภาพที่ส่งออก


def _blobs(mask: np.ndarray, amin: int, amax: int) -> list[tuple[float, float, int]]:
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    m = cv2.morphologyEx(mask.astype(np.uint8) * 255, cv2.MORPH_OPEN, k)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k, iterations=2)
    n, _lbl, st, cent = cv2.connectedComponentsWithStats(m, 8)
    return [
        (float(cent[i][0]), float(cent[i][1]), int(st[i, cv2.CC_STAT_AREA]))
        for i in range(1, n)
        if amin <= st[i, cv2.CC_STAT_AREA] <= amax
    ]


def find_centre(
    blue: list, red: list, w: int, h: int
) -> tuple[float, float]:
    """ศูนย์กลางสนามจากความสมมาตรของสิ่งปลูกสร้างสองฝั่ง

    ถ้าศูนย์กลางคือ c แล้วป้อมที่จับคู่กันจะมี blue + red = 2c เสมอ
    จับคู่แต่ละป้อมน้ำเงินกับป้อมแดงที่ให้จุดกึ่งกลางใกล้กลางภาพที่สุด
    แล้วเอา median ของทุกคู่ — median ทนต่อคู่ที่จับผิดได้
    """
    mids = []
    for bx, by, _ in blue:
        best, bd = None, float("inf")
        for rx, ry, _ in red:
            d = abs((bx + rx) / 2 - w / 2) + abs((by + ry) / 2 - h / 2)
            if d < bd:
                bd, best = d, ((bx + rx) / 2, (by + ry) / 2)
        if best:
            mids.append((best[0], best[1], bd))
    if not mids:
        return w / 2, h / 2
    mids.sort(key=lambda t: t[2])
    keep = mids[: max(4, len(mids) * 2 // 3)]
    return (
        float(np.median([m[0] for m in keep])),
        float(np.median([m[1] for m in keep])),
    )


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if not SRC.exists():
        print(f"ไม่พบ {SRC}")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)

    im = cv2.imread(str(SRC))
    H, W = im.shape[:2]
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    h, s, v = (hsv[..., i].astype(int) for i in range(3))

    # ── สิ่งปลูกสร้าง ป้อมมีสองเฉด สดกับซีด จับให้ครบทั้งคู่ ──
    blue = _blobs((h >= 96) & (h <= 115) & (s >= 55) & (v >= 170), 250, 9000)
    red = _blobs(((h <= 10) | (h >= 172)) & (s >= 55) & (v >= 170), 250, 9000)
    print(f"สิ่งปลูกสร้าง  น้ำเงิน {len(blue)}  แดง {len(red)}")

    cx, cy = find_centre(blue, red, W, H)
    print(f"ศูนย์กลางสนาม ({cx:.1f}, {cy:.1f}) — กลางภาพคือ ({W/2:.1f}, {H/2:.1f})")

    # ครอบเป็นจัตุรัสที่ใหญ่ที่สุดโดยให้ศูนย์กลางสนามอยู่กลางพอดี
    half = int(min(cx, W - cx, cy, H - cy))
    x0, y0 = int(round(cx - half)), int(round(cy - half))
    crop = im[y0 : y0 + 2 * half, x0 : x0 + 2 * half]
    scale = SIZE / crop.shape[0]
    board = cv2.resize(crop, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(OUT / "minimap.png"), board)
    print(f"ครอบ {2*half}x{2*half} จาก ({x0},{y0}) แล้วย่อเป็น {SIZE}x{SIZE}")

    def to_board(px: float, py: float) -> tuple[float, float]:
        """พิกัดในภาพต้นฉบับ -> พิกัดพิกเซลบนกระดานที่ครอบแล้ว

        คืนเป็นพิกเซล ไม่ใช่ normalized เพราะ norm() ข้างล่างหารด้วย SIZE
        ให้อยู่แล้ว ถ้าคืน normalized มาจะโดนหารซ้ำจนกลายเป็นศูนย์
        """
        return ((px - x0) * scale, (py - y0) * scale)

    # ── องค์ประกอบอื่น ──
    hs = cv2.cvtColor(board, cv2.COLOR_BGR2HSV)
    bh, bs, bv = (hs[..., i].astype(int) for i in range(3))

    river = (bh >= 88) & (bh <= 104) & (bs >= 110) & (bv >= 95)
    rk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    rmask = cv2.morphologyEx(river.astype(np.uint8) * 255, cv2.MORPH_CLOSE, rk, iterations=3)
    rmask = cv2.morphologyEx(rmask, cv2.MORPH_OPEN, rk, iterations=2)

    bush = (bv <= 58) & (bh >= 98) & (bh <= 128)
    bk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    bmask = cv2.morphologyEx(bush.astype(np.uint8) * 255, cv2.MORPH_OPEN, bk, iterations=2)
    bmask = cv2.morphologyEx(bmask, cv2.MORPH_CLOSE, bk, iterations=2)

    cv2.imwrite(str(WORK / "board_river.png"), rmask)
    cv2.imwrite(str(WORK / "board_bush.png"), bmask)
    print(f"แม่น้ำ {100*rmask.mean()/255:.1f}%  พุ่ม/ผนัง {100*bmask.mean()/255:.1f}%")

    # หลุม objective — Dark Slayer ม่วง, Abyssal Dragon ทอง (ใหญ่กว่าแคมป์ป่ามาก)
    slayer = _blobs((bh >= 125) & (bh <= 158) & (bs >= 60) & (bv >= 100), 700, 20000)
    # ตัวมังกรสีทองอมน้ำตาล วัดได้ H 17-20 S 122-124 V 72-142
    # เกณฑ์ V ต้องต่ำกว่าแคมป์ป่ามาก เพราะลำตัวมันมีส่วนที่มืด
    dragon = _blobs((bh >= 12) & (bh <= 32) & (bs >= 100) & (bv >= 60), 900, 30000)
    # แคมป์ป่ามีสองขนาดชัดเจน จุดส้มเล็ก ~85-100 px กับแคมป์ใหญ่ ~430-460 px
    # ตัวมังกรเองก็เข้าเกณฑ์สีทองด้วย (672 px) ต้องคัดออกด้วยตำแหน่ง
    camps_all = _blobs((bh >= 14) & (bh <= 30) & (bs >= 120) & (bv >= 140), 40, 900)
    dpos = dragon[0] if dragon else None
    def _is_dragon(c):
        return dpos is not None and abs(c[0] - dpos[0]) < 30 and abs(c[1] - dpos[1]) < 30
    big_camps = [c for c in camps_all if c[2] >= 250 and not _is_dragon(c)]
    camps = [c for c in camps_all if c[2] < 250]
    heal = _blobs((bh >= 40) & (bh <= 78) & (bs >= 110) & (bv >= 130), 110, 2400)
    print(f"หลุม Dark Slayer {len(slayer)}  Abyssal Dragon {len(dragon)}  "
          f"แคมป์ใหญ่ {len(big_camps)}  แคมป์เล็ก {len(camps)}  จุดฮีล {len(heal)}")

    def norm(items):
        return [
            {"x": round(a / SIZE, 4), "y": round(b / SIZE, 4), "area": c}
            for a, b, c in items
        ]

    meta = {
        "source": "data/assets/map/source/IMG_0419.PNG — minimap จากในเกมที่ผู้ใช้แคปมา",
        "size": SIZE,
        "crop_in_source": {"x": x0, "y": y0, "side": 2 * half},
        "centre_method": "ความสมมาตร 180 องศาของสิ่งปลูกสร้างสองฝั่ง",
        "centre_in_source": [round(cx, 1), round(cy, 1)],
        "structures_blue": norm([(*to_board(a, b), c) for a, b, c in blue]),
        "structures_red": norm([(*to_board(a, b), c) for a, b, c in red]),
        "slayer_pit": norm(slayer),
        "dragon_pit": norm(dragon),
        "big_camps": norm(big_camps),
        "camps": norm(camps),
        "heal_spots": norm(heal),
        "river_fraction": round(float(rmask.mean() / 255), 4),
        "bush_fraction": round(float(bmask.mean() / 255), 4),
        "note": (
            "พิกัดทั้งหมดเป็น normalized 0..1 บนภาพ minimap.png "
            "ศูนย์กลางสนามอยู่ที่ (0.5, 0.5) พอดีเพราะครอบมาให้ตรงแล้ว"
        ),
    }
    (OUT / "minimap_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ── ภาพตรวจ ──
    vis = board.copy()
    for grp, col in (("structures_blue", (255, 200, 0)), ("structures_red", (0, 0, 255)),
                     ("slayer_pit", (255, 0, 255)), ("dragon_pit", (0, 200, 255)),
                     ("big_camps", (0, 220, 255)), ("camps", (0, 165, 255)),
                     ("heal_spots", (0, 255, 0))):
        for d in meta[grp]:
            cv2.circle(vis, (int(d["x"] * SIZE), int(d["y"] * SIZE)), 10, col, 2)
    cv2.drawMarker(vis, (SIZE // 2, SIZE // 2), (0, 255, 255), cv2.MARKER_CROSS, 40, 3)
    cv2.imwrite(str(WORK / "board_check.png"), vis)

    g = cv2.cvtColor(cv2.resize(board, (360, 360)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    b = 20
    asym = float(np.abs(g[b:-b, b:-b] - np.rot90(g, 2)[b:-b, b:-b]).mean() / 255)
    print(f"ความไม่สมมาตรเมื่อหมุน 180 องศา {asym:.4f} (0 = สมมาตรสมบูรณ์)")
    print(f"เขียน {OUT/'minimap.png'} และ minimap_meta.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
