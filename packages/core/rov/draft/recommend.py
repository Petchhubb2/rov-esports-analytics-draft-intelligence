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
#
# ใช้เฉพาะตอนที่ยังไม่มีใครเปิดตัว ปกติ recommend() จะคำนวณน้ำหนักใหม่
# ตามจำนวนตัวที่เปิดมาแล้วด้วย weights_for() ดูเหตุผลที่นั่น
DEFAULT_WEIGHTS = {
    "meta": 0.39,
    "winrate": 0.48,
    "counter": 0.08,
    "synergy": 0.05,
}

# จำนวนเกมขั้นต่ำของคู่ ก่อนจะนำ matchup มาคิด
MIN_PAIR_GAMES = 8

# ─────────────────────────────────────────────────────────────────────
# น้ำหนักของ factor ที่เปิดใช้ใน PHASE B
#
# **ทุกตัวเริ่มที่ 0 โดยเจตนา** ไม่ใช่เพราะยังเขียนไม่เสร็จ
#
# เหตุผล: factor เหล่านี้คำนวณจากข้อมูลที่มีอยู่แล้วก็จริง แต่ยังไม่มีใคร
# วัดได้ว่ามันทำให้คำแนะนำดีขึ้นหรือแย่ลง การเปิดน้ำหนักโดยไม่วัดก่อน
# คือการเปลี่ยนคำแนะนำของผู้ใช้ด้วยการเดา ซึ่งแย่กว่าไม่เปลี่ยนเลย
#
# ค่าพวกนี้ยังถูกคำนวณและแสดงผลเสมอ ผู้ใช้จึงเห็นและตรวจได้ทันที
# แต่ยังไม่มีผลต่ออันดับ จนกว่า benchmark ใน PHASE I จะบอกว่าควรเปิดเท่าไร
#
# tests/unit/test_recommend_regression.py พิสูจน์ว่า "0 แปลว่าไม่เปลี่ยนจริง"
EXTRA_WEIGHTS: dict[str, float] = {
    "composition": 0.0,   # Q1 — คอมพ์ดีขึ้นแค่ไหนถ้าได้ตัวนี้
    "lane_counter": 0.0,  # Q2 — matchup เฉพาะคู่ที่ประกบกันในเลนเดียวกัน
    "synergy_adj": 0.0,   # Q5 — synergy ที่หัก "ทีมเก่งเล่นคู่นี้บ่อย" ออกแล้ว
}

# ฮีโร่ที่ตำแหน่งเต็มแล้วยังได้คะแนนเท่านี้ของเดิม
# ไม่ตัดเป็นศูนย์ เพราะข้อมูลเลนอาจไม่ครบ และตัวเฟลกอาจไปลงเลนอื่นได้
ROLE_FLOOR = 0.35

# ฮีโร่จะ "ปิด" เลนได้ต่อเมื่อลงเลนนั้น **มากกว่าครึ่ง** ของครั้งที่ถูกเลือก
# ใช้มากกว่าไม่ใช่มากกว่าเท่ากับ เพราะตัวที่เล่นสองเลน 50/50 เราไม่รู้ว่ามันจะลงเลนไหน
# ถือว่ายังไม่ปิดทั้งคู่ปลอดภัยกว่า จะได้ยังพิจารณาแบนและเลือกทั้งสองเลนต่อ
LANE_OWN_SHARE = 0.5


def _main_lane(usage: dict[str, int] | None) -> tuple[str, float] | None:
    if not usage:
        return None
    total = sum(usage.values())
    if not total:
        return None
    lane = max(usage, key=lambda k: usage[k])
    return lane, usage[lane] / total


def needed_lanes(
    picks: list[str], lane_usage: dict[str, dict[str, int]], lanes: list[str]
) -> set[str]:
    """เลนที่ทีมนั้นยังไม่มีตัวหลักลง"""
    filled = set()
    for hid in picks:
        m = _main_lane(lane_usage.get(hid))
        if m and m[1] > LANE_OWN_SHARE:
            filled.add(m[0])
    return {ln for ln in lanes if ln not in filled}


