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

from rov.domain.enums import DraftAction, LaneRole
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
    "trait_counter": 0.0, # Q4 — counter เชิงคุณภาพ (ยังไม่มีข้อมูล trait)
    "counter_evidence": 0.0,  # M1 — counter ที่มีกลไก เงื่อนไข และที่มา
    "synergy_evidence": 0.0,  # M2A — synergy ที่มีกลไก เงื่อนไข ผลที่คาด และที่มา
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


# สัดส่วนที่แบ่ง `rest` ระหว่าง meta กับ winrate — ต่างกันตามโจทย์
#
# pick ถาม "ตัวนี้เหมาะกับทีมเราแค่ไหน"
#     win rate ของตัวเองมีน้ำหนักมากกว่า เพราะเราจะเป็นคนเล่นมันเอง
#
# ban ถาม  "ตัวนี้อันตรายแค่ไหนถ้าปล่อยให้ศัตรูได้"
#     ซึ่งมีรูป BanPriority ~ P(ศัตรูได้) x Harm  โดย meta ประมาณ P
#     ที่เป็น **ตัวคูณ** ของทุกอย่าง ไม่ใช่ตัวบวก
#     ฮีโร่ที่แรงมากแต่ไม่มีใครแย่ง ไม่ใช่ตัวที่ควรเสียตาแบนไปกับมัน
#
# ดูที่มาเต็มใน docs/24-ban-intelligence-spec.md §4
PICK_META_SHARE = 0.45
BAN_META_SHARE = 0.75


def _split(rest: float, meta_share: float) -> dict[str, float]:
    return {"meta": rest * meta_share, "winrate": rest * (1.0 - meta_share)}


