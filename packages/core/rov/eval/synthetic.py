"""เครื่องกำเนิด minimap สังเคราะห์ พร้อม ground truth

เหตุผลที่ต้องมี: Milestone 1 คือสิ่งที่ตัดสินทั้งโครงการ แต่ยังไม่มีคลิปจริง
เครื่องนี้ทำให้พัฒนาและ "วัด" detector ได้ตั้งแต่วันนี้ โดยจำลองเงื่อนไขที่ยากจริง

  - พื้นหลังภูมิประเทศคงที่ (ป่า แม่น้ำ เลน) ที่มีสีใกล้เคียงกับ icon
  - ป้อมที่จางสีลงเรื่อย ๆ  → ทดสอบว่า rolling median จำเป็นจริง
  - minion เคลื่อนที่บนเลน  → รอด background subtraction เหมือนของจริง
  - icon ทับกันตอน teamfight → กรณียากอันดับหนึ่ง (แผนเดิม §77)
  - ping ที่ขยายวงแล้วหาย    → false positive ที่ต้องกรอง

สิ่งที่มันไม่ได้จำลอง: รายละเอียด portrait ของฮีโร่จริง การบีบอัดวิดีโอ
และความเพี้ยนของสีจาก broadcast ดังนั้น threshold ที่จูนบนนี้
"ห้าม" เอาไปใช้กับคลิปจริงโดยไม่วัดซ้ำ ตัวนี้ตรวจว่า "อัลกอริทึมถูก"
ไม่ใช่ตรวจว่า "ค่าพารามิเตอร์ถูก"
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np

from rov.domain.enums import Team
from rov.domain.geometry import Point

MINIMAP_SIZE = 186  # ใกล้เคียงขนาดจริงที่ 720p
ICON_DIAMETER = 18

# สีในระบบ BGR
_C_GRASS = (58, 92, 46)
_C_JUNGLE = (40, 66, 34)
_C_RIVER = (128, 92, 44)  # แม่น้ำสีน้ำเงิน — ทำให้ icon น้ำเงินตรวจยาก โดยเจตนา
_C_LANE = (96, 122, 88)
_C_BLUE_RING = (232, 148, 40)
_C_RED_RING = (48, 52, 226)
_C_MINION_BLUE = (170, 130, 70)
_C_MINION_RED = (80, 80, 168)


@dataclass(slots=True)
class TruthIcon:
    slot: int
    point: Point
    team: Team
    occluded: bool = False
    visible: bool = True


@dataclass(slots=True)
class SyntheticFrame:
    frame_idx: int
    video_time: float
    image: np.ndarray
    truth: list[TruthIcon]


def make_terrain(size: int = MINIMAP_SIZE, seed: int = 0) -> np.ndarray:
    """พื้นหลังภูมิประเทศคงที่ — เลียนโครงสร้าง 3 เลน + แม่น้ำทแยง + ป่า"""
    rng = np.random.default_rng(seed)
    img = np.full((size, size, 3), _C_GRASS, dtype=np.uint8)

    def npt(x: float, y: float) -> tuple[int, int]:
        return (int(x * (size - 1)), int(y * (size - 1)))

    # ป่าสี่ส่วน
    for cx, cy in [(0.28, 0.28), (0.28, 0.72), (0.72, 0.28), (0.72, 0.72)]:
        cv2.circle(img, npt(cx, cy), int(size * 0.15), _C_JUNGLE, -1)

    # แม่น้ำแนวทแยงจากซ้ายบนไปขวาล่าง
    cv2.line(img, npt(0.10, 0.10), npt(0.90, 0.90), _C_RIVER, int(size * 0.075))

    # สามเลน
    cv2.line(img, npt(0.06, 0.06), npt(0.06, 0.94), _C_LANE, 5)
    cv2.line(img, npt(0.06, 0.06), npt(0.94, 0.06), _C_LANE, 5)
    cv2.line(img, npt(0.10, 0.90), npt(0.90, 0.10), _C_LANE, 5)
    cv2.line(img, npt(0.94, 0.06), npt(0.94, 0.94), _C_LANE, 5)
    cv2.line(img, npt(0.06, 0.94), npt(0.94, 0.94), _C_LANE, 5)

    # noise ของพื้นผิว
    noise = rng.normal(0, 5, (size, size, 3))
    return np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)


# พิกัดป้อม 3 ชั้นต่อเลนต่อฝั่ง
TOWERS: list[tuple[float, float, Team]] = [
    (0.06, 0.30, Team.BLUE), (0.06, 0.52, Team.BLUE), (0.06, 0.74, Team.BLUE),
    (0.30, 0.94, Team.BLUE), (0.52, 0.94, Team.BLUE), (0.26, 0.74, Team.BLUE),
    (0.94, 0.70, Team.RED), (0.94, 0.48, Team.RED), (0.94, 0.26, Team.RED),
    (0.70, 0.06, Team.RED), (0.48, 0.06, Team.RED), (0.74, 0.26, Team.RED),
]


def draw_towers(img: np.ndarray, health: dict[int, float]) -> None:
    """วาดป้อมที่จางสีลงตามเลือด — ป้อมที่เลือดหมดจะหายไป

    ยืนยันจากเกมจริง: icon ป้อมจางสีลงตามความเสียหายและหายเมื่อถูกทำลาย
    (docs/08-game-reference.md §4) ตัวนี้คือเหตุผลที่ต้องใช้ rolling median
    """
    size = img.shape[0]
    for i, (x, y, team) in enumerate(TOWERS):
        hp = health.get(i, 1.0)
        if hp <= 0.0:
            continue
        base = np.array(_C_BLUE_RING if team is Team.BLUE else _C_RED_RING, dtype=np.float32)
        grass = np.array(_C_GRASS, dtype=np.float32)
        col = tuple(int(v) for v in (grass + (base - grass) * hp))
        cv2.rectangle(
            img,
            (int(x * size) - 3, int(y * size) - 3),
            (int(x * size) + 3, int(y * size) + 3),
            col,
            -1,
        )


def draw_icon(
    img: np.ndarray,
    p: Point,
    team: Team,
    slot: int,
    diameter: int = ICON_DIAMETER,
) -> None:
    """hero icon = วงแหวนสีทีม + เนื้อในที่ต่างกันตาม slot"""
    size = img.shape[0]
    cx, cy = int(p.x * size), int(p.y * size)
    r = diameter // 2
    ring = _C_BLUE_RING if team is Team.BLUE else _C_RED_RING

    # เนื้อใน — ให้แต่ละ slot มีโทนต่างกันเล็กน้อย เลียนแบบ portrait
    # ความต่างน้อยโดยเจตนา เพราะของจริงที่ 18px ก็แยกยากพอกัน
    tone = 70 + (slot % 5) * 26
    inner = (tone, tone - 12, tone + 14)
    cv2.circle(img, (cx, cy), r, ring, -1)
    cv2.circle(img, (cx, cy), max(1, r - 2), inner, -1)


def draw_minions(img: np.ndarray, t: float, rng: np.random.Generator) -> None:
    """minion เคลื่อนที่บนเลน — รอด background subtraction เหมือนของจริง"""
    size = img.shape[0]
    phase = (t * 0.02) % 1.0
    for lane in ((0.06, 0.06, 0.06, 0.94), (0.10, 0.90, 0.90, 0.10), (0.06, 0.94, 0.94, 0.94)):
        x0, y0, x1, y1 = lane
        for k in range(3):
            f = (phase + k * 0.12) % 1.0
            for team, ff in ((Team.BLUE, f), (Team.RED, 1.0 - f)):
                x = x0 + (x1 - x0) * ff
                y = y0 + (y1 - y0) * ff
                col = _C_MINION_BLUE if team is Team.BLUE else _C_MINION_RED
                jitter = rng.integers(-1, 2, 2)
                cv2.circle(
                    img,
                    (int(x * size) + int(jitter[0]), int(y * size) + int(jitter[1])),
                    2,
                    col,
                    -1,
                )


def draw_ping(img: np.ndarray, p: Point, age: float) -> None:
    """ping = วงแหวนที่ขยายแล้วจาง — false positive ที่ต้องกรองด้วยอายุ"""
    size = img.shape[0]
    r = int(4 + age * 22)
    alpha = max(0.0, 1.0 - age)
    if alpha <= 0:
        return
    overlay = img.copy()
    cv2.circle(overlay, (int(p.x * size), int(p.y * size)), r, (60, 220, 250), 2)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)


# ---------------------------------------------------------------------------


@dataclass
class SyntheticMatch:
    """จำลองแมตช์ทั้งเกม: 10 ฮีโร่เดิน ป้อมค่อย ๆ พัง มี teamfight ที่ icon ทับกัน"""

    size: int = MINIMAP_SIZE
    seed: int = 0
    duration: float = 600.0
    fps: float = 2.0
    fight_windows: list[tuple[float, float]] = field(
        default_factory=lambda: [(120.0, 150.0), (330.0, 370.0), (520.0, 560.0)]
    )

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self._terrain = make_terrain(self.size, self.seed)
        # เส้นทางเดินของแต่ละ slot เป็นวงรีที่ต่างกัน จำลองการวนฟาร์มและโรม
        self._orbit = []
        for s in range(10):
            r = self._rng.uniform(0.18, 0.34)
            cx = self._rng.uniform(0.30, 0.70)
            cy = self._rng.uniform(0.30, 0.70)
            speed = self._rng.uniform(0.008, 0.020)
            phase = self._rng.uniform(0, 2 * math.pi)
            self._orbit.append((cx, cy, r, speed, phase))

    def _base_position(self, slot: int, t: float) -> Point:
        cx, cy, r, speed, phase = self._orbit[slot]
        a = phase + t * speed
        return Point(
            x=float(np.clip(cx + r * math.cos(a), 0.04, 0.96)),
            y=float(np.clip(cy + r * math.sin(a) * 0.8, 0.04, 0.96)),
        )

    def _in_fight(self, t: float) -> bool:
        return any(a <= t <= b for a, b in self.fight_windows)

    def positions_at(self, t: float) -> list[TruthIcon]:
        pts: list[TruthIcon] = []
        if self._in_fight(t):
            # teamfight — ทุกคนกระจุกรอบจุดเดียว icon ทับกันหนัก
            #
            # รัศมีต้องสมจริง: icon มีขนาด 18/186 = 0.097 ในหน่วย normalized
            # ถ้าตั้งรัศมีกระจุกไว้ 0.03 จะได้ icon 10 ตัวซ้อนกันเกือบสนิท
            # ซึ่งแยกไม่ออกแม้ด้วยตาคน และไม่ตรงกับ teamfight จริง
            # ตั้งไว้ราว 1-1.5 เท่าของขนาด icon จึงจะได้การทับที่สมจริง
            fx = 0.5 + 0.12 * math.sin(t * 0.05)
            fy = 0.5 + 0.12 * math.cos(t * 0.05)
            for s in range(10):
                a = s * (2 * math.pi / 10) + t * 0.3
                rad = 0.105 + 0.030 * ((s % 3) - 1)
                pts.append(
                    TruthIcon(
                        slot=s,
                        point=Point(
                            x=float(np.clip(fx + rad * math.cos(a), 0.04, 0.96)),
                            y=float(np.clip(fy + rad * math.sin(a), 0.04, 0.96)),
                        ),
                        team=Team.BLUE if s < 5 else Team.RED,
                    )
                )
        else:
            for s in range(10):
                pts.append(
                    TruthIcon(
                        slot=s,
                        point=self._base_position(s, t),
                        team=Team.BLUE if s < 5 else Team.RED,
                    )
                )
        _mark_occlusions(pts, self.size)
        return pts

    def tower_health(self, t: float) -> dict[int, float]:
        """ป้อมค่อย ๆ พังตามเวลา — ตัวนี้ทำให้ median ทั้งเกมใช้ไม่ได้"""
        out: dict[int, float] = {}
        for i in range(len(TOWERS)):
            start = 180.0 + i * 32.0
            if t < start:
                out[i] = 1.0
            elif t < start + 90.0:
                out[i] = 1.0 - (t - start) / 90.0
            else:
                out[i] = 0.0
        return out

    def render(self, t: float, frame_idx: int) -> SyntheticFrame:
        img = self._terrain.copy()
        draw_towers(img, self.tower_health(t))
        draw_minions(img, t, self._rng)

        truth = self.positions_at(t)
        for icon in truth:
            draw_icon(img, icon.point, icon.team, icon.slot)

        # ping ทุก ๆ 40 วินาที
        ping_age = (t % 40.0) / 2.0
        if ping_age < 1.0:
            pr = np.random.default_rng(int(t // 40)).random(2)
            draw_ping(img, Point(0.15 + 0.7 * pr[0], 0.15 + 0.7 * pr[1]), ping_age)

        # สัญญาณรบกวนจากการบีบอัดวิดีโอ
        noise = self._rng.normal(0, 2.5, img.shape)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        return SyntheticFrame(frame_idx=frame_idx, video_time=t, image=img, truth=truth)

    def frames(self) -> list[SyntheticFrame]:
        step = 1.0 / self.fps
        return [
            self.render(t, i)
            for i, t in enumerate(np.arange(0.0, self.duration, step))
        ]


def _mark_occlusions(icons: list[TruthIcon], size: int) -> None:
    """ทำเครื่องหมายว่า icon ใดถูกทับ — ต้องรายงาน metric แยกสำหรับกรณีนี้

    ถ้าไม่แยก ตัวเลข recall รวมจะดูดีเกินจริง เพราะกรณียากมีสัดส่วนน้อย
    """
    thr = (ICON_DIAMETER * 0.8) / size
    for i, a in enumerate(icons):
        for j, b in enumerate(icons):
            if i != j and a.point.dist(b.point) < thr:
                a.occluded = True
                break