def role_fit(
    hero: str, need: set[str], lane_usage: dict[str, dict[str, int]], lanes: list[str]
) -> float:
    """สัดส่วนการเล่นของฮีโร่ที่ตกอยู่ในเลนที่ฝ่ายนั้นยังต้องการ

    แก้ปัญหา "แบนเมจทั้งที่เขามีเมจแล้ว" — ถ้าอีกฝั่งเปิดเมจ โรม แครี่ ไปครบ
    เหลือแต่ป่ากับออฟ การแบนเมจอีกตัวคือแบนทิ้งเปล่า เขาไม่มีช่องจะใส่แล้ว
    เรื่องเดียวกันตอนเลือก — ไม่ควรหยิบเมจตัวที่สองมาทับตำแหน่งเดิม

    คืน 1.0 เมื่อไม่มีข้อมูลเลน หรือยังต้องการทุกเลน (ต้นดราฟต์)
    """
    usage = lane_usage.get(hero)
    if not usage or not need or len(need) == len(lanes):
        return 1.0
    total = sum(usage.values())
    if not total:
        return 1.0
    return sum(usage.get(ln, 0) for ln in need) / total


def weights_for(n_enemy: int, n_ally: int) -> dict[str, float]:
    """น้ำหนักที่ขยับตามว่ารู้บริบทของเกมนี้มากแค่ไหน

    ปัญหาของน้ำหนักคงที่ (meta .30 / wr .30 / counter .25 / synergy .15)
    คือต้นดราฟต์ยังไม่มีใครเปิดตัว counter กับ synergy ไม่มีข้อมูลเลย
    ได้ค่ากลางไปทั้งคู่ คะแนนรวมจึงเหลือแต่ meta กับ win rate
    ซึ่งเป็นค่าเฉลี่ยข้ามทุกเกม ผลคือมันเชียร์ตัว win rate สูงเหมือนกันทุกครั้ง
    ไม่ว่าอีกฝั่งจะเปิดอะไรมา

    พอฝั่งตรงข้ามเปิดตัวแล้ว เรามีข้อมูลเฉพาะเกมนี้ ซึ่งควรเชื่อมากกว่า
    ค่าเฉลี่ยรวม น้ำหนักจึงไหลจาก meta/winrate ไปทาง counter/synergy

    ไต่แบบอิ่มตัว ไม่ใช่เส้นตรง เพราะตัวแรกที่เปิดมาให้ข้อมูลเยอะที่สุด
    ตัวที่ห้าเพิ่มอีกไม่มากแล้ว

    ปลอดภัยที่จะให้น้ำหนักสูง เพราะ counter_score ถ่วงด้วยขนาดตัวอย่างมาแล้ว
    คู่ที่ข้อมูลน้อยจะได้ค่าใกล้ศูนย์เอง การเพิ่มน้ำหนักจึงไม่ขยาย noise
    """
    e = n_enemy / (n_enemy + 1.2)
    a = n_ally / (n_ally + 1.2)
    counter = 0.08 + 0.40 * e
    synergy = 0.05 + 0.25 * a
    rest = 1.0 - counter - synergy
    return {
        "meta": rest * 0.45,
        "winrate": rest * 0.55,
        "counter": counter,
        "synergy": synergy,
    }


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
    # 1.0 = ตรงกับตำแหน่งที่ฝ่ายนั้นยังต้องการเต็ม ๆ · 0.0 = ตำแหน่งเต็มแล้ว
    role_fit: float = 1.0

    # Q1 — มิติที่ตัวนี้ช่วยยกขึ้น/กดลง เทียบกับคอมพ์ก่อนหยิบมัน
    # (มิติ, ส่วนต่าง) เช่น ("frontline", +18.4)
    # ว่างทั้งคู่ = ยังคำนวณไม่ได้ (attribute ไม่ครบ) ไม่ใช่แปลว่าไม่มีผล
    fills_gaps: list[tuple[str, float]] = field(default_factory=list)
    creates_gaps: list[tuple[str, float]] = field(default_factory=list)

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
    lane_usage: dict[str, dict[str, int]] | None = None,
    lanes: list[str] | None = None,
    hero_db: object | None = None,
    lane_matchups: dict | None = None,
    extra_weights: dict[str, float] | None = None,
) -> list[Suggestion]:
    """จัดอันดับฮีโร่ที่ควรเลือกหรือแบนในตาปัจจุบัน

    ส่ง lane_usage เข้ามาด้วยเพื่อให้คิดเรื่องตำแหน่งที่ยังว่างได้
    (ได้จาก rov.draft.lanes.lane_usage) ถ้าไม่ส่งมาจะข้ามการคิดส่วนนี้ไป

    ส่ง hero_db (rov.draft.heroes.HeroDB) เข้ามาเพื่อเปิด component
    "composition" ถ้าไม่ส่ง component นั้นจะไม่มีเลย — ไม่ใช่ค่า  50 แทน
    เพราะ "ไม่รู้" กับ "กลาง ๆ" ไม่เหมือนกัน

    ส่ง lane_matchups (rov.draft.lanes.compute_lane_matchups) เข้ามาเพื่อเปิด
    component "lane_counter" — counter ที่นับเฉพาะคู่ที่ประกบกันในเลนเดียวกันจริง
    ต้องส่ง lane_usage มาด้วย ไม่งั้นไม่รู้ว่าใครประกบกับใคร

    extra_weights ทับ EXTRA_WEIGHTS ได้ ใช้ตอนทดสอบว่าเปิดน้ำหนักแล้วอันดับเปลี่ยนจริง
    ห้ามใช้เปลี่ยนน้ำหนักจริงจนกว่า benchmark ใน PHASE I จะบอกว่าควรเท่าไร
    """
    turn = state.current
    if turn is None:
        return []

    stats = pooled.stats
    prior = stats.baseline_win_rate
    team = turn.team_enum
    is_ban = turn.action is DraftAction.BAN

    # ตอนแบน ให้มองจากมุมของศัตรู — เราอยากตัดตัวที่ดีต่อ "เขา"
    subject = team.opponent if is_ban else team
    ours = state.picks(subject)
    theirs = state.picks(subject.opponent)

    lu = lane_usage or {}
    ln_all = lanes or sorted({
        lane for u in lu.values() for lane in u
    })
    # ตอนแบนมองจากมุมศัตรู ตำแหน่งที่ต้องดูจึงเป็นตำแหน่งที่ "เขา" ยังไม่เปิด
    need = needed_lanes(ours, lu, ln_all) if lu and ln_all else set()

    # น้ำหนักขึ้นกับว่าเปิดตัวกันไปแล้วกี่ตัว
    # ถ้าผู้เรียกส่ง weights มาเอง ให้ทับลงบนค่าที่คำนวณได้
    # ส่งมาบางคีย์ก็ได้ ที่เหลือใช้ค่าไดนามิก
    w = {**weights_for(len(theirs), len(ours)), **(weights or {})}
    # factor ที่เปิดใช้ใน PHASE B รวมเข้ามาโดยมีค่าเริ่มต้นเป็น 0
    w_all = {**w, **EXTRA_WEIGHTS, **(extra_weights or {})}

    # บริบทของ composition — เตรียมครั้งเดียวนอกลูป ไม่ใช่ต่อ candidate
    # เพราะ dimension ของทีมก่อนหยิบ เป็นค่าเดียวกันสำหรับทุก candidate
    comp_ctx = _composition_context(hero_db, ours)

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
            "counter", "Counter", c_raw, _scale(c_raw, -3.0, 3.0), c_detail
        )

        y_raw, y_detail = _synergy_with(pooled, hid, ours, prior)
        s.components["synergy"] = Component(
            "synergy", "Synergy", y_raw, _scale(y_raw, -3.0, 3.0), y_detail
        )

        # Q2 — counter ที่นับเฉพาะคู่ที่ประกบกันในเลนเดียวกัน
        # เป็น component แยก ไม่ได้ไปแก้ counter เดิม เพราะสองตัวตอบคนละคำถาม
        # การกลืนเข้าด้วยกันจะทำให้ semantics เดิมหายไปโดยไม่มีใครสังเกต
        if lane_matchups and lu:
            lc_raw, lc_detail = _lane_counter_against(
                lane_matchups, lu, hid, theirs, prior
            )
            s.components["lane_counter"] = Component(
                "lane_counter", "Lane counter", lc_raw,
                _scale(lc_raw, -3.0, 3.0), lc_detail,
            )

        # Q1 — composition ดีขึ้นแค่ไหนถ้าได้ตัวนี้
        # มีเฉพาะเมื่อส่ง hero_db มา และ attribute ของทุกตัวครบ
        if comp_ctx is not None:
            cf = _composition_fit(comp_ctx, hid)
            if cf is not None:
                raw, fills, creates, detail = cf
                s.components["composition"] = Component(
                    "composition", "Composition", raw, _scale(raw, -12.0, 12.0), detail
                )
                s.fills_gaps = fills
                s.creates_gaps = creates

        # น้ำหนักของ factor ใหม่เป็น 0 สูตรจึงให้ผลเท่าเดิมเป๊ะ
        # ใช้ .get(k, 0.0) แทน w[k] เพราะ components มีคีย์ที่ w ไม่รู้จักแล้ว
        base = sum(w_all.get(k, 0.0) * c.scaled for k, c in s.components.items())
        fit = role_fit(hid, need, lu, ln_all) if need else 1.0
        s.role_fit = fit
        s.total = base * (ROLE_FLOOR + (1.0 - ROLE_FLOOR) * fit)
        s.reasons = _reasons(s, stats, hid, is_ban)
        out.append(s)

    out.sort(key=lambda x: x.total, reverse=True)
    return out[:limit]