def ban_weights_for(n_enemy: int, n_ally: int) -> dict[str, float]:
    """น้ำหนักสำหรับ **ตาแบน** — คนละโจทย์กับตาเลือก

    ใช้กลไกการไหลของ counter/synergy ชุดเดียวกับ `weights_for()` ทุกประการ
    เพราะเหตุผลของมัน ("ยิ่งเปิดตัวยิ่งมีข้อมูลเฉพาะเกมนี้") ใช้ได้กับทั้งสองโจทย์
    ต่างกันแค่การแบ่งส่วนที่เหลือระหว่าง meta กับ win rate

    **ทำไม win rate ถึงมีน้ำหนักน้อยลงมากตอนแบน**

    win rate ระดับอาชีพเกาะ 50% โดยโครงสร้าง เพราะทุกเกมมีผู้ชนะหนึ่งฝ่าย
    ความต่างระหว่างตัวบนกับตัวล่างจึงแคบและไวต่อ noise โดยเฉพาะบนตัวอย่างเล็ก
    ตอนเลือก เรายอมรับ noise นั้นได้เพราะเรากำลังหา "ตัวที่ดีที่สุดสำหรับเรา"
    ตอนแบน สิ่งที่ต้องประมาณคือ "ศัตรูจะหยิบตัวไหน" ซึ่ง presence ตอบตรงกว่ามาก

    หลักฐานเชิงประจักษ์ (docs/22): baseline ที่ใช้ win rate ล้วนได้ top-1 0.007
    บนตาแบน ส่วน baseline ที่ใช้ presence ล้วนได้ 0.265

    ⚠️ ค่า 0.75/0.25 เป็นการตัดสินใจเชิงโครงสร้างที่ประกาศไว้ก่อนวัดผล
    ไม่ได้มาจากการไล่ลองค่าบน benchmark — ดู docs/24 §4
    """
    base = weights_for(n_enemy, n_ally)
    rest = base["meta"] + base["winrate"]
    return {**base, **_split(rest, BAN_META_SHARE)}


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

    # โจทย์ของตานี้ — "ban" กับ "pick" ใช้ฟังก์ชันเป้าหมายคนละตัว
    # เก็บไว้เพื่อให้ผู้ใช้และเทสต์ตรวจได้ว่าคะแนนที่เห็นมาจากโจทย์ไหน
    objective: str = "pick"

    # M1 — หลักฐาน counter ที่เข้ากับสถานการณ์นี้ (rov.draft.counterknowledge.Match)
    # เก็บเป็น record ไม่ใช่คะแนน เพื่อให้อธิบายได้ว่า counter เพราะอะไร
    counter_matches: list = field(default_factory=list)

    # M2A — หลักฐาน synergy ที่เข้ากับทีมนี้ (rov.draft.synergyknowledge.SynergyMatch)
    # เก็บเป็น record ไม่ใช่คะแนน เพื่อให้อธิบายได้ว่าเข้าคู่กันเพราะอะไร
    synergy_matches: list = field(default_factory=list)

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
    counter_book: object | None = None,
    synergy_book: object | None = None,
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

    ส่ง counter_book (rov.draft.counterknowledge.CounterBook) เข้ามาเพื่อเปิด
    component "counter_evidence" — counter ที่บอกกลไก เงื่อนไข ความเสี่ยง และที่มา
    ไม่ส่งมา = ไม่มี component นั้น · ส่งมาแต่ไม่มีความรู้เรื่องคู่นี้ก็ไม่มีเหมือนกัน
    เพราะ "ไม่รู้" ต้องไม่ถูกแปลงเป็นคะแนน 0 (docs/28 §2.3)

    ส่ง synergy_book (rov.draft.synergyknowledge.SynergyBook) เข้ามาเพื่อเปิด
    component "synergy_evidence" — synergy ที่บอกกลไก เงื่อนไข ผลที่คาด และที่มา
    หลักเดียวกับ counter_book: ไม่ส่ง = ไม่มี component · record ที่ alias ยังไม่ยืนยัน
    (status=unknown) จะถูกข้าม ไม่ถูกนำมาคิด (docs/33 §5 · docs/34 §6)

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
    # ★ จุดเดียวที่ ban กับ pick แยกทางกัน
    # ตา pick เดินเส้นทางเดิมทุกบรรทัด คะแนนจึงไม่เปลี่ยนแม้แต่หลักทศนิยม
    profile = ban_weights_for if is_ban else weights_for
    w = {**profile(len(theirs), len(ours)), **(weights or {})}
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
        s = Suggestion(
            hero_id=hid, total=0.0, games=hs.picks,
            objective="ban" if is_ban else "pick",
        )

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

        # Q5 — synergy ที่หักค่าที่คาดหวังออกแล้ว
        # ใช้ expected_synergy() ที่มีอยู่ใน stats.py มาตั้งแต่ต้น ไม่ได้เขียนใหม่
        ya_raw, ya_detail = _synergy_adjusted(pooled, hid, ours)
        s.components["synergy_adj"] = Component(
            "synergy_adj", "Synergy (adj)", ya_raw,
            _scale(ya_raw, -3.0, 3.0), ya_detail,
        )

        # Q4 — counter เชิงคุณภาพจาก trait
        # มี component เฉพาะเมื่อมี trait จริง ซึ่งตอนนี้ยังไม่มีสักตัว
        # ไม่ใส่ค่ากลางแทน เพราะ "ยังไม่รู้" กับ "ไม่ได้เปรียบไม่เสียเปรียบ" ต่างกัน
        if comp_ctx is not None:
            tc = _trait_counter_component(comp_ctx, hid, theirs)
            if tc is not None:
                t_raw, t_detail = tc
                s.components["trait_counter"] = Component(
                    "trait_counter", "Trait counter", t_raw,
                    _scale(t_raw, -2.0, 2.0), t_detail,
                )

        # M1 — counter ที่มีกลไกและที่มา
        #
        # ไม่ยุบเป็นเลขเดียวตั้งแต่ต้น — Component เก็บ raw ไว้ แต่ตัว match
        # ทั้งหมดถูกแนบไปกับ Suggestion เพื่อให้ report() อธิบายได้ครบ
        # ตาม docs/28 §8 (กลไก · เงื่อนไข · ความเสี่ยง · ที่มา · ข้อมูลเรา)
        if counter_book is not None:
            ce = _counter_evidence_component(
                counter_book, hid, theirs, ours, is_ban, state, lu.get(hid)
            )
            if ce is not None:
                ce_raw, ce_detail, matches = ce
                s.components["counter_evidence"] = Component(
                    "counter_evidence", "Counter evidence", ce_raw,
                    _scale(ce_raw, 0.0, 3.0), ce_detail,
                )
                s.counter_matches = matches

        # M2A — synergy ที่มีกลไกและที่มา
        #
        # หลักเดียวกับ counter_evidence: เก็บ raw ใน Component แต่ match ทั้งหมด
        # แนบไปกับ Suggestion เพื่อให้ report() กางกลไก · เงื่อนไข · ผลที่คาด · จุดอ่อน
        # · ที่มา · ข้อมูลเราได้ครบ (docs/34 §7)
        if synergy_book is not None:
            se = _synergy_evidence_component(
                synergy_book, hid, ours, is_ban, state
            )
            if se is not None:
                se_raw, se_detail, se_matches = se
                s.components["synergy_evidence"] = Component(
                    "synergy_evidence", "Synergy evidence", se_raw,
                    _scale(se_raw, 0.0, 3.0), se_detail,
                )
                s.synergy_matches = se_matches

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


