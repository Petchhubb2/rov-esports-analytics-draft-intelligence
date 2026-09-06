"""พารามิเตอร์ของ pipeline — ห้ามมีตัวเลขวิเศษในโค้ด (หลัก P4)

ค่าเริ่มต้นในไฟล์นี้เป็นการเดาที่สมเหตุสมผล ยังไม่ผ่านการวัด
ทุกค่าที่มีเครื่องหมาย TUNE ต้องปรับด้วยข้อมูลจริงก่อนเชื่อผลลัพธ์
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class SampleParams(BaseModel):
    base_fps: float = 2.0
    dense_fps: float = 5.0
    # ช่วงเวลารอบ objective ที่ควรสุ่มถี่ขึ้น (วินาทีก่อน/หลังเวลาเกิด)
    dense_window_sec: float = 30.0


class DetectParams(BaseModel):
    # TUNE — ทั้งหมดต้องวัดจาก ground truth
    residual_threshold: int = 28
    upscale: int = 2  # ขยาย minimap ก่อน detect เพราะ icon เล็กมากที่ 720p
    min_circularity: float = 0.60
    morph_open: int = 3
    morph_close: int = 5
    # หน้าต่างของ background median
    #
    # วัดแล้วพบว่าหน้าต่างสั้นทำให้ผลแย่ลงชัดเจน (precision 0.92 vs 0.97,
    # recall 0.93 vs 0.97 บนชุดสังเคราะห์) เพราะฮีโร่ที่อยู่นิ่งนาน เช่น
    # ฟาร์มอยู่ในป่าหรือยืนเลน จะถูกนับเข้าไปใน median แล้วกลายเป็นพื้นหลัง
    # ทำให้ตรวจไม่พบตัวเอง
    #
    # เดิมตั้งหน้าต่างสั้นเพราะกังวลว่าป้อมจางสีลงตลอดเกม แต่ป้อมเป็นสี่เหลี่ยม
    # เล็กที่พื้นที่ต่ำกว่าเกณฑ์ขนาดของ icon อยู่แล้ว ตัวกรองขนาดจึงจัดการได้
    # และถ้ายังหลุด ให้ระบุ tower_positions ใน layout เพื่อ mask ทิ้งตรง ๆ
    #
    # ยังคงโครงสร้าง rolling ไว้เผื่อ broadcast ที่มีการเปลี่ยน overlay กลางเกม
    bg_window_sec: float = 600.0
    bg_samples: int = 80
    max_per_team: int = 5


class TrackParams(BaseModel):
    # TUNE — max_speed ต้องวัดจาก percentile 99 ของ ground truth
    # ห้ามเดา เพราะมันคือ gate ที่กันการกระโดดข้ามแมพผิด ๆ
    max_speed: float = 0.09  # normalized ต่อวินาที
    coast_max_sec: float = 3.0
    q_pos: float = 1e-4
    q_vel: float = 1e-3
    r_meas: float = 4e-5
    # น้ำหนักใน cost function ของ Hungarian
    w_distance: float = 1.0
    w_appearance: float = 0.4
    cost_null: float = 0.5
    # ค่าใช้จ่ายของการยอมรับว่าเป็นการ recall กลับฐาน
    cost_teleport: float = 0.35
    # อัปเดต template เฉพาะเมื่อมั่นใจสูง มิฉะนั้นจะเกิด template drift
    template_update_min_conf: float = 0.90


class ZoneParams(BaseModel):
    # hysteresis กันการกระพริบที่ขอบ zone
    # ถ้าไม่มีตัวนี้ การเดินเลียบขอบจะกลายเป็น rotation ปลอมนับสิบครั้งต่อนาที
    dwell_min_sec: float = 1.5
    edge_margin: float = 0.010


class EventParams(BaseModel):
    # ROTATION
    rotation_max_sec: float = 25.0
    rotation_merge_window_sec: float = 3.0
    # GROUPING
    group_radius: float = 0.08  # TUNE — วัดจาก ground truth ว่าระยะเท่าไรคนเรียกว่ารวมตัว
    group_min_size: int = 3
    group_min_sec: float = 3.0
    # OBJECTIVE_SETUP — ค่าตั้งจากรอบเวลาเกิดจริง (docs/08-game-reference.md §3)
    setup_min_sec: float = 5.0
    setup_lead_sec_dragon: float = 45.0  # dragon เกิดใหม่ทุก 120 วินาที
    setup_lead_sec_slayer: float = 60.0  # slayer เกิดใหม่ทุก 300 วินาที
    setup_max_mean_speed: float = 0.02  # ต้องยืนรอ ไม่ใช่เดินผ่าน
    # GANK
    engage_radius: float = 0.05
    gank_window_sec: float = 6.0
    gank_confidence_cap: float = 0.85  # เพดาน เพราะข้อมูลไม่พอจะมั่นใจกว่านี้
    # TEAMFIGHT
    fight_radius: float = 0.10
    fight_min_players: int = 4
    fight_min_per_side: int = 2
    fight_end_sec: float = 3.0
    hp_drop_rate: float = 0.15  # สัดส่วนเลือดที่ลดต่อวินาที ถือว่ากำลังปะทะ
    # SPLIT PUSH
    split_dist: float = 0.30
    split_min_sec: float = 15.0
    # coverage gate (docs/05-macro-events.md R3)
    coverage_flag_below: float = 0.80
    coverage_drop_below: float = 0.50


class ObjectiveTiming(BaseModel):
    """เวลาเกิดของ objective

    ค่าเริ่มต้นมาจากแหล่งก่อนแพตช์ 26 มิ.ย. 2026 ซึ่งมี major jungle system changes
    ต้องวัดซ้ำจากคลิปจริง (docs/08-game-reference.md §3)
    """

    verified: bool = False
    dragon_first: float = 120.0
    dragon_interval: float = 120.0
    dragon_enraged_from: float = 600.0
    dragon_enraged_interval: float = 300.0
    slayer_first: float = 480.0
    slayer_interval: float = 300.0
    sentinel_first: float = 110.0
    sentinel_interval: float = 120.0

    def next_dragon(self, clock: float, last_killed: float | None = None) -> float:
        """วินาทีจนกว่า dragon จะเกิดถัดไป — 0 แปลว่าเกิดอยู่แล้ว"""
        enraged = clock >= self.dragon_enraged_from
        interval = self.dragon_enraged_interval if enraged else self.dragon_interval
        first = self.dragon_enraged_from if enraged else self.dragon_first
        return _next_spawn(clock, first, interval, last_killed)

    def next_slayer(self, clock: float, last_killed: float | None = None) -> float:
        return _next_spawn(clock, self.slayer_first, self.slayer_interval, last_killed)


def _next_spawn(
    clock: float, first: float, interval: float, last_killed: float | None
) -> float:
    if clock < first:
        return first - clock
    if last_killed is None:
        # ยังไม่เคยถูกฆ่า แปลว่ามีชีวิตอยู่ตอนนี้
        return 0.0
    nxt = last_killed + interval
    return max(0.0, nxt - clock)


class EvalParams(BaseModel):
    """เกณฑ์จับคู่ตอนประเมิน — ห้ามแก้โดยไม่บันทึกเหตุผล

    ถ้าแก้ ตัวเลข precision/recall จะเทียบข้ามครั้งไม่ได้
    """

    detection_match_dist: float = 0.02
    event_temporal_iou: float = 0.50


class Params(BaseModel):
    sample: SampleParams = Field(default_factory=SampleParams)
    detect: DetectParams = Field(default_factory=DetectParams)
    track: TrackParams = Field(default_factory=TrackParams)
    zone: ZoneParams = Field(default_factory=ZoneParams)
    events: EventParams = Field(default_factory=EventParams)
    objectives: ObjectiveTiming = Field(default_factory=ObjectiveTiming)
    eval: EvalParams = Field(default_factory=EvalParams)

    @classmethod
    def load(cls, path: str | Path | None = None) -> Params:
        """โหลดจากไฟล์ ถ้าไม่ระบุจะใช้ค่าเริ่มต้นทั้งหมด"""
        if path is None:
            return cls()
        p = Path(path)
        if not p.exists():
            return cls()
        with p.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls.model_validate(data)

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(
                self.model_dump(mode="json"), fh, allow_unicode=True, sort_keys=False
            )

    def config_hash(self) -> str:
        """hash ของ config ใช้ตัดสินว่า stage ต้องรันใหม่หรือไม่ (หลัก P3)"""
        import hashlib
        import json

        blob = json.dumps(self.model_dump(mode="json"), sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:12]