# ---------------------------------------------------------------- Q2 · lane counter


# คู่ในเลนเดียวกันมีตัวอย่างน้อยกว่า context=TEAM มาก เพราะจับเฉพาะคู่ที่
# ประกบกันจริง ไม่ใช่ทุกคู่ข้ามทีม เกณฑ์จึงต่ำกว่า MIN_PAIR_GAMES
# ค่านี้ตรงกับ lanes.MIN_LANE_PAIR_GAMES ที่ใช้ตอน export อยู่แล้ว
MIN_LANE_PAIR = 3

# ฮีโร่จะถือว่า "ลงเลนนี้" เมื่อลงเลนนั้นเกินสัดส่วนนี้ของครั้งที่ถูกเลือก
# ใช้เกณฑ์ต่ำกว่า LANE_OWN_SHARE (0.5) เพราะคำถามต่างกัน
#   LANE_OWN_SHARE ถาม "ตัวนี้ปิดเลนนั้นให้ทีมหรือยัง" — ต้องมั่นใจสูง
#   ตรงนี้ถาม     "ตัวนี้มีโอกาสไปประกบใครในเลนนั้นไหม" — เอาพอมีเหตุผล
LANE_PLAY_SHARE = 0.30


def _lanes_played(usage: dict[str, int] | None) -> list[str]:
    """เลนที่ฮีโร่ตัวนี้ลงบ่อยพอจะนับ — เรียงจากบ่อยสุด"""
    if not usage:
        return []
    total = sum(usage.values())
    if not total:
        return []
    return [
        ln
        for ln, n in sorted(usage.items(), key=lambda kv: -kv[1])
        if n / total >= LANE_PLAY_SHARE
    ]


