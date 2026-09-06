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
    """Event ทั้ง 13 ชนิดตาม Blueprint §16

    OBJECTIVE แยกสี่สถานะโดยเจตนา เพราะ "เข้าไปเซ็ตอัพ" "แย่งกัน"
    "ได้มา" และ "เสียไป" ให้ข้อมูลเชิงกลยุทธ์คนละอย่างกัน
    การยุบรวมจะทำให้คำนวณอัตราสำเร็จของการเซ็ตอัพไม่ได้
    """

    ROTATION = "ROTATION"
    GROUPING = "GROUPING"
    GANK = "GANK"
    OBJECTIVE_SETUP = "OBJECTIVE_SETUP"
    OBJECTIVE_CONTEST = "OBJECTIVE_CONTEST"
    OBJECTIVE_TAKEN = "OBJECTIVE_TAKEN"
    OBJECTIVE_LOST = "OBJECTIVE_LOST"
    TEAMFIGHT = "TEAMFIGHT"
    DEATH = "DEATH"
    RESPAWN = "RESPAWN"
    RECALL = "RECALL"
    LANE_SWAP = "LANE_SWAP"
    SPLIT_PUSH = "SPLIT_PUSH"


class DataLayer(StrEnum):
    """ชั้นข้อมูล 5 ชั้นตาม Blueprint §54

    กฎเหล็ก: ชั้นบนห้ามเขียนทับชั้นล่าง
    ลบชั้น 3-5 ทิ้งแล้วสร้างใหม่จากชั้น 2 ได้เสมอ

    แผนเดิมมี 4 ชั้น Blueprint ใหม่แทรก ANALYTICS เข้ามาระหว่าง EVENT กับ INSIGHT
    เพราะสถิติที่รวมแล้ว (เช่น dragon first rotation 68%) ต่างจากข้อสรุป
    (เช่น objective-oriented jungler) และต้องตรวจสอบแยกกันได้
    """

    RAW = "L1_RAW"
    OBSERVATION = "L2_OBSERVATION"
    EVENT = "L3_EVENT"
    ANALYTICS = "L4_ANALYTICS"
    INSIGHT = "L5_INSIGHT"


class PlanTier(StrEnum):
    """ระดับของแผน macro ตาม Blueprint §44"""

    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    EMERGENCY = "EMERGENCY"


class GamePhase(StrEnum):
    """ช่วงของเกม — ใช้เป็นเงื่อนไขของ macro rule

    Blueprint §41 เตือนว่าอย่าใช้เวลาอย่างเดียวตัดสิน ต้องดู objective state
    level power spike wave state gold vision ประกอบด้วย
    ค่านี้จึงเป็นแค่หนึ่งในเงื่อนไข ไม่ใช่ตัวตัดสิน
    """

    OPENING = "OPENING"  # 0:00-1:00
    EARLY = "EARLY"  # 1:00-5:00
    MID = "MID"  # 5:00-12:00
    LATE = "LATE"  # 12:00+


class MacroTag(StrEnum):
    """ป้ายลักษณะ macro ของฮีโร่ ตาม Blueprint §39"""

    FAST_CLEAR = "FAST_CLEAR"
    EARLY_GANK = "EARLY_GANK"
    EARLY_PRESSURE = "EARLY_PRESSURE"
    SCALING = "SCALING"
    OBJECTIVE = "OBJECTIVE"
    ENGAGE = "ENGAGE"
    PEEL = "PEEL"
    POKE = "POKE"
    DIVE = "DIVE"
    SPLIT_PUSH = "SPLIT_PUSH"


class MacroShape(StrEnum):
    """โครงสร้างการกระจายตัวของทีม ตาม Blueprint §43"""

    S_3_1_1 = "3-1-1"
    S_3_2 = "3-2"
    S_4_1 = "4-1"
    S_1_3_1 = "1-3-1"
    S_5_MAN = "5-MAN"
    S_2_2_1 = "2-2-1"


class JobStatus(StrEnum):
    """สถานะของ processing job ตาม Blueprint §7 และ §56"""

    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    EXTRACTING = "EXTRACTING"
    DETECTING = "DETECTING"
    TRACKING = "TRACKING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    @property
    def is_terminal(self) -> bool:
        return self in (JobStatus.COMPLETED, JobStatus.FAILED)


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
