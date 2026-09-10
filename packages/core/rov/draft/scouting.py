"""Scouting ต่อทีม — Blueprint §33 · docs/06-draft-engine.md

**ทำไมต้องมีแยกจาก stats.py**

`stats.py` ตอบว่า "ลีกนี้ให้ค่าฮีโร่ตัวไหน" ซึ่งเป็นค่าเฉลี่ยข้ามทุกทีม
แต่ตอนดราฟต์จริงเราไม่ได้เจอ "ลีก" เราเจอ **ทีมหนึ่งทีม** ที่มีคนห้าคน
แต่ละคนถนัดไม่กี่ตัว โค้ชระดับสูงจึงแบนตามคู่แข่ง ไม่ใช่แบนตามเมตารวม

โมดูลนี้ตอบคำถามที่ต่างออกไป

    ทีมนี้เปิดตัวอะไรบ่อย                pick_counts
    เลนไหนของเขาแคบ แบนแล้วเจ็บ         lane_pools + narrowness
    เขากลัวอะไร (สิ่งที่เขาแบนซ้ำ ๆ)      ban_counts
    แบนอะไรถึงจะกินพื้นที่เขาได้มากที่สุด    target_bans

**ข้อมูลมาจากไหน**

`team1` `team2` `date` ถูก parse อยู่แล้วใน importer/parser.py ตั้งแต่ต้น
แต่ก่อนหน้านี้ไม่มีใครใช้ โมดูลนี้ไม่ต้องดึงข้อมูลเพิ่มแม้แต่ request เดียว

**ข้อจำกัดที่ต้องบอกผู้ใช้เสมอ**

1. Liquipedia ไม่ได้เก็บว่า *ผู้เล่นคนไหน* เล่นตัวไหน เก็บแค่ระดับทีม
   เมื่อทีมเปลี่ยนตัวผู้เล่นกลางฤดูกาล ข้อมูลเก่าจะเพี้ยนโดยไม่มีสัญญาณเตือน
2. จำนวนเกมต่อทีมน้อยกว่าระดับลีกมาก (สิบ ๆ ไม่ใช่ร้อย ๆ)
   ทุกตัวเลขจึงต้องแสดง n ควบเสมอ และห้ามใช้ win rate ดิบต่อทีม
3. เลนอนุมานจากช่องของ roster เหมือน lanes.py — ข้อจำกัดเดียวกันทั้งหมด
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date

from rov.domain.enums import LaneRole
from rov.draft.importer.parser import SeriesDraft
from rov.draft.lanes import PICKS_PER_TEAM, SLOT_LANES

# ทีมที่มีเกมน้อยกว่านี้ ไม่ควรสรุปอะไรเกี่ยวกับสไตล์ของเขา
MIN_TEAM_GAMES = 6

# เลนจะเรียกว่า "แคบ" เมื่อตัวยอดนิยม N ตัวแรกกินสัดส่วนเกินเกณฑ์นี้
NARROW_TOP_N = 3
NARROW_SHARE = 0.75

_MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
        ],
        start=1,
    )
}

_DATE_RE = re.compile(r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})")


def parse_date(raw: str | None) -> date | None:
    """แปลงวันที่แบบ Liquipedia ("January 31, 2026 - 12:00 {{Abbr/ICT}}")

    คืน None เมื่ออ่านไม่ได้ ผู้เรียกต้องจัดการเอง ไม่เดาเป็นวันนี้
    เพราะการเดาวันที่จะทำให้ตัวถ่วงตามความใหม่ผิดแบบเงียบ ๆ
    """
    if not raw:
        return None
    m = _DATE_RE.search(raw)
    if not m:
        return None
    month = _MONTHS.get(m.group(1).lower())
    if not month:
        return None
    try:
        return date(int(m.group(3)), month, int(m.group(2)))
    except ValueError:
        return None


def date_range(
    all_series: list[SeriesDraft], played_only: bool = True
) -> tuple[date | None, date | None]:
    """ช่วงวันที่ของชุดข้อมูล — ใช้เตือนว่ากำลังรวมข้ามแพตช์อยู่หรือเปล่า

    ค่าเริ่มต้นนับเฉพาะซีรีส์ที่ **แข่งไปแล้วจริง** (มีเกมที่ข้อมูลครบ)

    จำเป็นเพราะ Liquipedia ลงตารางแมตช์ล่วงหน้าไว้ด้วย ในชุดข้อมูลชุดนี้
    มีนัดที่ยังไม่แข่งลากวันสูงสุดไปถึงสองเดือนข้างหน้า ถ้านับรวม
    ช่วง "120 วันล่าสุด" จะเลื่อนตามอนาคตไปเรื่อย ๆ แล้วกินแมตช์จริงน้อยลง
    """
    src = [s for s in all_series if s.complete_games] if played_only else all_series
    ds = [d for s in src if (d := parse_date(s.date))]
    return (min(ds), max(ds)) if ds else (None, None)


def filter_since(all_series: list[SeriesDraft], since: date) -> list[SeriesDraft]:
    """เก็บเฉพาะซีรีส์ตั้งแต่วันที่กำหนด

    ซีรีส์ที่ไม่มีวันที่จะถูก**ตัดทิ้ง** ไม่ใช่เก็บไว้ เพราะเจตนาของผู้เรียก
    คือ "เอาเฉพาะช่วงนี้" การเก็บของที่ไม่รู้วันไว้จะทำให้ผลไม่ตรงคำถาม
    """
    out = []
    for s in all_series:
        d = parse_date(s.date)
        if d and d >= since:
            out.append(s)
    return out


# ---------------------------------------------------------------- โปรไฟล์ทีม


@dataclass
class TeamProfile:
    """สิ่งที่ทีมหนึ่งทำซ้ำ ๆ — ทุกช่องมี n ควบเสมอ"""

    team: str
    games: int = 0
    wins: int = 0
    blue_games: int = 0
    blue_wins: int = 0

    pick_counts: Counter[str] = field(default_factory=Counter)
    ban_counts: Counter[str] = field(default_factory=Counter)
    # เลน -> ฮีโร่ที่ทีมนี้ส่งลงเลนนั้น
    lane_pools: dict[LaneRole, Counter[str]] = field(default_factory=dict)
    first_seen: date | None = None
    last_seen: date | None = None

    # ------------------------------------------------------------------

    @property
    def reliable(self) -> bool:
        return self.games >= MIN_TEAM_GAMES

    @property
    def win_rate(self) -> float | None:
        """ดิบ — ใช้แสดงเท่านั้น ห้ามใช้จัดอันดับ (ดู docs/01 G8)"""
        return self.wins / self.games if self.games else None

    def lane_pool(self, lane: LaneRole) -> Counter[str]:
        return self.lane_pools.get(lane, Counter())

    def pool_size(self, lane: LaneRole) -> int:
        """จำนวนตัวที่ทีมนี้เคยส่งลงเลนนั้น"""
        return len(self.lane_pool(lane))

    def narrowness(self, lane: LaneRole) -> tuple[float, int, int]:
        """สัดส่วนที่ตัวยอดนิยม 3 ตัวแรกกินไป · จำนวนตัวทั้งหมด · จำนวนเกม

        ยิ่งสัดส่วนสูงยิ่งแบนง่าย เพราะตัดสองสามตัวแล้วเขาไม่เหลือของถนัด
        """
        pool = self.lane_pool(lane)
        total = sum(pool.values())
        if not total:
            return 0.0, 0, 0
        top = sum(n for _, n in pool.most_common(NARROW_TOP_N))
        return top / total, len(pool), total

    def narrow_lanes(self) -> list[tuple[LaneRole, float, int, int]]:
        """เลนที่แคบพอจะกดดันด้วยการแบน เรียงจากแคบที่สุด"""
        out = []
        for lane in SLOT_LANES:
            share, n_heroes, n_games = self.narrowness(lane)
            if n_games >= MIN_TEAM_GAMES and share >= NARROW_SHARE:
                out.append((lane, share, n_heroes, n_games))
        return sorted(out, key=lambda r: r[1], reverse=True)

    def signature_heroes(self, top: int = 8) -> list[tuple[str, int, float]]:
        """ตัวที่ทีมนี้หยิบบ่อยกว่าปกติ — คืน (hero, ครั้ง, สัดส่วนของเกม)"""
        if not self.games:
            return []
        return [
            (h, n, n / self.games) for h, n in self.pick_counts.most_common(top)
        ]


def team_profiles(all_series: list[SeriesDraft]) -> dict[str, TeamProfile]:
    """สร้างโปรไฟล์ของทุกทีมที่พบในชุดข้อมูล

    ใช้เฉพาะเกมที่มีครบ 5 ช่องทั้งสองฝั่ง เหมือน lanes.py
    เพราะถ้าช่องขาด parser จะเลื่อนช่องชิดกัน ทำให้เลนเพี้ยน
    """
    out: dict[str, TeamProfile] = {}

    def prof(team: str) -> TeamProfile:
        if team not in out:
            out[team] = TeamProfile(team=team, lane_pools=defaultdict(Counter))
        return out[team]

    for series in all_series:
        d = parse_date(series.date)
        for g in series.complete_games:
            for team, picks, bans, is_blue in (
                (g.blue_team, g.blue_picks, g.blue_bans, True),
                (g.red_team, g.red_picks, g.red_bans, False),
            ):
                if not team:
                    continue
                p = prof(team)
                p.games += 1
                won = g.winner_team == team
                p.wins += int(won)
                if is_blue:
                    p.blue_games += 1
                    p.blue_wins += int(won)
                p.pick_counts.update(picks)
                p.ban_counts.update(bans)
                if len(picks) == PICKS_PER_TEAM:
                    for lane, hero in zip(SLOT_LANES, picks, strict=True):
                        p.lane_pools[lane][hero] += 1
                if d:
                    p.first_seen = min(p.first_seen or d, d)
                    p.last_seen = max(p.last_seen or d, d)

    for p in out.values():
        p.lane_pools = dict(p.lane_pools)
    return out


def find_team(profiles: dict[str, TeamProfile], query: str) -> TeamProfile | None:
    """ค้นทีมแบบไม่สนตัวพิมพ์ และยอมให้พิมพ์แค่บางส่วนถ้าไม่กำกวม"""
    q = query.strip().lower()
    for name, p in profiles.items():
        if name.lower() == q:
            return p
    hits = [p for name, p in profiles.items() if q and q in name.lower()]
    return hits[0] if len(hits) == 1 else None


# ------------------------------------------------------------------ target ban


@dataclass
class TargetBan:
    hero_id: str
    lane: LaneRole | None
    team_picks: int
    team_share: float          # สัดส่วนของเกมที่ทีมนี้หยิบตัวนี้
    league_share: float        # สัดส่วนของเกมที่ทั้งลีกหยิบตัวนี้
    lift: float                # team_share / league_share
    lane_pressure: float       # สัดส่วนที่ตัวนี้กินในเลนของทีมนั้น
    score: float
    reason: str


def target_bans(
    profile: TeamProfile,
    league_pick_rate: dict[str, float],
    limit: int = 8,
    min_team_picks: int = 3,
    exclude: set[str] | None = None,
) -> list[TargetBan]:
    """ตัวที่ควรแบนเพื่อกดดัน "ทีมนี้โดยเฉพาะ" ไม่ใช่ตามเมตารวม

    คะแนนรวมสามอย่าง

        lift          เขาหยิบบ่อยกว่าที่ลีกหยิบแค่ไหน — ตัวประจำตัวได้คะแนนสูง
        lane_pressure ตัวนี้กินพื้นที่เลนเขาเท่าไร — แบนแล้วเลนนั้นเหลือน้อย
        ความถี่ดิบ    กันไม่ให้ตัวที่หยิบ 3 ครั้งแต่ลีกไม่เคยหยิบพุ่งขึ้นบนสุด

    ตัวที่ทีมหยิบน้อยกว่า `min_team_picks` ถูกตัดทิ้ง เพราะ lift ของตัวอย่าง
    ขนาดเล็กเป็นสัญญาณรบกวนล้วน ๆ
    """
    if not profile.games:
        return []
    exclude = exclude or set()

    hero_lane: dict[str, LaneRole] = {}
    lane_totals: dict[LaneRole, int] = {}
    for lane, pool in profile.lane_pools.items():
        lane_totals[lane] = sum(pool.values())
        for hero, n in pool.items():
            # ถ้าตัวเดียวลงหลายเลน ให้ถือเลนที่เขาใช้มันบ่อยที่สุด
            cur = hero_lane.get(hero)
            if cur is None or n > profile.lane_pools[cur].get(hero, 0):
                hero_lane[hero] = lane

    out: list[TargetBan] = []
    for hero, n in profile.pick_counts.items():
        if hero in exclude or n < min_team_picks:
            continue
        team_share = n / profile.games
        league = league_pick_rate.get(hero, 0.0)
        # กันหารศูนย์ และกันไม่ให้ตัวที่ลีกแทบไม่หยิบได้ lift มหาศาล
        lift = team_share / max(league, 0.02)

        lane = hero_lane.get(hero)
        lane_total = lane_totals.get(lane, 0) if lane else 0
        lane_pressure = (
            profile.lane_pools[lane][hero] / lane_total
            if lane and lane_total
            else 0.0
        )

        score = (
            100.0 * team_share * 0.45
            + 100.0 * min(lift, 4.0) / 4.0 * 0.35
            + 100.0 * lane_pressure * 0.20
        )

        bits = [f"หยิบ {n}/{profile.games} เกม ({team_share:.0%})"]
        if lift >= 1.6:
            bits.append(f"บ่อยกว่าลีก {lift:.1f} เท่า")
        if lane and lane_pressure >= 0.4:
            bits.append(f"กิน {lane_pressure:.0%} ของเลน {lane.value}")
        out.append(
            TargetBan(
                hero_id=hero,
                lane=lane,
                team_picks=n,
                team_share=team_share,
                league_share=league,
                lift=lift,
                lane_pressure=lane_pressure,
                score=score,
                reason=" · ".join(bits),
            )
        )

    out.sort(key=lambda t: t.score, reverse=True)
    return out[:limit]


# ---------------------------------------------------------------------- report


def report(profile: TeamProfile, bans: list[TargetBan] | None = None) -> str:
    p = profile
    lines = [f"═══ {p.team} ═══", ""]
    wr = p.win_rate
    span = ""
    if p.first_seen and p.last_seen:
        span = f" · {p.first_seen.isoformat()} ถึง {p.last_seen.isoformat()}"
    lines.append(
        f"  {p.games} เกม · ชนะ {p.wins}"
        + (f" ({wr:.0%})" if wr is not None else "")
        + span
    )
    if p.blue_games:
        bwr = p.blue_wins / p.blue_games
        lines.append(f"  ฝั่งน้ำเงิน {p.blue_games} เกม ชนะ {bwr:.0%}")
    if not p.reliable:
        lines.append(f"  ⚠ ข้อมูลน้อยกว่า {MIN_TEAM_GAMES} เกม ยังสรุปสไตล์ไม่ได้")

    lines += ["", "  ── hero pool แต่ละเลน ──"]
    for lane in SLOT_LANES:
        pool = p.lane_pool(lane)
        if not pool:
            continue
        share, n_heroes, n_games = p.narrowness(lane)
        top = " · ".join(f"{h} {n}" for h, n in pool.most_common(4))
        tag = "  ← แคบ" if share >= NARROW_SHARE and n_games >= MIN_TEAM_GAMES else ""
        lines.append(f"  {lane.value:<8} {n_heroes:>2} ตัว / {n_games:>2} เกม  {top}{tag}")

    narrow = p.narrow_lanes()
    if narrow:
        lines += ["", "  ── เลนที่กดดันด้วยการแบนได้ ──"]
        for lane, share, n_heroes, n_games in narrow:
            lines.append(
                f"  {lane.value:<8} 3 ตัวแรกกิน {share:.0%} ของ {n_games} เกม "
                f"(มีทั้งหมด {n_heroes} ตัว)"
            )

    if p.ban_counts:
        top_bans = " · ".join(f"{h} {n}" for h, n in p.ban_counts.most_common(6))
        lines += ["", f"  แบนบ่อย  {top_bans}"]

    if bans:
        lines += ["", "  ── ควรแบนอะไรใส่ทีมนี้ ──", ""]
        lines.append(f"  {'#':<3}{'hero':<16}{'เลน':<9}{'คะแนน':>7}  เหตุผล")
        for i, t in enumerate(bans, 1):
            lane = t.lane.value if t.lane else "—"
            lines.append(f"  {i:<3}{t.hero_id:<16}{lane:<9}{t.score:>7.1f}  {t.reason}")

    lines += [
        "",
        "  ข้อมูลระดับทีม ไม่ใช่ระดับผู้เล่น — เปลี่ยนตัวผู้เล่นแล้วตัวเลขนี้เพี้ยนได้",
    ]
    return "\n".join(lines)