def _lane_counter_against(
    lane_matchups: dict,
    lane_usage: dict[str, dict[str, int]],
    hero: str,
    enemies: list[str],
    prior: float,
) -> tuple[float, str]:
    """ความได้เปรียบเมื่อ **ประกบกันในเลนเดียวกันจริง**

    ต่างจาก `_counter_against()` ตรงบริบท ไม่ใช่ตรงสูตร
        _counter_against      คู่ที่อยู่คนละทีมในเกมเดียวกัน (context=TEAM)
                              ตัวอย่างเยอะแต่ปนคู่ที่ไม่เคยเจอหน้ากันเลย
        _lane_counter_against คู่ที่ยืนเลนเดียวกัน (context=LANE)
                              ตัวอย่างน้อยกว่ามาก แต่ตรงคำถาม "ชนเลนแล้วใครชนะ"

    เฉลี่ยต่อจำนวนศัตรูที่เปิดมาทั้งหมด ไม่ใช่ต่อคู่ที่มีข้อมูล —
    หลักเดียวกับ `_counter_against()` เพื่อให้คู่ที่ไม่รู้ถ่วงลงหาศูนย์เอง
    """
    if not enemies:
        return 0.0, "ศัตรูยังไม่ได้เลือก จึงยังคิดการชนเลนไม่ได้"
    if not lane_matchups or not lane_usage:
        return 0.0, "ยังไม่มีข้อมูล matchup แยกเลน"

    my_lanes = set(_lanes_played(lane_usage.get(hero)))
    if not my_lanes:
        return 0.0, "ไม่รู้ว่าฮีโร่ตัวนี้ลงเลนไหน"

    total = 0.0
    used = 0
    best: tuple[str, str, float] | None = None
    for e in enemies:
        shared = my_lanes & set(_lanes_played(lane_usage.get(e)))
        if not shared:
            continue
        # ถ้าเจอกันได้หลายเลน เอาเลนที่มีข้อมูลมากที่สุดเป็นตัวแทน
        rows = [
            (ln, lane_matchups.get((ln, hero, e)))
            for ln in sorted(shared)
        ]
        rows = [(ln, m) for ln, m in rows if m is not None and m.games >= MIN_LANE_PAIR]
        if not rows:
            continue
        ln, m = max(rows, key=lambda r: r[1].games)
        sc = m.counter_score(prior)
        total += sc
        used += 1
        if best is None or sc > best[2]:
            best = (e, ln, sc)

    if used == 0:
        return 0.0, f"ยังไม่มีคู่ที่ประกบกันในเลนถึง {MIN_LANE_PAIR} เกม"
    total /= max(1, len(enemies))
    detail = f"จาก {used}/{len(enemies)} คู่ที่ประกบกันจริง"
    if best and best[2] > 0.5:
        detail += f" · เด่นเมื่อชน {best[0]} ที่เลน {best[1]} ({best[2]:+.1f})"
    return total, detail