# ------------------------------------------------------- M1 · counter evidence


# แปลงความมั่นใจเป็นน้ำหนักของหลักฐานหนึ่งชิ้น
#
# ⚠️ สามค่านี้ **ไม่ใช่** น้ำหนักที่มีผลต่ออันดับ — component ทั้งก้อนยังคูณ 0 อยู่
# มันมีไว้เรียงลำดับหลักฐานภายในเท่านั้น การเปิดน้ำหนักจริงไม่ใช่งานของ M1
_CONF_WEIGHT = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3}


def _counter_evidence_component(
    book,
    hero_id: str,
    theirs: list[str],
    ours: list[str],
    is_ban: bool,
    state,
    hero_lanes: dict[str, int] | None = None,
):
    """component ที่ตอบได้ว่า counter เพราะอะไร — ไม่ใช่แค่ว่า counter

    คืน None เมื่อ **ไม่รู้** ซึ่งเป็นสถานะปกติของฮีโร่ 95 จาก 119 ตัว
    ห้ามคืน 0.0 แทน เพราะ 0 แปลว่า "รู้แล้วว่าไม่ได้เปรียบ" ซึ่งคนละเรื่อง

    **pick กับ ban มองคนละฝั่งของกระดาน** (docs/28 §6)

        pick  ศัตรูเปิดอะไรมา แล้วตัวนี้แก้ได้ไหม      -> subject = ตัวที่ศัตรูเปิด
        ban   ถ้าเขาได้ตัวนี้ เขาจะกดอะไรของเราได้      -> subject = ตัวที่เราเปิด

    ตอนแบนเฟส 1 เรายังไม่ได้เปิดอะไรเลย ฝั่ง ban จึงว่างเปล่าเกือบทั้งหมด
    ซึ่งเป็นผลลัพธ์ที่ถูกต้อง ไม่ใช่บั๊ก
    """
    from rov.draft.counterknowledge import CounterContext, find_matches, summarize

    # เลนที่ฮีโร่นี้ลงบ่อยที่สุดจริงในข้อมูล — ใช้ตรวจเงื่อนไขของ lane counter
    # ใช้ข้อมูลแข่งจริง ไม่ใช่ lane_roles จากวิกิ ตามที่ docs/08 §6 สรุปไว้
    lane = None
    if hero_lanes:
        try:
            lane = LaneRole(max(hero_lanes, key=lambda k: hero_lanes[k]))
        except ValueError:
            lane = None

    # ban มองจากมุมศัตรู — `theirs`/`ours` ถูกสลับมาแล้วตอนต้น recommend()
    # ที่นี่จึงถามว่า "ถ้าฝ่ายตรงข้ามของ subject ได้ตัวนี้ จะกดใครได้"
    ctx = CounterContext(
        enemies=list(theirs),
        allies=list(ours),
        phase=state.current.phase if state.current else 1,
        objective="ban" if is_ban else "pick",
        candidate_lane=lane,
    )
    matches = [m for m in find_matches(book, hero_id, ctx) if m.counts]
    if not matches:
        return None

    summary = summarize(matches)
    raw = sum(_CONF_WEIGHT[m.confidence.value] for m in matches)

    parts = [f"{summary.direct} ตรงคู่"] if summary.direct else []
    if summary.mechanism:
        parts.append(f"{summary.mechanism} ผ่านกลไก")
    if summary.condition_unchecked:
        parts.append(f"{summary.condition_unchecked} เงื่อนไขยังตรวจให้ไม่ได้")
    top = max(matches, key=lambda m: _CONF_WEIGHT[m.confidence.value])
    detail = (
        " · ".join(parts)
        + f" · เด่นสุดเจอ {top.evidence.target} ({top.confidence.value})"
    )
    return raw, detail, matches


