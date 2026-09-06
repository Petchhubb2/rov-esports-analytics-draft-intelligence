"""Enum ทั้งหมดของระบบ

ค่าเหล่านี้ถูกเขียนลง parquet และฐานข้อมูล การเปลี่ยนค่าถือเป็น breaking change
ต้องเพิ่ม migration ไม่ใช่แก้ตรง ๆ
"""

from __future__ import annotations

from enum import StrEnum


class Team(StrEnum):
    BLUE = "BLUE"
    RED = "RED"
    UNKNOWN = "UNKNOWN"

    @property
    def opponent(self) -> Team:
        if self is Team.BLUE:
            return Team.RED
        if self is Team.RED:
            return Team.BLUE
        return Team.UNKNOWN


class FrameState(StrEnum):
    """สถานะของเฟรม มีเพียง LIVE เท่านั้นที่เข้าสู่ Layer 2

    ดู docs/01-assessment.md G3 — ถ้าไม่กรอง replay ข้อมูลตำแหน่งจะปนเปื้อนเงียบ ๆ
    """

    LIVE = "LIVE"
    REPLAY = "REPLAY"
    PAUSE = "PAUSE"
    DRAFT = "DRAFT"
    NON_GAME = "NON_GAME"


class Source(StrEnum):
    """ที่มาของค่าตำแหน่ง — แยก observed ออกจาก inferred ในระดับสคีมา

    ดู docs/03-data-contracts.md — ห้าม query ที่ไม่ระบุ source
    """

    DETECTION = "DETECTION"  # เห็นจริงบน minimap เฟรมนี้
    TRACKING = "TRACKING"  # Kalman ทำนาย ไม่ได้เห็น
    HUD = "HUD"  # อนุมานจาก HUD เช่น ตายอยู่ที่ฐาน
    MANUAL = "MANUAL"  # คนใส่เอง (ground truth)

    @property
    def is_observed(self) -> bool:
        return self is Source.DETECTION


class TrackState(StrEnum):
    OBSERVED = "OBSERVED"  # จับคู่กับ detection ได้ในเฟรมนี้
    COASTING = "COASTING"  # ไม่เห็น แต่ยังอยู่ในช่วงที่ยอมให้ทำนาย
    DEAD = "DEAD"  # HUD ยืนยันว่าตาย ห้ามรับ detection
    UNKNOWN = "UNKNOWN"  # ไม่เห็นและเกินเวลาที่จะเดา — x,y เป็น null


class ObjectiveState(StrEnum):
    ALIVE = "ALIVE"
    DEAD = "DEAD"
    UNKNOWN = "UNKNOWN"


class Objective(StrEnum):
    DRAGON = "DRAGON"
    SLAYER = "SLAYER"


class EventType(StrEnum):
    ROTATION = "ROTATION"
    GANK = "GANK"
    GROUPING = "GROUPING"
    OBJECTIVE_SETUP = "OBJECTIVE_SETUP"
    OBJECTIVE_TAKEN = "OBJECTIVE_TAKEN"
    TEAMFIGHT = "TEAMFIGHT"
    DEATH = "DEATH"
    RESPAWN = "RESPAWN"
    RECALL = "RECALL"
    SPLIT_PUSH = "SPLIT_PUSH"
    LANE_SWAP = "LANE_SWAP"


class LaneRole(StrEnum):
    """ตำแหน่งเลน 5 ตำแหน่งของ RoV — ต่างจาก hero_class

    ดู docs/08-game-reference.md §6
    """

    DS = "ds"  # Dark Slayer lane / ออฟเลน
    JUNGLE = "jungle"  # ป่า
    MID = "mid"  # มิด
    DRAGON = "dragon"  # Abyssal Dragon lane / แครี่
    SUPPORT = "support"  # ซัพพอร์ต


class HeroClass(StrEnum):
    """class ตามที่เกมกำหนด — ฮีโร่มีได้ 1-2 class ตัวแรกเป็นหลัก"""

    MARKSMAN = "marksman"
    MAGE = "mage"
    ASSASSIN = "assassin"
    TANK = "tank"
    WARRIOR = "warrior"
    SUPPORT = "support"


class DamageType(StrEnum):
    PHYSICAL = "physical"
    MAGICAL = "magical"
    TRUE = "true"
    HYBRID = "hybrid"


class DraftAction(StrEnum):
    BAN = "BAN"
    PICK = "PICK"


class Confidence(StrEnum):
    """ป้ายหยาบสำหรับกรณีที่ยัง calibrate ตัวเลขไม่ได้

    ดู docs/01-assessment.md G10 — ตัวเลขทศนิยมที่ไม่ผ่านการวัด
    อันตรายกว่าป้ายหยาบที่ซื่อสัตย์
    """

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
