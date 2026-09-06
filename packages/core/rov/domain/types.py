"""Type หลักที่ไหลผ่าน pipeline

สคีมาเหล่านี้ตรงกับ docs/03-data-contracts.md
ถ้าแก้ที่นี่ ต้องแก้เอกสารและ store/artifacts.py ให้ตรงกัน
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rov.domain.enums import (
    EventType,
    FrameState,
    ObjectiveState,
    Source,
    Team,
    TrackState,
)
from rov.domain.geometry import Point

# ----------------------------------------------------------------- Layer 1


@dataclass(slots=True)
class FrameRecord:
    """หนึ่งเฟรมที่สุ่มมา — Layer 1

    มีสองแกนเวลาโดยเจตนา (ดู docs/01-assessment.md G2)
      video_time  ใช้กระโดดดูวิดีโอ
      game_clock  ใช้วิเคราะห์ทุกอย่าง
    """

    frame_idx: int
    pts: float
    video_time: float
    game_id: str | None = None
    game_clock: float | None = None
    clock_conf: float = 0.0
    frame_state: FrameState = FrameState.LIVE
    state_reason: str = ""
    minimap_ok: bool = True
    dragon_state: ObjectiveState = ObjectiveState.UNKNOWN
    slayer_state: ObjectiveState = ObjectiveState.UNKNOWN
    obj_state_conf: float = 0.0

    @property
    def usable(self) -> bool:
        """เฟรมนี้เข้าสู่ Layer 2 ได้หรือไม่"""
        return self.frame_state is FrameState.LIVE and self.minimap_ok


# ----------------------------------------------------------------- Layer 2


@dataclass(slots=True)
class Detection:
    """blob ที่ตรวจพบบน minimap — ยังไม่รู้ว่าเป็นใคร

    ไม่มี hero_id และ player_id โดยเจตนา
    การผูก identity เป็นหน้าที่ของ tracking เท่านั้น
    """

    frame_idx: int
    det_id: int
    px: float  # pixel ภายใน minimap crop
    py: float
    point: Point  # normalized 0..1
    radius: float
    area: float
    circularity: float
    team_hint: Team = Team.UNKNOWN
    team_conf: float = 0.0
    det_conf: float = 0.0
    patch: Any | None = field(default=None, repr=False)  # np.ndarray ของ icon


@dataclass(slots=True)
class HudSlot:
    """สถานะหนึ่งช่องใน side HUD

    alive จากที่นี่คือแหล่งความจริงหลักเรื่องความเป็นความตาย
    ไม่ใช่การหายไปของ icon บน minimap (ดู docs/01-assessment.md G4)
    """

    frame_idx: int
    slot: int  # 0-4 ทีมน้ำเงิน, 5-9 ทีมแดง
    alive: bool | None = None
    respawn_in: float | None = None
    level: int | None = None
    hp_frac: float | None = None
    conf: float = 0.0


@dataclass(slots=True)
class TrackSample:
    """ผลของ assignment สำหรับหนึ่ง slot ในหนึ่งเฟรม"""

    frame_idx: int
    slot: int
    det_id: int | None
    point: Point | None
    vx: float
    vy: float
    state: TrackState
    age_since_obs: float
    assign_cost: float
    conf: float


@dataclass(slots=True)
class Observation:
    """ตารางหลักของ Layer 2 — ทุกอย่างใน Layer 3/4 ต่อยอดจากที่นี่

    กฎการใช้งาน: ห้าม filter ด้วย `point is not None` เฉย ๆ
    เพราะจะปนค่าที่เดา (TRACKING) กับค่าที่เห็นจริง (DETECTION)
    ต้องระบุ source ทุกครั้ง
    """

    match_id: str
    game_id: str
    game_clock: float
    video_time: float
    slot: int
    player_id: str
    hero_id: str
    team: Team
    point: Point | None
    zone: str | None
    zone_raw: str | None
    visible: bool
    alive: bool
    source: Source
    confidence: float

    @property
    def is_observed(self) -> bool:
        return self.source.is_observed and self.visible


# ----------------------------------------------------------------- Layer 3


@dataclass(slots=True)
class Event:
    """Layer 3 — ทุก event ต้องอธิบายที่มาของตัวเองได้

    evidence คือคำตอบของแผนเดิม §41 ที่ว่าต้องแสดงเหตุผลเป็น metrics
    coverage บอกว่าช่วงเวลานั้นมีข้อมูลจริงกี่เปอร์เซ็นต์
    """

    event_id: str
    match_id: str
    game_id: str
    event_type: EventType
    start_clock: float
    end_clock: float
    team: Team | None = None
    player_ids: list[str] = field(default_factory=list)
    slots: list[int] = field(default_factory=list)
    zone_from: str | None = None
    zone_to: str | None = None
    confidence: float = 0.0
    coverage: float = 0.0
    detector_version: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return self.end_clock - self.start_clock

    @property
    def low_coverage(self) -> bool:
        """ต่ำกว่า 0.8 ต้องติดธง ต่ำกว่า 0.5 ไม่ควรรายงานเลย

        ดู docs/05-macro-events.md R3
        """
        return self.coverage < 0.8


@dataclass(slots=True)
class MatchPlayer:
    """ผูก slot ใน HUD เข้ากับผู้เล่นและฮีโร่ — คงที่ตลอดเกม

    ตัวนี้ทำให้ tracker ไม่ต้องรู้จักชื่อฮีโร่เลย
    มันแค่รักษาความต่อเนื่องของ slot 10 ช่อง (ดู docs/04-vision-pipeline.md §5.1)
    """

    match_id: str
    slot: int
    player_id: str
    hero_id: str
    team: Team
    lane_role: str | None = None
