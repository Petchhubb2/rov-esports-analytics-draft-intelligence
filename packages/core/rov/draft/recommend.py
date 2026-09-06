"""คำแนะนำ pick และ ban จากข้อมูลจริง — Blueprint §33

**ทุกองค์ประกอบมาจากแมตช์ที่เกิดขึ้นจริง ไม่มีค่าที่ตั้งขึ้นเอง**

องค์ประกอบ 4 อย่าง แต่ละอย่างบอกที่มาและจำนวนเกมได้

    meta     ฮีโร่นี้ถูก pick หรือ ban บ่อยแค่ไหน = ทีมอาชีพให้ค่าแค่ไหน
    winrate  อัตราชนะที่ถ่วงด้วยขนาดตัวอย่างแล้ว
    counter  ผลรวมความได้เปรียบเมื่อเจอฮีโร่ที่ศัตรูเลือกไปแล้ว
    synergy  ความเข้ากันกับฮีโร่ที่ทีมเราเลือกไปแล้ว

สิ่งที่ยัง**ไม่ได้**คิดเข้าไป เพราะยังไม่มีข้อมูล
    composition (ต้องรอกรอก hero attribute)
    ความถนัดของผู้เล่นแต่ละคน (ต้องรอ player stats)
    สภาพเลน (ต้องรอ vision pipeline)

จึงต้องเรียกผลลัพธ์นี้ว่า "คำแนะนำจากสถิติ" ไม่ใช่ "ตัวที่ดีที่สุด"
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rov.domain.enums import DraftAction
from rov.draft.meta import PooledStats
from rov.draft.state import DraftState

# น้ำหนักเริ่มต้น ยังไม่ผ่านการ validate ด้วยผลแพ้ชนะ
# ต้อง fit ด้วย logistic regression เมื่อมีข้อมูลพอ (docs/06 §6)
DEFAULT_WEIGHTS = {
    "meta": 0.30,
    "winrate": 0.30,
    "counter": 0.25,
    "synergy": 0.15,
}

# จำนวนเกมขั้นต่ำของคู่ ก่อนจะนำ matchup มาคิด
MIN_PAIR_GAMES = 8


@dataclass
class Component:
    key: str
    label: str
    raw: float
    scaled: float  # 0-100
    detail: str


@dataclass
class Suggestion:
    hero_id: str
    total: float
    components: dict[str, Component] = field(default_factory=dict)
    games: int = 0
    reasons: list[str] = field(default_factory=list)

    @property
    def reliable(self) -> bool:
        return self.games >= 15


def _scale(value: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 50.0
    return max(0.0, min(100.0, 100.0 * (value - lo) / (hi - lo)))


def recommend(
    state: DraftState,
    pooled: PooledStats,
    weights: dict[str, float] | None = None,
    limit: int = 8,
    min_games: int = 5,
) -> list[Suggestion]:
    """จัดอันดับฮีโร่ที่ควรเลือกหรือแบนในตาปัจจุบัน"""
    turn = state.current
    if turn is None:
        return []

    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    stats = pooled.stats
    prior = stats.baseline_win_rate
    team = turn.team_enum
    is_ban = turn.action is DraftAction.BAN

    # ตอนแบน ให้มองจากมุมของศัตรู — เราอยากตัดตัวที่ดีต่อ "เขา"
    subject = team.opponent if is_ban else team
    ours = state.picks(subject)
    theirs = state.picks(subject.opponent)

    legal = state.legal_moves()
    if is_ban:
        # ฮีโร่ที่ศัตรูใช้ไม่ได้อยู่แล้วเพราะ Global Ban-Pick ไม่ต้องเสียตาแบน
        legal = legal - state.locked_by_series(subject)

    candidates = [h for h in legal if stats.get(h).picks >= min_games]
    if not candidates:
        return []

    presences = [stats.presence_rate(h) for h in candidates]
    p_lo, p_hi = min(presences), max(presences)

    out: list[Suggestion] = []
    for hid in candidates:
        hs = stats.get(hid)
        s = Suggestion(hero_id=hid, total=0.0, games=hs.picks)

        pres = stats.presence_rate(hid)
        s.components["meta"] = Component(
            "meta", "Meta", pres, _scale(pres, p_lo, p_hi),
            f"pick {hs.picks} ban {hs.bans} จาก {stats.total_games} เกม",
        )

        wr = hs.adjusted_win_rate(prior)
        s.components["winrate"] = Component(
            "winrate", "Win rate", wr, _scale(wr, 0.42, 0.58),
            f"{wr:.3f} จาก {hs.picks} เกม (ถ่วงตัวอย่างแล้ว)",
        )

        c_raw, c_detail = _counter_against(pooled, hid, theirs, prior)
        s.components["counter"] = Component(
            "counter", "Counter", c_raw, _scale(c_raw, -6.0, 6.0), c_detail
        )

        y_raw, y_detail = _synergy_with(pooled, hid, ours, prior)
        s.components["synergy"] = Component(
            "synergy", "Synergy", y_raw, _scale(y_raw, -6.0, 6.0), y_detail
        )

        s.total = sum(w[k] * c.scaled for k, c in s.components.items())
        s.reasons = _reasons(s, stats, hid, is_ban)
        out.append(s)

    out.sort(key=lambda x: x.total, reverse=True)
    return out[:limit]


def _counter_against(
    pooled: PooledStats, hero: str, enemies: list[str], prior: float
) -> tuple[float, str]:
    """ผลรวมความได้เปรียบของ hero เมื่อเจอฮีโร่ที่ศัตรูเลือกไปแล้ว"""
    if not enemies:
        return 0.0, "ศัตรูยังไม่ได้เลือก จึงยังคิด counter ไม่ได้"
    total = 0.0
    used = 0
    best: tuple[str, float] | None = None
    for e in enemies:
        m = pooled.matchups.get((hero, e))
        if m is None or m.games < MIN_PAIR_GAMES:
            continue
        sc = m.counter_score(prior)
        total += sc
        used += 1
        if best is None or sc > best[1]:
            best = (e, sc)
    if used == 0:
        return 0.0, f"ยังไม่มีคู่ที่ถึง {MIN_PAIR_GAMES} เกมกับตัวที่ศัตรูเลือก"
    detail = f"จาก {used}/{len(enemies)} คู่ที่มีข้อมูล"
    if best and best[1] > 0.5:
        detail += f" · เด่นเมื่อเจอ {best[0]} ({best[1]:+.1f})"
    return total, detail


def _synergy_with(
    pooled: PooledStats, hero: str, allies: list[str], prior: float
) -> tuple[float, str]:
    """ความเข้ากันกับฮีโร่ที่ทีมเดียวกันเลือกไปแล้ว

    ใช้ตาราง synergy ที่นับคู่ในทีมเดียวกัน ไม่ใช่ตาราง matchup

    ระวัง: ค่านี้ปนเปื้อนด้วย "ทีมเก่งเล่นคู่นี้บ่อย" ยังไม่ได้หักออก
    """
    if not allies:
        return 0.0, "ทีมยังไม่ได้เลือก จึงยังคิด synergy ไม่ได้"
    syn = pooled.synergies
    if not syn:
        return 0.0, "ยังไม่ได้คำนวณ synergy"
    total = 0.0
    used = 0
    for a in allies:
        key = (hero, a) if hero < a else (a, hero)
        m = syn.get(key)
        if m is None or m.games < MIN_PAIR_GAMES:
            continue
        total += m.counter_score(prior)
        used += 1
    if used == 0:
        return 0.0, f"ยังไม่มีคู่ที่ถึง {MIN_PAIR_GAMES} เกมกับตัวที่ทีมเลือก"
    return total, f"จาก {used}/{len(allies)} คู่ที่มีข้อมูล"


def _reasons(s: Suggestion, stats, hid: str, is_ban: bool) -> list[str]:
    out: list[str] = []
    hs = stats.get(hid)
    pres = stats.presence_rate(hid)
    if pres >= 0.5:
        out.append(f"อยู่ในเมตาหนัก presence {pres:.0%}")
    if hs.bans > hs.picks * 2 and hs.bans >= 20:
        out.append(f"ถูกแบนมากกว่าถูกเลือก {hs.bans} ต่อ {hs.picks} — ทีมอาชีพกลัวตัวนี้")
    if s.components["counter"].raw > 2.0:
        out.append("ได้เปรียบตัวที่ศัตรูเลือกไปแล้ว")
    if s.components["counter"].raw < -2.0:
        out.append("เสียเปรียบตัวที่ศัตรูเลือกไปแล้ว")
    if not s.reliable:
        out.append(f"ข้อมูลยังน้อย {hs.picks} เกม ตัวเลขยังไม่นิ่ง")
    if is_ban and pres >= 0.4:
        out.append("แบนแล้วตัดตัวเลือกหลักของศัตรูได้")
    return out


def report(sugs: list[Suggestion], state: DraftState, top: int = 8) -> str:
    turn = state.current
    if turn is None:
        return "draft จบแล้ว"
    verb = "แบน" if turn.action is DraftAction.BAN else "เลือก"
    lines = [
        f"── แนะนำให้{verb} ({state.team_name(turn.team_enum)}) ──",
        "",
        f"  {'#':<3}{'hero':<16}{'รวม':>7}{'meta':>7}{'wr':>7}{'ctr':>7}{'syn':>7}{'เกม':>6}",
    ]
    for i, s in enumerate(sugs[:top], 1):
        c = s.components
        mark = "" if s.reliable else " *"
        lines.append(
            f"  {i:<3}{s.hero_id:<16}{s.total:>7.1f}"
            f"{c['meta'].scaled:>7.0f}{c['winrate'].scaled:>7.0f}"
            f"{c['counter'].scaled:>7.0f}{c['synergy'].scaled:>7.0f}"
            f"{s.games:>6}{mark}"
        )
    if sugs:
        best = sugs[0]
        lines += ["", f"  อันดับ 1 · {best.hero_id}"]
        for r in best.reasons:
            lines.append(f"    · {r}")
        for c in best.components.values():
            lines.append(f"    {c.label:<10} {c.scaled:>5.0f}  {c.detail}")
    lines += ["", "  * = เล่นน้อยกว่า 15 เกม ตัวเลขยังไม่นิ่ง",
              "  คำแนะนำนี้มาจากสถิติล้วน ยังไม่ได้คิดเรื่อง composition และผู้เล่น"]
    return "\n".join(lines)
