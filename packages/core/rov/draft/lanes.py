"""matchup แยกตามเลน — context=LANE

**ที่มาของการแยกเลน**

Liquipedia เก็บ pick เป็นช่องเรียงเลข `t1h1..t1h5` เดิมเราคิดว่าเป็นแค่
ลำดับการเลือก จึงใช้ได้แค่ context=TEAM ปรากฏว่า **ช่องเรียงตามเลน**
ตามลำดับ roster ของทีม ไม่ใช่ลำดับการเลือก

หลักฐานจากข้อมูลจริง 1,722 ทีม (ดู `slot_evidence()` ที่คำนวณสดได้)

    ช่อง 1  warrior 47%  assassin 21%  tank 19%     -> DS lane
    ช่อง 2  assassin 48%  warrior 41%               -> jungle
    ช่อง 3  mage 65%                                -> mid
    ช่อง 4  marksman 97%                            -> Abyssal Dragon lane
    ช่อง 5  tank 47%  support 37%                   -> support

ตัวชี้ขาดคือช่อง 4 เป็น marksman 91-100% **ในทุกรายการทั้ง 5 รายการ
ทั้งลีกไทยและไต้หวัน** ถ้าช่องเป็นลำดับการเลือก สัดส่วนจะไม่กระจุกแบบนี้

ระดับฮีโร่ยิ่งชัด — Tachi กับ Billow อยู่ช่อง 2 ที่ 100%,
Y'bneth กับ TeeMee อยู่ช่อง 5 ที่ 100%, Stuart อยู่ช่อง 4 ที่ 100%
52 จาก 67 ตัวที่เล่นบ่อยพอ อยู่เลนเดียว >= 90%

⚠️ **ข้อจำกัด**

1. เป็นการอนุมานจากตำแหน่งช่อง ไม่ใช่ Liquipedia บอกตรง ๆ ว่าเลนไหน
   ทีมที่สลับเลนกลางเกม (lane swap) จะถูกนับตามช่องใน roster อยู่ดี
2. ใช้เฉพาะเกมที่มีครบ 5 ช่อง ถ้าขาดช่องใดช่องหนึ่ง parser จะเลื่อนช่อง
   ขึ้นมาชิดกัน ทำให้เลนเพี้ยน จึงตัดเกมพวกนั้นทิ้ง
3. จำนวนตัวอย่างต่อคู่น้อยกว่า context=TEAM มาก เพราะจับคู่แค่เลนเดียวกัน
   ไม่ใช่ทุกคู่ข้ามทีม การดึงเข้าหาค่ากลางจึงกินแรงกว่าเดิม
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from rov.domain.enums import LaneRole
from rov.draft.importer.parser import SeriesDraft
from rov.draft.stats import ScoredPair

# ช่องที่ i ของ roster = เลนนี้ ลำดับยืนยันแล้วจากข้อมูล 5 รายการ
SLOT_LANES: tuple[LaneRole, ...] = (
    LaneRole.DS,
    LaneRole.JUNGLE,
    LaneRole.MID,
    LaneRole.DRAGON,
    LaneRole.SUPPORT,
)

PICKS_PER_TEAM = len(SLOT_LANES)

# คลาสที่ควรครองแต่ละช่อง ถ้าลำดับช่องถูกต้อง — ใช้ตรวจสมมติฐานเท่านั้น
EXPECTED_DOMINANT: dict[LaneRole, str] = {
    LaneRole.MID: "mage",
    LaneRole.DRAGON: "marksman",
}

# เกณฑ์ส่งออกขั้นต่ำ ตั้งต่ำกว่า context=TEAM เพราะตัวอย่างต่อคู่น้อยกว่ามาก
# หน้าเว็บมีสไลเดอร์ให้ยกเกณฑ์เองอยู่แล้ว ส่งออกเผื่อไว้ให้เลือกได้
MIN_LANE_PAIR_GAMES = 3


@dataclass
class LaneMatchup(ScoredPair):
    """ฮีโร่สองตัวที่อยู่เลนเดียวกันคนละทีมในเกมเดียวกัน

    `adjusted()` และ `counter_score()` มาจาก `ScoredPair` ใน stats.py
    ซึ่งเป็นที่เดียวที่เขียนสูตร — เดิมเขียนซ้ำที่นี่แล้วเพี้ยนจากกันได้เงียบ ๆ
    """

    lane: LaneRole
    hero_id: str
    enemy_id: str
    games: int = 0
    wins: int = 0

    @property
    def losses(self) -> int:
        return self.games - self.wins

    @property
    def raw_win_rate(self) -> float | None:
        return self.wins / self.games if self.games else None


def _lane_rows(all_series: list[SeriesDraft]):
    """คืน (lane, ฮีโร่ฝั่งน้ำเงิน, ฮีโร่ฝั่งแดง, น้ำเงินชนะไหม) ทีละเลน"""
    for s in all_series:
        for g in s.games:
            if not g.complete:
                continue
            blue_won = g.winner_team == g.blue_team
            for i, lane in enumerate(SLOT_LANES):
                yield lane, g.blue_picks[i], g.red_picks[i], blue_won


def lane_usage(all_series: list[SeriesDraft]) -> dict[str, Counter[LaneRole]]:
    """ฮีโร่แต่ละตัวถูกเลือกลงเลนไหนบ้าง กี่ครั้ง

    นี่คือข้อมูลที่ **นับได้จริง** ไม่ใช่การประเมิน จึงคำนวณเองได้
    ต่างจาก lane_roles ใน configs/draft/heroes.yaml ที่เป็นค่าที่คนกรอก
    """
    out: dict[str, Counter[LaneRole]] = defaultdict(Counter)
    for s in all_series:
        for g in s.games:
            for picks in (g.blue_picks, g.red_picks):
                if len(picks) != PICKS_PER_TEAM:
                    continue
                for i, hero in enumerate(picks):
                    out[hero][SLOT_LANES[i]] += 1
    return dict(out)


def main_lane(usage: Counter[LaneRole]) -> tuple[LaneRole, float] | None:
    """เลนหลักของฮีโร่ กับสัดส่วนที่เล่นเลนนั้น"""
    total = sum(usage.values())
    if not total:
        return None
    lane, n = usage.most_common(1)[0]
    return lane, n / total


def compute_lane_matchups(
    all_series: list[SeriesDraft],
) -> dict[tuple[LaneRole, str, str], LaneMatchup]:
    """matchup แบบ context=LANE — เก็บสองทิศทางเหมือน compute_matchups

    key คือ (lane, ฮีโร่, ศัตรู) และ wins คือจำนวนเกมที่ "ฮีโร่" ชนะ
    """
    out: dict[tuple[LaneRole, str, str], LaneMatchup] = {}

    def bump(lane: LaneRole, a: str, b: str, a_won: bool) -> None:
        key = (lane, a, b)
        m = out.get(key)
        if m is None:
            m = out[key] = LaneMatchup(lane=lane, hero_id=a, enemy_id=b)
        m.games += 1
        m.wins += int(a_won)

    for lane, blue, red, blue_won in _lane_rows(all_series):
        if blue == red:
            # ฮีโร่ตัวเดียวกันสองฝั่งเป็นไปไม่ได้ในเกมเดียว แต่กันไว้
            continue
        bump(lane, blue, red, blue_won)
        bump(lane, red, blue, not blue_won)
    return out


def slot_evidence(
    all_series: list[SeriesDraft], hero_class: dict[str, list[str]]
) -> dict:
    """วัดหลักฐานว่าช่องเรียงตามเลนจริงหรือไม่ — คำนวณสดจากข้อมูลที่มี

    คืนสัดส่วนคลาสของแต่ละช่อง กับ `passes` ที่บอกว่าผ่านเกณฑ์ไหม
    เกณฑ์คือช่อง 4 ต้องเป็น marksman เกินครึ่งชัดเจน และช่อง 3 เป็น mage
    ถ้าวันหนึ่ง Liquipedia เปลี่ยนวิธีเก็บ ตัวนี้จะจับได้
    """
    per_slot: list[Counter[str]] = [Counter() for _ in SLOT_LANES]
    teams = 0
    for s in all_series:
        for g in s.games:
            for picks in (g.blue_picks, g.red_picks):
                if len(picks) != PICKS_PER_TEAM:
                    continue
                teams += 1
                for i, hero in enumerate(picks):
                    for c in hero_class.get(hero, []):
                        per_slot[i][c] += 1

    shares: dict[str, dict[str, float]] = {}
    for i, lane in enumerate(SLOT_LANES):
        total = sum(per_slot[i].values())
        shares[lane.value] = (
            {c: round(v / total, 4) for c, v in per_slot[i].most_common(4)}
            if total
            else {}
        )

    passes = all(
        shares.get(lane.value, {}).get(cls, 0.0) > 0.50
        for lane, cls in EXPECTED_DOMINANT.items()
    )
    return {"teams": teams, "class_share_by_lane": shares, "passes": passes}