# ------------------------------------------------------- M2A · synergy evidence


def _synergy_evidence_component(book, hero_id: str, allies: list[str], is_ban: bool, state):
    """component ที่ตอบได้ว่าเข้าคู่กันเพราะอะไร — ไม่ใช่แค่ว่าเข้าคู่

    คืน None เมื่อ **ไม่รู้** ซึ่งเป็นสถานะปกติของฮีโร่เกือบทั้งหมด (คลังมีแค่ 7 คู่)
    ห้ามคืน 0.0 แทน เพราะ 0 แปลว่า "รู้แล้วว่าไม่เข้ากัน" ซึ่งคนละเรื่อง

    ใช้ `ours` เป็น allies เหมือน `_synergy_with()` — ตอนแบน `ours` ถูกสลับเป็น
    ฝั่งศัตรูมาแล้วตอนต้น recommend() จึงถามว่า "ตัวนี้เข้าคู่กับที่ศัตรูเปิดไปไหม"

    record ที่ alias ยังไม่ยืนยัน (status=unknown) ถูกกรองทิ้งใน find_matches แล้ว
    จึงไม่มีวันโผล่มาเป็นคะแนน (docs/33 §5)
    """
    from rov.draft.synergyknowledge import SynergyContext, find_matches, summarize

    ctx = SynergyContext(
        allies=list(allies),
        phase=state.current.phase if state.current else 1,
        objective="ban" if is_ban else "pick",
    )
    matches = [m for m in find_matches(book, hero_id, ctx) if m.counts]
    if not matches:
        return None

    summary = summarize(matches)
    raw = sum(_CONF_WEIGHT[m.confidence.value] for m in matches)

    parts = [f"{summary.direct} คู่เข้ากัน"]
    if summary.condition_unchecked:
        parts.append(f"{summary.condition_unchecked} เงื่อนไขยังตรวจให้ไม่ได้")
    top = max(matches, key=lambda m: _CONF_WEIGHT[m.confidence.value])
    detail = " · ".join(parts) + f" · เด่นสุดเข้าคู่ {top.ally} ({top.confidence.value})"
    return raw, detail, matches


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
    # Q3 — สี่มิติที่เพิ่งเข้ามา ทุกตัวเป็น "ยิ่งสูงยิ่งดี" เหมือนกัน
    "soft_cc", "poke", "sustain", "mobility",
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


# ------------------------------------------------- Q5 · synergy ที่หักค่าคาดหวัง


def _synergy_adjusted(
    pooled: PooledStats, hero: str, allies: list[str]
) -> tuple[float, str]:
    """synergy ที่หัก "ทีมเก่งเล่นคู่นี้บ่อย" ออกไปแล้ว

    ต่างจาก `_synergy_with()` ตรงตัวเทียบ ไม่ใช่ตรงสูตร
        _synergy_with      เทียบ win rate ของคู่กับ prior 0.5
                           คู่ที่ต่างคนต่างเก่งจะดูดีทั้งคู่ ทั้งที่อาจไม่เข้ากันเลย
        _synergy_adjusted  เทียบกับ expected_synergy() คือ win rate ที่ควรได้
                           ถ้าสองตัวไม่มีผลต่อกันเลย ส่วนต่างจึงคือ synergy จริง

    `expected_synergy()` อยู่ใน stats.py มาตั้งแต่ต้นแต่ไม่เคยถูกเรียก
    ตรงนี้เรียกของเดิม **ไม่ได้เขียนสูตรซ้ำ**

    ยังไม่สมบูรณ์ — docstring ของ expected_synergy() ยอมรับเองว่า
    ยังไม่ได้หักความแข็งของทีมออก แต่ดีกว่าใช้ค่าดิบมาก
    """
    from rov.draft.stats import SHRINKAGE_K, expected_synergy

    if not allies:
        return 0.0, "ทีมยังไม่ได้เลือก จึงยังคิด synergy ไม่ได้"
    syn = pooled.synergies
    if not syn:
        return 0.0, "ยังไม่ได้คำนวณ synergy"

    stats = pooled.stats
    total = 0.0
    used = 0
    for a in allies:
        key = (hero, a) if hero < a else (a, hero)
        m = syn.get(key)
        if m is None or m.games < MIN_PAIR_GAMES:
            continue
        exp = expected_synergy(stats, hero, a)
        # สูตรเดียวกับ counter_score ทุกประการ ต่างแค่ตัวเทียบเป็น exp ไม่ใช่ prior
        conf = m.games / (m.games + SHRINKAGE_K)
        total += (m.adjusted(exp) - exp) * 100.0 * conf
        used += 1
    if used == 0:
        return 0.0, f"ยังไม่มีคู่ที่ถึง {MIN_PAIR_GAMES} เกมกับตัวที่ทีมเลือก"
    total /= max(1, len(allies))
    return total, f"จาก {used}/{len(allies)} คู่ · หักค่าที่คาดหวังออกแล้ว"


