"""สถิติฮีโร่จากข้อมูล draft จริง

ทุกตัวเลขในโมดูลนี้คำนวณจากแมตช์ที่เกิดขึ้นจริง ไม่มีค่าที่ตั้งขึ้นเอง
ค่าที่เป็นการประเมินเชิงคุณภาพอยู่ใน rov/draft/heroes.py แยกกันคนละที่โดยเจตนา

หลักการสำคัญ (docs/01-assessment.md G8)
    ห้ามใช้ win rate ดิบ ต้องดึงเข้าหาค่ากลางตามจำนวนเกม
    มิฉะนั้นฮีโร่ที่เล่น 3 เกมชนะ 3 จะได้ 100% และขึ้นอันดับหนึ่งตลอดกาล
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from rov.draft.importer.parser import GameDraft, SeriesDraft

# ค่าความแรงของการดึงเข้าหาค่ากลาง ยิ่งสูงยิ่งต้องมีเกมเยอะจึงจะขยับจาก prior
# 30 หมายถึงต้องมีราว 30 เกมจึงจะเชื่อครึ่งหนึ่งของค่าที่วัดได้
SHRINKAGE_K = 30

# จำนวนเกมขั้นต่ำก่อนแสดงตัวเลขโดยไม่มีคำเตือน
MIN_GAMES_RELIABLE = 15


@dataclass
class HeroStat:
    hero_id: str
    picks: int = 0
    bans: int = 0
    wins: int = 0
    # ความยาวเกมที่ฮีโร่นี้ลงเล่น ใช้ประเมินแนวโน้มช่วงเกม
    win_lengths: list[float] = field(default_factory=list)
    loss_lengths: list[float] = field(default_factory=list)

    @property
    def games(self) -> int:
        return self.picks

    @property
    def losses(self) -> int:
        return self.picks - self.wins

    @property
    def raw_win_rate(self) -> float | None:
        """win rate ดิบ — ห้ามใช้จัดอันดับ ใช้ดูเปรียบเทียบเท่านั้น"""
        return self.wins / self.picks if self.picks else None

    @property
    def presence(self) -> int:
        """ถูกหยิบหรือถูกแบน = ทีมให้ความสำคัญ"""
        return self.picks + self.bans

    def adjusted_win_rate(self, prior: float, k: int = SHRINKAGE_K) -> float:
        """Beta-Binomial shrinkage เข้าหาค่ากลางของ patch"""
        return (self.wins + k * prior) / (self.picks + k)

    def confidence(self, k: int = SHRINKAGE_K) -> float:
        """0..1 — ความมั่นใจที่ได้จากขนาดตัวอย่าง"""
        return self.picks / (self.picks + k) if self.picks else 0.0

    @property
    def reliable(self) -> bool:
        return self.picks >= MIN_GAMES_RELIABLE


@dataclass
class DraftStats:
    """สถิติรวมของชุดข้อมูลหนึ่งชุด"""

    heroes: dict[str, HeroStat] = field(default_factory=dict)
    total_games: int = 0
    blue_wins: int = 0
    game_lengths: list[float] = field(default_factory=list)

    # ------------------------------------------------------------------

    @property
    def baseline_win_rate(self) -> float:
        """ค่ากลางที่ใช้เป็น prior — 0.5 ตามนิยาม เพราะทุกเกมมีผู้ชนะหนึ่งฝ่าย"""
        return 0.5

    @property
    def blue_side_win_rate(self) -> float | None:
        """อคติของฝั่ง — ต้องรู้ก่อนตีความ win rate ของฮีโร่"""
        return self.blue_wins / self.total_games if self.total_games else None

    @property
    def median_game_length(self) -> float | None:
        if not self.game_lengths:
            return None
        s = sorted(self.game_lengths)
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

    def get(self, hero_id: str) -> HeroStat:
        return self.heroes.setdefault(hero_id, HeroStat(hero_id=hero_id))

    # ------------------------------------------------------------------

    def pick_rate(self, hero_id: str) -> float:
        return self.get(hero_id).picks / self.total_games if self.total_games else 0.0

    def ban_rate(self, hero_id: str) -> float:
        return self.get(hero_id).bans / self.total_games if self.total_games else 0.0

    def presence_rate(self, hero_id: str) -> float:
        return self.get(hero_id).presence / self.total_games if self.total_games else 0.0

    def ranked_by_presence(self) -> list[HeroStat]:
        """เรียงตามความสำคัญในเมตา ใช้จัดลำดับว่าจะกรอก attribute ตัวไหนก่อน"""
        return sorted(self.heroes.values(), key=lambda h: h.presence, reverse=True)

    def ranked_by_win_rate(self, min_games: int = MIN_GAMES_RELIABLE) -> list[HeroStat]:
        pool = [h for h in self.heroes.values() if h.picks >= min_games]
        return sorted(
            pool, key=lambda h: h.adjusted_win_rate(self.baseline_win_rate), reverse=True
        )

    # ------------------------------------------------------------------

    def game_length_tendency(self, hero_id: str) -> tuple[float | None, int]:
        """สัญญาณช่วงเกมที่คำนวณจากข้อมูลจริง

        แนวคิด: ฮีโร่ที่ชนะในเกมสั้นและแพ้ในเกมยาว มีแนวโน้มเป็นสายต้นเกม
        คืน (คะแนน -1..+1, จำนวนเกมที่ใช้)
            ค่าลบ  = แนวโน้มเก่งช่วงต้น
            ค่าบวก = แนวโน้มเก่งช่วงท้าย

        ข้อจำกัดที่ต้องรู้: สัญญาณนี้หยาบและปนกับความแข็งของทีม
        ใช้เป็น "ตัวช่วยจัดลำดับ" ตอนกรอก attribute เท่านั้น
        ห้ามใช้แทนค่า scaling ที่คนกรอก
        """
        h = self.get(hero_id)
        n = len(h.win_lengths) + len(h.loss_lengths)
        if n < 8 or not h.win_lengths or not h.loss_lengths:
            return None, n
        mw = sum(h.win_lengths) / len(h.win_lengths)
        ml = sum(h.loss_lengths) / len(h.loss_lengths)
        median = self.median_game_length or 1.0
        # เกมที่ชนะยาวกว่าเกมที่แพ้ = ยิ่งยืดยิ่งได้เปรียบ = สายท้ายเกม
        raw = (mw - ml) / max(median, 1.0)
        return max(-1.0, min(1.0, raw * 2.0)), n


def compute_stats(all_series: list[SeriesDraft]) -> DraftStats:
    """คำนวณสถิติจากซีรีส์ที่แยกข้อมูลมาแล้ว

    นับเฉพาะเกมที่ข้อมูลครบ เกมที่ยังไม่ได้เล่น (map ว่างใน Bo5) ไม่นับ
    """
    st = DraftStats()
    for series in all_series:
        for g in series.complete_games:
            _accumulate(st, g)
    return st


def _accumulate(st: DraftStats, g: GameDraft) -> None:
    st.total_games += 1
    if g.winner_team and g.winner_team == g.blue_team:
        st.blue_wins += 1
    if g.length_sec:
        st.game_lengths.append(g.length_sec)

    for team, picks in ((g.blue_team, g.blue_picks), (g.red_team, g.red_picks)):
        won = g.winner_team is not None and team == g.winner_team
        for hid in picks:
            h = st.get(hid)
            h.picks += 1
            if won:
                h.wins += 1
                if g.length_sec:
                    h.win_lengths.append(g.length_sec)
            elif g.length_sec:
                h.loss_lengths.append(g.length_sec)

    for hid in set(g.blue_bans) | set(g.red_bans):
        st.get(hid).bans += 1


# ---------------------------------------------------------------- matchup


@dataclass
class MatchupStat:
    hero_id: str
    enemy_id: str
    games: int = 0
    wins: int = 0

    def adjusted(self, prior: float, k: int = SHRINKAGE_K) -> float:
        return (self.wins + k * prior) / (self.games + k)

    def counter_score(self, prior: float, k: int = SHRINKAGE_K) -> float:
        """ดีกว่าปกติแค่ไหน ถ่วงด้วยความมั่นใจ

        คู่ที่ไม่มีข้อมูลได้ 0 โดยอัตโนมัติ ไม่ใช่ค่าสุดโต่ง
        """
        conf = self.games / (self.games + k) if self.games else 0.0
        return (self.adjusted(prior, k) - prior) * 100.0 * conf


def compute_matchups(all_series: list[SeriesDraft]) -> dict[tuple[str, str], MatchupStat]:
    """matchup แบบ context=TEAM — ฮีโร่คนละทีมในเกมเดียวกัน

    จับคู่ทุกตัวข้ามทีม ไม่สนว่ายืนเลนไหน ตัวอย่างจึงเยอะแต่ปนข้ามเลน

    ถ้าอยากได้เฉพาะคู่ที่ประกบกันในเลนเดียวกัน ใช้
    `rov.draft.lanes.compute_lane_matchups()` แทน — ช่อง t1h1..t1h5 ของ
    Liquipedia เรียงตามเลนจริง (ยืนยันแล้ว ดู rov/draft/lanes.py)
    ไม่ต้องรอ role assignment จาก vision pipeline อย่างที่เคยเขียนไว้ตรงนี้
    """
    out: dict[tuple[str, str], MatchupStat] = {}

    def bump(a: str, b: str, won: bool) -> None:
        key = (a, b)
        m = out.get(key)
        if m is None:
            m = out[key] = MatchupStat(hero_id=a, enemy_id=b)
        m.games += 1
        if won:
            m.wins += 1

    for series in all_series:
        for g in series.complete_games:
            blue_won = g.winner_team == g.blue_team
            for a in g.blue_picks:
                for b in g.red_picks:
                    bump(a, b, blue_won)
                    bump(b, a, not blue_won)
    return out


def compute_synergies(all_series: list[SeriesDraft]) -> dict[tuple[str, str], MatchupStat]:
    """คู่ฮีโร่ในทีมเดียวกัน — เก็บทิศทางเดียวโดยเรียงชื่อ

    ระวัง: ตัวเลขนี้ปนเปื้อนด้วย "ทีมเก่งเล่นคู่นี้บ่อย"
    ต้องเทียบกับค่าที่คาดหวังก่อนตีความ ดู expected_synergy()
    """
    out: dict[tuple[str, str], MatchupStat] = {}
    for series in all_series:
        for g in series.complete_games:
            for team, picks in ((g.blue_team, g.blue_picks), (g.red_team, g.red_picks)):
                won = g.winner_team is not None and team == g.winner_team
                for i, a in enumerate(sorted(picks)):
                    for b in sorted(picks)[i + 1 :]:
                        key = (a, b)
                        m = out.get(key)
                        if m is None:
                            m = out[key] = MatchupStat(hero_id=a, enemy_id=b)
                        m.games += 1
                        if won:
                            m.wins += 1
    return out


def expected_synergy(stats: DraftStats, a: str, b: str) -> float:
    """win rate ที่ควรได้ถ้าฮีโร่สองตัวไม่มีผลต่อกันเลย

    ใช้เทียบกับค่าที่วัดได้จริง ส่วนต่างคือ synergy ที่แท้จริง
    ยังไม่สมบูรณ์เพราะไม่ได้หักความแข็งของทีมออก แต่ดีกว่าใช้ค่าดิบมาก
    """
    p = stats.baseline_win_rate
    wa = stats.get(a).adjusted_win_rate(p)
    wb = stats.get(b).adjusted_win_rate(p)
    # รวมความน่าจะเป็นแบบ odds ไม่ใช่คูณตรง ๆ เพราะทุกเกมมีผู้ชนะเสมอ
    oa = wa / max(1e-9, 1 - wa)
    ob = wb / max(1e-9, 1 - wb)
    o = math.sqrt(max(1e-9, oa * ob))
    return o / (1 + o)


def hero_priority_order(stats: DraftStats) -> list[tuple[str, int, float]]:
    """ลำดับที่ควรกรอก attribute — เรียงตามความสำคัญในเมตาจริง

    คืน (hero_id, presence, presence_rate)
    ฮีโร่ที่ไม่เคยถูกหยิบหรือแบนในระดับ pro แทบไม่มีผลต่อ draft engine
    """
    return [
        (h.hero_id, h.presence, stats.presence_rate(h.hero_id))
        for h in stats.ranked_by_presence()
    ]


def report(stats: DraftStats, top: int = 20) -> str:
    lines = [
        "═══ สถิติจากข้อมูล draft จริง ═══",
        f"เกมที่ใช้คำนวณ    {stats.total_games}",
        f"ฮีโร่ที่พบ         {len(stats.heroes)}",
    ]
    if (bw := stats.blue_side_win_rate) is not None:
        lines.append(f"blue side win     {bw:.1%}")
    if (ml := stats.median_game_length) is not None:
        lines.append(f"ความยาวเกมกลาง    {ml / 60:.1f} นาที")

    lines += ["", f"── {top} อันดับแรกตาม presence (pick + ban) ──",
              f"{'hero':<16}{'pick':>6}{'ban':>6}{'pres%':>8}{'wr':>8}{'wr_adj':>9}{'n':>5}"]
    for h in stats.ranked_by_presence()[:top]:
        wr = h.raw_win_rate
        adj = h.adjusted_win_rate(stats.baseline_win_rate)
        mark = "" if h.reliable else " *"
        lines.append(
            f"{h.hero_id:<16}{h.picks:>6}{h.bans:>6}"
            f"{stats.presence_rate(h.hero_id):>7.0%}"
            f"{(f'{wr:.0%}' if wr is not None else '-'):>8}"
            f"{adj:>9.3f}{h.picks:>5}{mark}"
        )
    lines.append("")
    lines.append(f"* = เล่นน้อยกว่า {MIN_GAMES_RELIABLE} เกม ตัวเลขยังเชื่อไม่ได้")
    return "\n".join(lines)
