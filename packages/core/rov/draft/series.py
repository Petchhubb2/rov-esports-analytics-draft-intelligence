"""Series identity & Global Ban-Pick — PHASE M2A.5

**Side (BLUE/RED) มีอายุแค่หนึ่งเกม · Team identity คงที่ข้ามซีรีส์**

บั๊กที่โมดูลนี้แก้ (docs/36): runtime เดิมเก็บ series history โดย key = side ไม่ใช่ identity
เมื่อ BO3/BO5 สลับฝั่ง จะ lock ฮีโร่ผิดทีม · โมดูลนี้ทำให้ทุก lock/score key ด้วย team_id

หลักการ (docs/37):
    - `GameRecord[]` เป็น **source of truth เดียว และ immutable** — บันทึกแล้วห้ามเขียนทับ
    - `heroes_used_by` / `wins_of` เป็น **derived view** ไม่ใช่ store แยกที่ mutate ได้
    - `id` ของทีมคงที่ · `display_name` แก้ได้ · เปลี่ยนชื่อห้ามขยับ history/locks/wins
    - "swap sides" แก้ได้เฉพาะ assignment ของเกมปัจจุบัน/ถัดไป ห้ามแตะ record เก่า
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rov.domain.enums import Team

if TYPE_CHECKING:
    from rov.draft.state import DraftFormat


@dataclass(frozen=True)
class TeamIdentity:
    """ทีมที่คงที่ข้ามซีรีส์

    `id` เสถียรและไม่เปลี่ยน (เช่น "TEAM_A"/"TEAM_B" สำหรับ manual session หรือ
    team id จากข้อมูลการแข่งเมื่อมี) · `display_name` ใช้แสดงผลเท่านั้น แก้ได้
    การเปลี่ยน display_name ต้องไม่ขยับ history / wins / locks (docs/37 §2)
    """

    id: str
    display_name: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("TeamIdentity.id ต้องไม่ว่าง")
        if not self.display_name:
            object.__setattr__(self, "display_name", self.id)


@dataclass(frozen=True)
class GameSideAssignment:
    """ทีมไหนอยู่ฝั่งไหนใน **หนึ่งเกม** — side เป็นของชั่วคราวต่อเกม"""

    blue_team_id: str
    red_team_id: str

    def __post_init__(self) -> None:
        if self.blue_team_id == self.red_team_id:
            raise ValueError("ทีมเดียวกันอยู่สองฝั่งพร้อมกันไม่ได้")

    def team_for_side(self, side: Team) -> str:
        if side is Team.BLUE:
            return self.blue_team_id
        if side is Team.RED:
            return self.red_team_id
        raise ValueError(f"side ต้องเป็น BLUE หรือ RED ไม่ใช่ {side}")

    def side_for_team(self, team_id: str) -> Team | None:
        if team_id == self.blue_team_id:
            return Team.BLUE
        if team_id == self.red_team_id:
            return Team.RED
        return None

    def swapped(self) -> GameSideAssignment:
        """สลับ blue<->red — คืน assignment ใหม่ ไม่แตะของเดิม (invariant #3)"""
        return GameSideAssignment(
            blue_team_id=self.red_team_id, red_team_id=self.blue_team_id
        )


@dataclass(frozen=True)
class GameRecord:
    """snapshot ของเกมที่จบแล้ว — **immutable** ห้ามเขียนทับ (invariant #4)

    เก็บ assignment ของเกมนั้นไว้ในตัว จึงถาม picks_of(team_id) ได้โดยไม่ต้องรู้ side
    winner เก็บเป็น team_id ไม่ใช่ "blue"/"red" (correction #4)
    """

    game_no: int
    assignment: GameSideAssignment
    blue_picks: tuple[str, ...] = ()
    red_picks: tuple[str, ...] = ()
    blue_bans: tuple[str, ...] = ()
    red_bans: tuple[str, ...] = ()
    winner_team_id: str | None = None

    def picks_of(self, team_id: str) -> tuple[str, ...]:
        side = self.assignment.side_for_team(team_id)
        if side is Team.BLUE:
            return self.blue_picks
        if side is Team.RED:
            return self.red_picks
        return ()

    def bans_of(self, team_id: str) -> tuple[str, ...]:
        side = self.assignment.side_for_team(team_id)
        if side is Team.BLUE:
            return self.blue_bans
        if side is Team.RED:
            return self.red_bans
        return ()

    def won_by(self, team_id: str) -> bool:
        return self.winner_team_id is not None and self.winner_team_id == team_id


@dataclass
class SeriesState:
    """สถานะทั้งซีรีส์ — `games` เป็น source of truth เดียว ที่เหลือ derive จากมัน"""

    teams: dict[str, TeamIdentity] = field(default_factory=dict)
    games: list[GameRecord] = field(default_factory=list)
    current_assignment: GameSideAssignment | None = None
    best_of: int | None = None

    # ---- derived views (ไม่มี store แยก — correction #2) ----------------

    def heroes_used_by(self, team_id: str) -> set[str]:
        """ฮีโร่ที่ทีมนี้ pick ไปแล้วในเกมก่อน ๆ ของซีรีส์ — คำนวณสดจาก games"""
        out: set[str] = set()
        for g in self.games:
            out |= set(g.picks_of(team_id))
        return out

    def wins_of(self, team_id: str) -> int:
        """จำนวนเกมที่ทีมนี้ชนะ — ตาม team_id ไม่ใช่ side (correction #4)"""
        return sum(1 for g in self.games if g.won_by(team_id))

    def game_no(self) -> int:
        """หมายเลขเกมถัดไปที่กำลังจะดราฟต์ (1-based)"""
        return len(self.games) + 1

    def is_final_game(self) -> bool:
        """เกมถัดไปเป็นเกมสุดท้ายที่เป็นไปได้ของซีรีส์หรือไม่ (Bo7 เกม 7)"""
        return (
            self.best_of is not None
            and self.best_of > 1
            and self.game_no() >= self.best_of
        )

    def locked_heroes_for(self, team_id: str, fmt: DraftFormat) -> set[str]:
        """ฮีโร่ที่ทีมนี้ใช้ไม่ได้เพราะกติกา Global Ban-Pick ของ fmt

        คงกติกาเดิมทุกประการ (docs/37 §5) — ต่างจากของเดิมแค่ key = team_id
        """
        g = fmt.global_ban_pick
        if not g.enabled:
            return set()
        if g.reset_on_final_game and self.is_final_game():
            return set()
        if g.scope == "both_teams":
            out: set[str] = set()
            for tid in self.teams:
                out |= self.heroes_used_by(tid)
            return out
        return self.heroes_used_by(team_id)

    # ---- mutation: เพิ่มเกมใหม่เท่านั้น (record เก่า immutable) -----------

    def record(self, game: GameRecord) -> None:
        self.games.append(game)


def team_ids(assignment: GameSideAssignment) -> tuple[str, str]:
    """คู่ team_id ของ assignment เรียง (blue, red)"""
    return assignment.blue_team_id, assignment.red_team_id