# ---------------------------------------------------- Q4 · counter เชิงคุณภาพ


def _trait_counter_component(ctx, hero_id: str, enemies: list[str]):
    """ต่อ `composition.trait_counter()` เข้ากับ recommend

    คืน None เมื่อยังไม่รู้ ซึ่งตอนนี้คือทุกกรณี เพราะ trait ว่างทั้ง 119 ตัว
    """
    from rov.draft.composition import trait_counter

    hero_db, _team, _before = ctx
    hero = hero_db.get(hero_id)
    if hero is None:
        return None
    foes = [h for e in enemies if (h := hero_db.get(e)) is not None]
    if not foes:
        return None
    out = trait_counter(hero, foes)
    if out is None:
        return None
    score, used = out
    return score, f"จาก trait ของศัตรู {used} ตัว"


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
    is_ban = turn.action is DraftAction.BAN
    verb = "แบน" if is_ban else "เลือก"
    ratio = BAN_META_SHARE / (1 - BAN_META_SHARE)
    objective_line = (
        f"โจทย์: แบน — ให้น้ำหนัก meta ราว {ratio:.0f} เท่าของ win rate "
        "เพราะแบนคือการตัดตัวที่ศัตรูจะได้ ไม่ใช่การหาตัวที่เข้ากับทีมเรา"
        if is_ban
        else "โจทย์: เลือก — มองจากมุมทีมเรา ว่าตัวไหนเข้ากับสิ่งที่มีอยู่มากที่สุด"
    )
    lines = [
        f"── แนะนำให้{verb} ({state.team_name(turn.team_enum)}) ──",
        f"  {objective_line}",
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
        # M1 · STEP 5 — กางหลักฐาน counter ให้ครบทุกช่องที่ spec ขอ
        # กลไก · เงื่อนไข · ความเสี่ยง · ที่มา · ความมั่นใจ · ข้อมูลเราว่าอย่างไร
        if best.counter_matches:
            from rov.draft.counterknowledge import explain

            lines += ["", "  หลักฐาน counter"]
            for m in best.counter_matches:
                for row in explain(m, best.objective).splitlines():
                    lines.append(f"    {row}")
                lines.append("")
        # M2A · กางหลักฐาน synergy ให้ครบทุกช่องที่ spec ขอ
        # ชนิด · กลไก · เงื่อนไข · ผลที่คาด · จุดอ่อน · ที่มา · ความมั่นใจ · ข้อมูลเรา
        if best.synergy_matches:
            from rov.draft.synergyknowledge import explain as syn_explain

            lines += ["", "  หลักฐาน synergy"]
            for m in best.synergy_matches:
                for row in syn_explain(m, best.objective).splitlines():
                    lines.append(f"    {row}")
                lines.append("")
    lines += ["", "  * = เล่นน้อยกว่า 15 เกม ตัวเลขยังไม่นิ่ง",
              "  คำแนะนำนี้มาจากสถิติล้วน ยังไม่ได้คิดเรื่อง composition และผู้เล่น"]
    return "\n".join(lines)