# ---------------------------------------------------------------- Q1 · composition


# มิติที่ถือว่า "ยิ่งสูงยิ่งดี" ทั้งหมด — ใช้วัดว่าหยิบตัวนี้แล้วคอมพ์ขยับไปทางไหน
# ไม่รวม damage_mix เพราะมันเป็นความสมดุล ไม่ใช่ยิ่งมากยิ่งดี
# และไม่รวม role_balance เพราะ role_fit จัดการเรื่องตำแหน่งอยู่แล้ว
# การนับซ้ำจะทำให้เรื่องตำแหน่งมีน้ำหนักเกินจริง
_FIT_DIMS = (
    "frontline", "engage", "disengage", "peel",
    "objective", "crowd_control", "waveclear", "split_push",
)

# ส่วนต่างที่ถือว่ามีนัย ต่ำกว่านี้คือความผันผวนปกติ ไม่ต้องรายงาน
_GAP_DELTA = 5.0


def _composition_context(hero_db: object | None, ours: list[str]):
    """เตรียมข้อมูลที่ทุก candidate ใช้ร่วมกัน — คืน None ถ้าคิดไม่ได้

    คืน None เมื่อ (ก) ไม่ได้ส่ง hero_db มา (ข) ทีมเรามีตัวที่ attribute ไม่ครบ
    ทั้งสองกรณีคือ "ยังไม่รู้" ซึ่งต้องไม่มี component ออกไปเลย
    ไม่ใช่ใส่ค่ากลางแล้วทำเหมือนรู้
    """
    if hero_db is None:
        return None
    from rov.draft.composition import partial_dimensions

    try:
        team = [hero_db.require(h) for h in ours]
    except KeyError:
        return None
    before = partial_dimensions(team)
    if before is None:
        return None
    return hero_db, team, before


