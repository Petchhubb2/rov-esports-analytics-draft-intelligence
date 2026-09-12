"""Draft state machine — Blueprint §26

รองรับ pick, ban, undo, reset, ประวัติ และกติกา Global Ban-Pick
ลำดับการกระทำมาจากไฟล์ config ไม่ใช่ hardcode เพราะแต่ละรายการต่างกัน
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from rov.domain.enums import DraftAction, Team
from rov.draft.series import GameSideAssignment, SeriesState


class TurnSpec(BaseModel):
    phase: int
    team: Literal["blue", "red"]
    action: DraftAction

    @property
    def team_enum(self) -> Team:
        return Team.BLUE if self.team == "blue" else Team.RED


class GlobalBanPick(BaseModel):
    """กติกา soft fearless

    ยืนยันสองชั้น — จากข้อมูลจริง 270/272 เกม และจากกติกาที่เขียนไว้ตรง ๆ
    ในหน้ารายการของ Liquipedia (ดู source ใน configs/draft/format.yaml)
    """

    enabled: bool = False
    scope: Literal["own_team_only", "both_teams"] = "own_team_only"
    applies_to_bans: bool = False
    reset_on_final_game: bool = True
    # กติกาข้อนี้ยืนยันกับ rulebook แล้วหรือยัง — แยกจาก verified ของลำดับ
    verified: bool = False
    source: str | None = None


class TurnClock(BaseModel):
    """เวลาต่อหนึ่งตา — ใช้บนกระดานเว็บ

    ⚠️ ค่าเริ่มต้นยังไม่ยืนยัน หาไม่พบทั้งในหน้ารายการแข่งของ Liquipedia
    และในคลิปสอนดราฟต์ที่อยู่ใน knowledge/raw/ จึงใส่ค่ามาตรฐานของ MOBA ไว้
    แล้วกำกับ verified: false ตามหลักเดียวกับลำดับ ban/pick

    ยืนยันได้ด้วยการดูคลิปแข่งหนึ่งคลิปแล้วจับเวลาหนึ่งตา
    """

    ban: int = 30
    pick: int = 30
    # เวลาสำรองที่สะสมได้ต่อทีม 0 = ไม่มี
    reserve: int = 0
    verified: bool = False
    source: str | None = None


class SideSelection(BaseModel):
    """สิทธิ์เลือกฝั่ง — มีผลต่อคำแนะนำระดับซีรีส์

    เกมแรกทีมฝั่งซ้ายของตารางเป็นฝ่ายเลือกข้าง เกมถัดไปฝ่ายที่แพ้เกมก่อนเลือก
    แปลว่าทีมที่แพ้เลือกได้ว่าจะเอา blue หรือ red ในเกมถัดไป
    """

    enabled: bool = False
    game1: Literal["home_team", "coin_toss", "unknown"] = "unknown"
    later_games: Literal["previous_loser", "alternate", "unknown"] = "unknown"
    verified: bool = False
    source: str | None = None


class DraftFormat(BaseModel):
    id: str
    name: str | None = None
    verified: bool = False
    bans_per_team: int = 4
    picks_per_team: int = 5
    global_ban_pick: GlobalBanPick = Field(default_factory=GlobalBanPick)
    side_selection: SideSelection = Field(default_factory=SideSelection)
    turn_clock: TurnClock = Field(default_factory=TurnClock)
    sequence: list[TurnSpec] = Field(default_factory=list)
    # ที่มาของลำดับสลับแบน/เลือก — ว่างแปลว่ายังเดาอยู่
    sequence_source: str | None = None

    @model_validator(mode="after")
    def _check_counts(self) -> DraftFormat:
        for team in ("blue", "red"):
            bans = sum(
                1 for t in self.sequence
                if t.team == team and t.action is DraftAction.BAN
            )
            picks = sum(
                1 for t in self.sequence
                if t.team == team and t.action is DraftAction.PICK
            )
            if bans != self.bans_per_team:
                raise ValueError(
                    f"ลำดับมี BAN ของ {team} {bans} ครั้ง "
                    f"แต่ bans_per_team = {self.bans_per_team}"
                )
            if picks != self.picks_per_team:
                raise ValueError(
                    f"ลำดับมี PICK ของ {team} {picks} ครั้ง "
                    f"แต่ picks_per_team = {self.picks_per_team}"
                )
        return self

    @classmethod
    def load(cls, path: str | Path = "configs/draft/format.yaml") -> DraftFormat:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"ไม่พบไฟล์ format: {p}")
        with p.open("r", encoding="utf-8") as fh:
            return cls.model_validate(yaml.safe_load(fh))

    @property
    def total_turns(self) -> int:
        return len(self.sequence)


@dataclass(slots=True)
class Move:
    index: int
    turn: TurnSpec
    hero_id: str


class IllegalMove(ValueError):
    """การกระทำที่ผิดกติกา — บอกเหตุผลเสมอ"""


@dataclass
class DraftState:
    """สถานะการ draft หนึ่งเกม

    Global Ban-Pick อ่านจาก `series` (ประวัติทั้งซีรีส์) ผ่าน `sides` (ทีมไหนอยู่ฝั่งไหน
    ในเกมนี้) — key ด้วย **team identity ไม่ใช่ side** เพื่อให้ถูกเมื่อ BO3/BO5 สลับฝั่ง
    (docs/36-37) · ไม่ส่ง sides/series มา = เกมเดี่ยว ไม่มี series lock
    """

    fmt: DraftFormat
    pool: set[str]
    blue_name: str = "BLUE"
    red_name: str = "RED"
    moves: list[Move] = field(default_factory=list)
    # ★ M2A.5 — series identity: sides = assignment ของเกมนี้ · series = source of truth
    sides: GameSideAssignment | None = None
    series: SeriesState | None = None

    # ------------------------------------------------------------------

    @property
    def turn_index(self) -> int:
        return len(self.moves)

    @property
    def complete(self) -> bool:
        return self.turn_index >= self.fmt.total_turns

    @property
    def current(self) -> TurnSpec | None:
        if self.complete:
            return None
        return self.fmt.sequence[self.turn_index]

    def team_name(self, team: Team) -> str:
        # มี series identity → ใช้ชื่อของทีมที่อยู่ฝั่งนั้นในเกมนี้ (ตาม identity ไม่ใช่ side)
        if self.sides is not None and self.series is not None:
            t = self.series.teams.get(self.sides.team_for_side(team))
            if t is not None:
                return t.display_name
        return self.blue_name if team is Team.BLUE else self.red_name

    # ------------------------------------------------------------------

    def picks(self, team: Team) -> list[str]:
        return [
            m.hero_id for m in self.moves
            if m.turn.team_enum is team and m.turn.action is DraftAction.PICK
        ]

    def bans(self, team: Team) -> list[str]:
        return [
            m.hero_id for m in self.moves
            if m.turn.team_enum is team and m.turn.action is DraftAction.BAN
        ]

    @property
    def all_taken(self) -> set[str]:
        return {m.hero_id for m in self.moves}

    def locked_by_series(self, team: Team) -> set[str]:
        """ฮีโร่ที่ใช้ไม่ได้เพราะกติกา Global Ban-Pick

        resolve ผ่าน identity: side → ทีมที่อยู่ฝั่งนั้นในเกมนี้ → ประวัติของทีมนั้น
        (docs/37 §3) · ไม่มี series/sides = เกมเดี่ยว ไม่มี lock
        """
        if self.sides is None or self.series is None:
            return set()
        team_id = self.sides.team_for_side(team)
        return self.series.locked_heroes_for(team_id, self.fmt)

    # ------------------------------------------------------------------

    def legal_moves(self) -> set[str]:
        """ฮีโร่ที่เลือกหรือแบนได้ในตาปัจจุบัน"""
        turn = self.current
        if turn is None:
            return set()
        available = self.pool - self.all_taken
        g = self.fmt.global_ban_pick
        if turn.action is DraftAction.PICK or g.applies_to_bans:
            available -= self.locked_by_series(turn.team_enum)
        return available

    def why_illegal(self, hero_id: str) -> str | None:
        """เหตุผลที่เลือกไม่ได้ — None แปลว่าเลือกได้"""
        turn = self.current
        if turn is None:
            return "draft จบแล้ว"
        if hero_id not in self.pool:
            return f"ไม่รู้จักฮีโร่ {hero_id}"
        for m in self.moves:
            if m.hero_id == hero_id:
                verb = "แบน" if m.turn.action is DraftAction.BAN else "เลือก"
                return f"{hero_id} ถูก{verb}ไปแล้วโดย {self.team_name(m.turn.team_enum)}"
        if turn.action is DraftAction.PICK or self.fmt.global_ban_pick.applies_to_bans:
            if hero_id in self.locked_by_series(turn.team_enum):
                return (
                    f"{hero_id} ใช้ไม่ได้เพราะกติกา Global Ban-Pick — "
                    f"{self.team_name(turn.team_enum)} ใช้ไปแล้วในเกมก่อนหน้า"
                )
        return None

    # ------------------------------------------------------------------

    def apply(self, hero_id: str) -> Move:
        turn = self.current
        if turn is None:
            raise IllegalMove("draft จบแล้ว")
        reason = self.why_illegal(hero_id)
        if reason:
            raise IllegalMove(reason)
        mv = Move(index=self.turn_index, turn=turn, hero_id=hero_id)
        self.moves.append(mv)
        return mv

    def undo(self) -> Move | None:
        return self.moves.pop() if self.moves else None

    def reset(self) -> None:
        self.moves.clear()

    # ------------------------------------------------------------------

    def board(self) -> str:
        """แสดงกระดาน draft"""
        b_pick, r_pick = self.picks(Team.BLUE), self.picks(Team.RED)
        b_ban, r_ban = self.bans(Team.BLUE), self.bans(Team.RED)
        n = max(self.fmt.picks_per_team, self.fmt.bans_per_team)

        def cell(items: list[str], i: int) -> str:
            return items[i] if i < len(items) else "—"

        lines = [
            f"  {self.blue_name:^22} │ {self.red_name:^22}",
            "  " + "─" * 22 + "─┼─" + "─" * 22,
            f"  {'BAN':^22} │ {'BAN':^22}",
        ]
        for i in range(self.fmt.bans_per_team):
            lines.append(f"  {cell(b_ban, i):^22} │ {cell(r_ban, i):^22}")
        lines.append("  " + "─" * 22 + "─┼─" + "─" * 22)
        lines.append(f"  {'PICK':^22} │ {'PICK':^22}")
        for i in range(self.fmt.picks_per_team):
            lines.append(f"  {cell(b_pick, i):^22} │ {cell(r_pick, i):^22}")
        del n
        return "\n".join(lines)

    def history(self) -> str:
        if not self.moves:
            return "ยังไม่มีการกระทำ"
        out = []
        for m in self.moves:
            out.append(
                f"  {m.index + 1:>2}. {self.team_name(m.turn.team_enum):<8} "
                f"{m.turn.action.value:<4} {m.hero_id}"
            )
        return "\n".join(out)

    def prompt(self) -> str:
        turn = self.current
        if turn is None:
            return "draft เสร็จสมบูรณ์"
        verb = "แบน" if turn.action is DraftAction.BAN else "เลือก"
        return (
            f"ตาที่ {self.turn_index + 1}/{self.fmt.total_turns} · "
            f"เฟส {turn.phase} · {self.team_name(turn.team_enum)} {verb}"
        )
