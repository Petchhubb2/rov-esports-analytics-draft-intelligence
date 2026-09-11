"""Baseline สำหรับเทียบกับ Draft Engine — PHASE M0.5

**ทำไมต้องมี**

`docs/21-phase-b-report.md §8` ข้อ 3 บันทึกไว้ว่า "top-1 4.8% ตีความไม่ได้
เพราะไม่มี baseline เทียบ" — ตัวเลขลอย ๆ บอกไม่ได้ว่าดีหรือแย่
ไฟล์นี้คือตัวเทียบนั้น

**หลักการออกแบบ baseline**

baseline ที่ดีต้อง **โง่พอที่จะไม่ใช่ engine** แต่ **ฉลาดพอที่จะเอาชนะยาก**
ถ้า baseline โง่เกินไป การชนะมันไม่ได้พิสูจน์อะไร
ถ้า baseline ฉลาดเกินไป มันก็คือ engine อีกตัว

ทั้งสาม baseline ใช้ `PooledStats` ชุดเดียวกับ engine ซึ่งสร้างจาก train เท่านั้น
และเห็นสถานะดราฟต์เท่ากัน — ต่างกันแค่ "ใช้ข้อมูลอะไรตัดสิน"

**สิ่งที่ baseline ทั้งหมดไม่มี และ engine มี**

    counter / synergy      ความสัมพันธ์กับตัวที่เปิดมาแล้ว
    น้ำหนักที่ไหลตามบริบท   weights_for()
    composition            (ยังน้ำหนัก 0 ใน PHASE B)

ถ้า engine ชนะ baseline ได้ แปลว่าสามอย่างนี้มีค่าจริง ถ้าแพ้ แปลว่ายังไม่มีค่า
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rov.domain.enums import DraftAction
from rov.draft.meta import PooledStats
from rov.draft.recommend import needed_lanes
from rov.draft.state import DraftState


@dataclass(frozen=True)
class TurnContext:
    """ทุกอย่างที่ ranker เห็น ณ ตาหนึ่ง — เท่ากันทุกตัวเพื่อความเป็นธรรม"""

    state: DraftState
    pooled: PooledStats
    lane_usage: dict[str, dict[str, int]]
    lanes: list[str]
    lane_matchups: dict
    hero_db: object | None
    min_games: int

    @property
    def is_ban(self) -> bool:
        turn = self.state.current
        return turn is not None and turn.action is DraftAction.BAN

    @property
    def subject_picks(self) -> list[str]:
        """ตัวที่ฝ่ายที่เรากำลังคิดแทนเลือกไปแล้ว

        ตอนแบนมองจากมุมศัตรู เหมือนที่ `recommend()` ทำ —
        baseline ต้องใช้มุมเดียวกัน ไม่งั้นเทียบกันไม่ได้
        """
        turn = self.state.current
        if turn is None:
            return []
        team = turn.team_enum
        subject = team.opponent if self.is_ban else team
        return self.state.picks(subject)

    def candidates(self) -> list[str]:
        """ฮีโร่ที่เลือกได้จริงในตานี้ และมีข้อมูลถึงเกณฑ์

        กรองเหมือน `recommend()` ทุกประการ เพื่อให้ทุก ranker
        เลือกจากกลุ่มเดียวกันเป๊ะ ๆ
        """
        legal = self.state.legal_moves()
        if self.is_ban:
            turn = self.state.current
            subject = turn.team_enum.opponent
            legal = legal - self.state.locked_by_series(subject)
        stats = self.pooled.stats
        return [h for h in legal if stats.get(h).picks >= self.min_games]


class Ranker(Protocol):
    """จัดอันดับฮีโร่ทั้งหมดที่เลือกได้ในตานี้

    ต้องคืน **ทุกตัว** ไม่ใช่แค่ top-k เพราะ MRR และ mean rank
    ต้องรู้อันดับของตัวที่ทีมอาชีพเลือกจริง ซึ่งอาจอยู่อันดับ 40
    """

    name: str
    description: str
    limitations: str

    def rank(self, ctx: TurnContext) -> list[str]: ...


# ---------------------------------------------------------------- Baseline A


class PresenceBaseline:
    """เลือกตัวที่ทีมอาชีพให้ค่ามากที่สุด — ไม่สนอะไรอย่างอื่นเลย

    เป็น baseline ที่เดาได้ง่ายที่สุดและมักแข็งกว่าที่คิด เพราะเมตาของ RoV
    กระจุกตัวสูง ตัวที่ presence สูงถูกหยิบหรือแบนเกือบทุกเกมอยู่แล้ว
    """

    name = "A · presence"
    description = "เรียงตาม pick + ban ในข้อมูล train ล้วน"
    limitations = (
        "ไม่รู้จักสถานะเกมเลย — แนะนำเหมือนกันทุกตาไม่ว่าอีกฝั่งจะเปิดอะไรมา "
        "และไม่รู้ว่าตำแหน่งไหนเต็มแล้ว"
    )

    def rank(self, ctx: TurnContext) -> list[str]:
        st = ctx.pooled.stats
        return sorted(
            ctx.candidates(),
            key=lambda h: (-st.get(h).presence, h),
        )


# ---------------------------------------------------------------- Baseline B


class WinRateBaseline:
    """เลือกตัวที่อัตราชนะสูงสุด ใช้ shrinkage ชุดเดียวกับระบบจริง

    ใช้ `adjusted_win_rate(prior, SHRINKAGE_K)` ตัวเดียวกับที่ engine ใช้
    เพื่อให้ความต่างที่วัดได้มาจาก "วิธีตัดสิน" ไม่ใช่ "วิธีคำนวณ win rate"
    """

    name = "B · win rate"
    description = "เรียงตาม adjusted win rate (shrinkage k=30 เหมือน engine)"
    limitations = (
        "win rate ระดับอาชีพเกาะ 50% โดยธรรมชาติ เพราะทุกเกมมีผู้ชนะหนึ่งฝ่าย "
        "ความต่างระหว่างตัวบนกับตัวล่างจึงแคบและไวต่อ noise · "
        "ตัวที่เล่นน้อยถูกดึงเข้าหา 0.5 จนแยกกันแทบไม่ออก"
    )

    def rank(self, ctx: TurnContext) -> list[str]:
        st = ctx.pooled.stats
        prior = st.baseline_win_rate
        return sorted(
            ctx.candidates(),
            key=lambda h: (-st.get(h).adjusted_win_rate(prior), h),
        )


# ---------------------------------------------------------------- Baseline C


class RoleAwarePresenceBaseline:
    """กรองด้วยตำแหน่งที่ยังว่างก่อน แล้วค่อยเรียงตาม presence

    เป็น baseline ที่แข็งที่สุดในสามตัว เพราะรู้สองอย่างที่คนดราฟต์จริงรู้ —
    ตัวไหนอยู่ในเมตา และตำแหน่งไหนยังไม่มีคนลง

    ใช้ `needed_lanes()` ตัวเดียวกับ engine เพื่อให้ความต่างที่เหลือ
    มาจาก counter/synergy/น้ำหนักไดนามิก ไม่ใช่จากวิธีคิดเรื่องเลน
    """

    name = "C · role + presence"
    description = "ตัวที่ลงตำแหน่งที่ยังว่างได้ก่อน แล้วเรียงตาม presence"
    limitations = (
        "เลนมาจากการอนุมานช่อง roster (rov/draft/lanes.py) ซึ่งทีมที่สลับเลน "
        "กลางเกมจะถูกนับผิด · และยังไม่รู้เรื่อง counter/synergy เลย"
    )

    def rank(self, ctx: TurnContext) -> list[str]:
        st = ctx.pooled.stats
        lu, lanes = ctx.lane_usage, ctx.lanes
        cands = ctx.candidates()
        if not lu or not lanes:
            return PresenceBaseline().rank(ctx)

        need = needed_lanes(ctx.subject_picks, lu, lanes)

        def share_in_need(h: str) -> float:
            """สัดส่วนการเล่นของฮีโร่ที่ตกในเลนที่ยังต้องการ"""
            usage = lu.get(h)
            if not usage or not need:
                return 1.0
            total = sum(usage.values())
            if not total:
                return 1.0
            return sum(usage.get(ln, 0) for ln in need) / total

        # เรียงสองชั้น: ลงเลนที่ว่างได้ไหมก่อน แล้วค่อย presence
        # ไม่ได้ตัดตัวที่ลงไม่ได้ทิ้ง เพราะข้อมูลเลนไม่สมบูรณ์
        # และตัวเฟลกอาจไปลงเลนอื่นได้ — หลักเดียวกับ ROLE_FLOOR ใน engine
        return sorted(
            cands,
            key=lambda h: (-round(share_in_need(h), 3), -st.get(h).presence, h),
        )


# ------------------------------------------------------------------ engine


class EngineRanker:
    """Draft Engine ปัจจุบัน — ห่อให้เข้า interface เดียวกับ baseline

    เรียก `recommend()` ด้วย `limit` ใหญ่พอที่จะได้ทุกตัว
    เพราะต้องรู้อันดับของตัวที่ทีมอาชีพเลือกจริง แม้มันจะอยู่อันดับท้าย ๆ
    """

    name = "current engine"
    description = "meta + winrate + counter + synergy ถ่วงด้วย role_fit"
    limitations = (
        "counter/synergy เป็น context=TEAM ซึ่งปนคู่ที่ไม่เคยประกบกัน · "
        "น้ำหนักยังไม่เคย fit กับผลแพ้ชนะ · factor ของ PHASE B ยังน้ำหนัก 0"
    )

    def __init__(self, recommend_fn):
        self._recommend = recommend_fn

    def scores(self, ctx: TurnContext) -> list[tuple[str, float]]:
        """(ฮีโร่, คะแนนรวม) เรียงจากมากไปน้อย — ใช้วัด calibration

        baseline ไม่มีเมธอดนี้เพราะมีแต่ลำดับ ไม่มีคะแนนที่ตีความได้
        """
        sugs = self._recommend(
            ctx.state,
            ctx.pooled,
            limit=10**6,
            min_games=ctx.min_games,
            lane_usage=ctx.lane_usage or None,
            lanes=ctx.lanes or None,
            lane_matchups=ctx.lane_matchups or None,
            hero_db=ctx.hero_db,
        )
        return [(s.hero_id, s.total) for s in sugs]

    def rank(self, ctx: TurnContext) -> list[str]:
        return [h for h, _ in self.scores(ctx)]


def default_rankers(recommend_fn) -> list[Ranker]:
    """ชุดมาตรฐานที่ใช้เทียบ — engine ก่อน แล้วตามด้วย baseline A B C"""
    return [
        EngineRanker(recommend_fn),
        PresenceBaseline(),
        WinRateBaseline(),
        RoleAwarePresenceBaseline(),
    ]