def _composition_fit(ctx, hero_id: str):
    """คอมพ์ขยับไปทางไหนถ้าเพิ่มฮีโร่ตัวนี้เข้าไป

    คืน (raw, fills_gaps, creates_gaps, detail) หรือ None ถ้าฮีโร่ตัวนี้
    ยังไม่ได้กรอก attribute

    **raw ถ่วงด้วยความต้องการ** — การยก frontline จาก 10 เป็น 40 มีค่ากว่า
    การยกจาก 80 เป็น 95 มาก เพราะทีมที่ frontline 80 แล้วไม่ได้ขาดมันอีก
    ใช้ (100 - ค่าเดิม)/100 เป็นตัวถ่วง ซึ่งเป็นหลักเดียวกับที่
    `_saturating_sum` ใช้กับ CC คือผลตอบแทนลดลงเมื่อมีมากแล้ว
    """
    from rov.draft.composition import partial_dimensions

    hero_db, team, before = ctx
    hero = hero_db.get(hero_id)
    if hero is None or not hero.complete:
        return None
    after = partial_dimensions([*team, hero])
    if after is None:
        return None

    raw = 0.0
    fills: list[tuple[str, float]] = []
    creates: list[tuple[str, float]] = []
    for dim in _FIT_DIMS:
        delta = after[dim] - before[dim]
        raw += delta * (100.0 - before[dim]) / 100.0
        if delta >= _GAP_DELTA:
            fills.append((dim, round(delta, 1)))
        elif delta <= -_GAP_DELTA:
            creates.append((dim, round(delta, 1)))
    raw /= len(_FIT_DIMS)

    fills.sort(key=lambda x: -x[1])
    creates.sort(key=lambda x: x[1])
    if fills:
        detail = "ยก " + ", ".join(f"{k} {v:+.0f}" for k, v in fills[:3])
    elif creates:
        detail = "กด " + ", ".join(f"{k} {v:+.0f}" for k, v in creates[:3])
    else:
        detail = "ไม่เปลี่ยนมิติไหนเกิน 5 แต้ม"
    return raw, fills, creates, detail


def _counter_against(
    pooled: PooledStats, hero: str, enemies: list[str], prior: float
) -> tuple[float, str]:
    """ความได้เปรียบเฉลี่ยของ hero เมื่อเจอฮีโร่ที่ศัตรูเลือกไปแล้ว

    เฉลี่ยต่อ "ตัวที่ศัตรูเปิดมา" ไม่ใช่ต่อคู่ที่มีข้อมูล คู่ที่ไม่มีข้อมูล
    จึงถ่วงค่าลงมาหาศูนย์เอง

    เดิมใช้ผลรวม ซึ่งปนสองเรื่องเข้าด้วยกัน — ความแรงของผล กับจำนวนที่รู้
    ทำให้ต้นดราฟต์สัญญาณจางเกินจริง ตอนนี้แยกกัน ค่านี้บอกความแรง
    ส่วนจำนวนที่รู้ไปอยู่ที่น้ำหนักใน weights_for()
    """
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
    total /= max(1, len(enemies))
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
    total /= max(1, len(allies))
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
