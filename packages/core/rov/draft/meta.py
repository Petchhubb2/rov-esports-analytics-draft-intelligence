"""เปรียบเทียบเมต้าข้ามลีกและข้ามฤดูกาล

ทำไมต้องเทียบข้ามลีก
    1. เมต้าของแต่ละภูมิภาคต่างกันจริง ฮีโร่ที่ไทยแบนทุกเกมอาจไม่มีใครแตะที่ไต้หวัน
       ความต่างนี้เองคือข้อมูล scouting ก่อนเจอทีมข้ามภูมิภาค
    2. matchup ต้องการตัวอย่างเยอะ การรวมหลายลีกทำให้คู่ที่เจอกันน้อย
       มีข้อมูลพอจะเชื่อได้เร็วขึ้น
    3. ฮีโร่ที่แข็งในทุกลีก แข็งจริง ส่วนที่แข็งลีกเดียว
       อาจเป็นเพราะสไตล์ของทีมในลีกนั้น ไม่ใช่ตัวฮีโร่

ข้อควรระวัง
    ห้ามรวมข้อมูลข้าม patch โดยไม่แยก (Blueprint §70 ข้อ 5)
    ตอนนี้ยังไม่มี patch กำกับต่อแมตช์ จึงต้องระบุด้วยมือว่าชุดไหนอยู่ patch ใด
    และแสดงช่วงเวลาของข้อมูลควบคู่เสมอ
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rov.draft.importer.parser import SeriesDraft
from rov.draft.stats import (
    MIN_GAMES_RELIABLE,
    SHRINKAGE_K,
    DraftStats,
    MatchupStat,
    compute_matchups,
    compute_stats,
)


@dataclass
class Region:
    """ชุดข้อมูลหนึ่งชุด — ปกติคือหนึ่งลีกหนึ่งฤดูกาล"""

    key: str
    label: str
    series: list[SeriesDraft] = field(default_factory=list)
    stats: DraftStats | None = None

    def compute(self) -> DraftStats:
        if self.stats is None:
            self.stats = compute_stats(self.series)
        return self.stats


@dataclass
class HeroDiff:
    hero_id: str
    presence_a: float
    presence_b: float
    games_a: int
    games_b: int
    wr_a: float | None
    wr_b: float | None

    @property
    def presence_delta(self) -> float:
        return self.presence_a - self.presence_b

    @property
    def both_reliable(self) -> bool:
        return self.games_a >= MIN_GAMES_RELIABLE and self.games_b >= MIN_GAMES_RELIABLE


def compare_regions(a: Region, b: Region, min_presence: float = 0.05) -> list[HeroDiff]:
    """เทียบ presence และ win rate ของฮีโร่ระหว่างสองชุดข้อมูล"""
    sa, sb = a.compute(), b.compute()
    out: list[HeroDiff] = []
    for hid in set(sa.heroes) | set(sb.heroes):
        pa, pb = sa.presence_rate(hid), sb.presence_rate(hid)
        if max(pa, pb) < min_presence:
            continue
        ha, hb = sa.get(hid), sb.get(hid)
        out.append(
            HeroDiff(
                hero_id=hid,
                presence_a=pa,
                presence_b=pb,
                games_a=ha.picks,
                games_b=hb.picks,
                wr_a=ha.adjusted_win_rate(sa.baseline_win_rate) if ha.picks else None,
                wr_b=hb.adjusted_win_rate(sb.baseline_win_rate) if hb.picks else None,
            )
        )
    return sorted(out, key=lambda d: abs(d.presence_delta), reverse=True)


# --------------------------------------------------------------- pooled


@dataclass
class PooledStats:
    """สถิติที่รวมหลายชุดข้อมูลเข้าด้วยกัน"""

    stats: DraftStats
    matchups: dict[tuple[str, str], MatchupStat]
    sources: list[str]
    games_by_source: dict[str, int]

    @property
    def total_games(self) -> int:
        return self.stats.total_games


def pool(regions: list[Region]) -> PooledStats:
    """รวมทุกชุดเข้าด้วยกัน เพื่อให้ matchup มีตัวอย่างมากพอ"""
    all_series: list[SeriesDraft] = []
    by_source: dict[str, int] = {}
    for r in regions:
        all_series.extend(r.series)
        by_source[r.label] = r.compute().total_games
    return PooledStats(
        stats=compute_stats(all_series),
        matchups=compute_matchups(all_series),
        sources=[r.label for r in regions],
        games_by_source=by_source,
    )


def top_counters(
    pooled: PooledStats, hero_id: str, min_games: int = 10, limit: int = 8
) -> tuple[list[tuple[str, MatchupStat, float]], list[tuple[str, MatchupStat, float]]]:
    """คู่ที่ฮีโร่นี้ได้เปรียบและเสียเปรียบที่สุด

    คืน (ได้เปรียบ, เสียเปรียบ) โดยแต่ละรายการเป็น (ศัตรู, สถิติ, counter score)
    counter score ถ่วงด้วยความมั่นใจแล้ว คู่ที่ข้อมูลน้อยจึงเข้าใกล้ 0 เอง
    """
    prior = pooled.stats.baseline_win_rate
    rows = [
        (enemy, m, m.counter_score(prior))
        for (h, enemy), m in pooled.matchups.items()
        if h == hero_id and m.games >= min_games
    ]
    rows.sort(key=lambda r: r[2], reverse=True)
    return rows[:limit], list(reversed(rows[-limit:]))


# --------------------------------------------------------------- รายงาน


def region_summary(regions: list[Region]) -> str:
    lines = ["═══ ชุดข้อมูลที่มี ═══", "",
             f"{'ลีก / ฤดูกาล':<38}{'เกม':>6}{'ฮีโร่':>7}{'blue wr':>9}{'ยาวกลาง':>9}"]
    total = 0
    for r in regions:
        s = r.compute()
        total += s.total_games
        bw = s.blue_side_win_rate
        ml = s.median_game_length
        lines.append(
            f"{r.label:<38}{s.total_games:>6}{len(s.heroes):>7}"
            f"{(f'{bw:.1%}' if bw is not None else '-'):>9}"
            f"{(f'{ml / 60:.1f} น.' if ml else '-'):>9}"
        )
    lines.append("")
    lines.append(f"รวมทั้งหมด {total} เกม")
    return "\n".join(lines)


def compare_report(a: Region, b: Region, top: int = 15) -> str:
    diffs = compare_regions(a, b)
    lines = [
        f"═══ เทียบเมต้า: {a.label} vs {b.label} ═══",
        "",
        f"{'hero':<16}{a.key:>9}{b.key:>9}{'ต่าง':>8}{'wr ' + a.key:>10}{'wr ' + b.key:>10}",
    ]
    for d in diffs[:top]:
        wa = f"{d.wr_a:.3f}" if d.wr_a is not None else "-"
        wb = f"{d.wr_b:.3f}" if d.wr_b is not None else "-"
        lines.append(
            f"{d.hero_id:<16}{d.presence_a:>8.0%}{d.presence_b:>9.0%}"
            f"{d.presence_delta:>+8.0%}{wa:>10}{wb:>10}"
        )

    only_a = [d for d in diffs if d.presence_b < 0.02 and d.presence_a >= 0.15]
    only_b = [d for d in diffs if d.presence_a < 0.02 and d.presence_b >= 0.15]
    if only_a:
        lines += ["", f"เล่นเฉพาะใน {a.label}: " + ", ".join(d.hero_id for d in only_a[:12])]
    if only_b:
        lines += ["", f"เล่นเฉพาะใน {b.label}: " + ", ".join(d.hero_id for d in only_b[:12])]
    lines += ["", "หมายเหตุ: ค่าต่างของ presence คือความต่างของเมต้าจริงระหว่างภูมิภาค",
              "ใช้เป็นข้อมูล scouting ก่อนเจอทีมข้ามภูมิภาคได้"]
    return "\n".join(lines)


def counter_report(pooled: PooledStats, hero_id: str, min_games: int = 10) -> str:
    good, bad = top_counters(pooled, hero_id, min_games=min_games)
    h = pooled.stats.get(hero_id)
    lines = [
        f"═══ ตัวแก้ของ {hero_id} ═══",
        f"ข้อมูลรวม {pooled.total_games} เกม จาก {len(pooled.sources)} รายการ",
        f"{hero_id} ถูกเลือก {h.picks} ครั้ง ถูกแบน {h.bans} ครั้ง "
        f"wr {h.adjusted_win_rate(0.5):.3f}",
        "",
        f"เจอแล้วได้เปรียบ (อย่างน้อย {min_games} เกม)",
        f"  {'ศัตรู':<16}{'ชนะ/เกม':>10}{'counter':>10}",
    ]
    if not good:
        lines.append("  (ยังไม่มีคู่ที่ข้อมูลถึงเกณฑ์)")
    for enemy, m, score in good:
        lines.append(f"  {enemy:<16}{f'{m.wins}/{m.games}':>10}{score:>+10.1f}")
    lines += ["", "เจอแล้วเสียเปรียบ", f"  {'ศัตรู':<16}{'ชนะ/เกม':>10}{'counter':>10}"]
    if not bad:
        lines.append("  (ยังไม่มีคู่ที่ข้อมูลถึงเกณฑ์)")
    for enemy, m, score in bad:
        lines.append(f"  {enemy:<16}{f'{m.wins}/{m.games}':>10}{score:>+10.1f}")
    lines += [
        "",
        f"counter score ถ่วงด้วยขนาดตัวอย่างแล้ว (k={SHRINKAGE_K})",
        "คู่ที่ข้อมูลน้อยจะเข้าใกล้ 0 เอง ไม่ใช่ค่าสุดโต่ง",
        "",
        "⚠ นี่คือ context=TEAM คือเจอกันคนละทีมในเกมเดียวกัน",
        "ยังไม่ใช่การดวลกันในเลนเดียวกัน ซึ่งต้องรอ role assignment จาก vision",
    ]
    return "\n".join(lines)
