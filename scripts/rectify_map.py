"""แปลงภาพแผนที่จากหน้า "ข้อมูลสมรภูมิ" ในเกม ให้เป็นมุมมองบนลงล่าง

ที่มา: data/exports/mapdetal.mp4 — คลิปหน้าแนะนำแผนที่ในเกม RoV
ที่ผู้ใช้อัดมาให้ ไม่ได้ดึงจากเว็บภายนอก

ขั้นตอน
  1. สุ่มเฟรมจากคลิป เก็บเฉพาะเฟรมที่นิ่ง (ไม่ได้อยู่กลาง transition)
  2. หาเฟรมที่เป็น "ภาพแมพเต็ม" — หลายหน้าใช้ภาพเดียวกัน ต่างแค่ข้อความ
  3. median รวมกัน ลบข้อความและ marker ที่เปลี่ยนไปมาออก
  4. แยกสนามออกจากพื้นหลังเมนูด้วย hue แล้วลดรูปเหลือสี่เหลี่ยม
  5. warp เป็นจัตุรัส

⚠️ ข้อจำกัดที่ต้องรู้ (ดู docs/16-map-guide.md §9)

ภาพต้นทางเป็นงานศิลป์ 3 มิติ มีความสูงต่ำของภูมิประเทศและแสงเงาทิศทางเดียว
homography เป็นการประมาณระนาบพื้นเท่านั้น **พิกัดที่ได้จึงคลาดเคลื่อนราว
±0.03-0.05 ในหน่วย normalized** ใช้ยืนยัน "โครงสร้าง" ได้ (ฐานอยู่มุมไหน
แม่น้ำวางตัวยังไง หลุมอยู่คนละครึ่ง) แต่ **ใช้เป็นพิกัดสอบเทียบไม่ได้**
การสอบเทียบจริงต้องรอ minimap จากคลิปการแข่งขัน

ตัว marker ยังลอยอยู่เหนือพื้นด้วย พอ warp แล้วมันเลื่อนจากจุดยืนจริง
และเลื่อนไม่เท่ากันตามระยะ จึงห้ามอ่านพิกัด objective จากกึ่งกลาง marker ตรง ๆ

รัน:  python scripts/rectify_map.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import av
import cv2
import numpy as np

SRC = Path("data/exports/mapdetal.mp4")
OUT = Path("data/assets/map")
WORK = Path("data/exports/mapwork")
SIZE = 900

# hue ของพื้นหลังเมนู วัดจากภาพจริง — พื้นหลัง 109-135 สนาม 60-105
BG_HUE = (109, 135)
BG_SAT_MIN = 60
SIDEBAR_X = 215  # เมนูซ้ายมือ ไม่ใช่สนาม


def stable_frames(path: Path, step: float = 0.25) -> list[np.ndarray]:
    """สุ่มเฟรมทุก step วินาที เก็บเฉพาะเฟรมที่เหมือนเฟรมถัดไป"""
    cont = av.open(str(path))
    st = cont.streams.video[0]
    st.thread_type = "AUTO"
    frames, nxt = [], 0.0
    for fr in cont.decode(st):
        t = float(fr.pts * st.time_base)
        if t + 1e-6 < nxt:
            continue
        nxt = t + step
        frames.append(fr.to_ndarray(format="bgr24"))
    cont.close()

    def sig(img: np.ndarray) -> np.ndarray:
        g = cv2.cvtColor(cv2.resize(img, (64, 32)), cv2.COLOR_BGR2GRAY)
        return g.astype(np.float32) / 255.0

    sigs = [sig(f) for f in frames]
    return [
        frames[i]
        for i in range(len(frames) - 1)
        if np.abs(sigs[i] - sigs[i + 1]).mean() < 0.006
    ]


def full_map_frames(frames: list[np.ndarray]) -> list[np.ndarray]:
    """หาเฟรมที่เป็นภาพแมพเต็ม

    หน้าที่แสดงแมพเต็มใช้ภาพพื้นหลังเดียวกันเป๊ะ ต่างแค่ข้อความฝั่งซ้าย
    กับชุด marker ที่โชว์อยู่ จึงจับกลุ่มแบบ "หลวม" ตั้งใจ — ให้ได้ทั้งเฟรม
    ที่มี marker และไม่มี marker เข้ามาปนกัน median จะได้กิน marker ทิ้ง
    ถ้าจับกลุ่มแน่นเกินไปจะได้แต่เฟรมที่มี marker แล้วลบไม่ออก
    """
    # เทียบครึ่งขวาบน — เลี่ยงทั้งเมนูซ้ายและแถบเวลาที่ขอบล่าง
    # หน้า "ช่วงเวลา" ใช้ภาพแมพเดียวกันแต่มีแถบเวลาทับอยู่ด้านล่าง
    # ถ้าไม่กันออก ตัวเลข 4:00 8:00 15:00 จะติดมาในภาพ median
    h, w = frames[0].shape[:2]
    def key(f):
        return f[: int(h * 0.80), w // 2 :].astype(np.float32)
    half = [key(f) for f in frames]
    n = len(frames)
    best: list[int] = []
    for i in range(n):
        grp = [j for j in range(n) if np.abs(half[i] - half[j]).mean() < 6.0]
        if len(grp) > len(best):
            best = grp

    # ตัดเฟรมที่ขอบล่างต่างจากพวก ออกอีกชั้น
    bot = np.median(
        np.stack([frames[j][int(h * 0.88) :].astype(np.float32) for j in best]), 0
    )
    best = [
        j
        for j in best
        if np.abs(frames[j][int(h * 0.88) :].astype(np.float32) - bot).mean() < 4.0
    ]
    return [frames[j] for j in best]


def find_quad(im: np.ndarray) -> np.ndarray:
    """หาสี่เหลี่ยมของสนาม คืนมุมเรียง บนซ้าย บนขวา ล่างขวา ล่างซ้าย"""
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    hue, sat = hsv[..., 0], hsv[..., 1]
    bg = (hue >= BG_HUE[0]) & (hue <= BG_HUE[1]) & (sat > BG_SAT_MIN)
    mask = (~bg).astype(np.uint8) * 255
    mask[:, :SIDEBAR_X] = 0

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=4)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        raise RuntimeError("แยกสนามออกจากพื้นหลังไม่ได้")
    hull = cv2.convexHull(max(cnts, key=cv2.contourArea))
    peri = cv2.arcLength(hull, True)

    quad = None
    for eps in np.arange(0.004, 0.10, 0.002):
        ap = cv2.approxPolyDP(hull, eps * peri, True)
        if len(ap) == 4:
            quad = ap.reshape(4, 2).astype(np.float32)
            break
    if quad is None:
        quad = cv2.boxPoints(cv2.minAreaRect(hull)).astype(np.float32)

    s, d = quad.sum(1), np.diff(quad, axis=1).ravel()
    return np.array(
        [quad[np.argmin(s)], quad[np.argmin(d)], quad[np.argmax(s)], quad[np.argmax(d)]],
        dtype=np.float32,
    )


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if not SRC.exists():
        print(f"ไม่พบ {SRC} — ต้องมีคลิปหน้าแนะนำแผนที่ก่อน")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)

    frames = stable_frames(SRC)
    print(f"เฟรมที่นิ่ง {len(frames)}")

    maps = full_map_frames(frames)
    print(f"เฟรมที่เป็นภาพแมพเต็ม {len(maps)}")
    if len(maps) < 3:
        print("เฟรมแมพน้อยเกินไป median จะลบ marker ไม่ออก")
        return 1

    stack = np.stack([m.astype(np.float32) for m in maps])
    med = np.median(stack, 0).astype(np.uint8)
    cv2.imwrite(str(WORK / "base_median.png"), med)

    # ใช้ median หามุม เพราะทนต่อเฟรมแปลกปลอม
    quad = find_quad(med)

    # แต่ภาพที่เอาไปใช้จริงใช้ "เฟรมเดียว" ที่ใกล้ median ที่สุด ไม่ใช่ median
    #
    # median ทำให้ marker จางครึ่ง ๆ กลาง ๆ แล้วภาพเบลอ ลองลบ marker ด้วย
    # percentile ต่ำกับ inpaint แล้วทั้งคู่ให้ผลแย่กว่า — percentile ทิ้งกล่องเงาดำ
    # inpaint ทิ้งรอยเบลอ ตัว marker เองก็มีประโยชน์ เพราะเป็นคำอธิบาย
    # ตำแหน่งแคมป์และ objective ที่เกมทำมาให้ จึงเก็บไว้ทั้งชุด
    d = np.abs(stack - med.astype(np.float32)).mean(axis=(1, 2, 3))
    pick = int(np.argmin(d))
    base = maps[pick]
    print(f"ใช้เฟรมที่ {pick} (ต่างจาก median {d[pick]:.2f}) เป็นภาพหลัก")
    names = ["บนซ้าย", "บนขวา", "ล่างขวา", "ล่างซ้าย"]
    print("มุมของสนามในภาพต้นฉบับ:")
    for n, p in zip(names, quad, strict=True):
        print(f"  {n:9s} ({p[0]:6.1f}, {p[1]:6.1f})")

    dst = np.array(
        [[0, 0], [SIZE, 0], [SIZE, SIZE], [0, SIZE]], dtype=np.float32
    )
    hm = cv2.getPerspectiveTransform(quad, dst)
    top = cv2.warpPerspective(base, hm, (SIZE, SIZE), flags=cv2.INTER_CUBIC)
    cv2.imwrite(str(OUT / "topdown.png"), top)

    # ภาพตรวจความสมมาตร — แมพ MOBA สมมาตรรอบจุดกึ่งกลาง
    # เขียวคือภาพจริง ม่วงคือภาพที่หมุน 180 องศา ยิ่งทับกันยิ่งดี
    g = cv2.cvtColor(top, cv2.COLOR_BGR2GRAY)
    rot = np.rot90(g, 2)
    cv2.imwrite(str(WORK / "symcheck.png"), cv2.merge([g, rot, g]))
    asym = float(np.abs(g.astype(np.float32) - rot.astype(np.float32)).mean() / 255)
    print(f"\nความไม่สมมาตรที่เหลือ {asym:.3f} (0 = สมมาตรสมบูรณ์)")

    meta = {
        "source": "data/exports/mapdetal.mp4 — หน้าข้อมูลสมรภูมิในเกม RoV",
        "frames_used": len(maps),
        "note_markers": "marker ในภาพคือแคมป์และ objective ที่เกมทำมาให้ ไม่ได้ลบออก",
        "quad_in_source": quad.tolist(),
        "size": SIZE,
        "asymmetry": round(asym, 4),
        "warning": (
            "เป็นการ warp งานศิลป์ 3 มิติเป็นระนาบ คลาดเคลื่อน ±0.03-0.05 "
            "ใช้ยืนยันโครงสร้างได้ ใช้สอบเทียบพิกัดไม่ได้"
        ),
    }
    (OUT / "map_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"เขียน {OUT / 'topdown.png'} และ map_meta.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
