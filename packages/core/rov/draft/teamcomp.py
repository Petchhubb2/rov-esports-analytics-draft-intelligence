"""คอมพ์ของแต่ละทีม — ทีมนี้ "ชอบจัดทีมทรงไหน"

**อ่านก่อนใช้: คำถาม "ทีมเล่นคอมพ์อะไรเยอะสุด" ข้อมูลตอบไม่ได้**

วัดจาก 861 เกมจริงแล้วพบว่าทีมอาชีพ **แทบไม่เล่นชุด 5 ตัวซ้ำเลย**

    bru   164 คอมพ์ -> ชุด 5 ตัวไม่ซ้ำกัน 162 แบบ  ซ้ำมากสุด 2 ครั้ง
    bac   157 คอมพ์ -> 156 แบบ                      ซ้ำมากสุด 2 ครั้ง
    fs    148 คอมพ์ -> 148 แบบ                      ไม่ซ้ำเลยสักครั้ง

สาเหตุหลักคือกติกา Global Ban-Pick — ในซีรีส์เดียวทีมใช้ฮีโร่ซ้ำไม่ได้
(docs/08 §7) การจัดชุดเดิมจึงเป็นไปไม่ได้โดยโครงสร้าง ไม่ใช่เพราะทีมไม่อยาก

ดังนั้นหน้าไหนที่เขียนว่า "คอมพ์ที่ทีมนี้เล่นบ่อยสุด: 5 ตัวนี้ 2 ครั้ง"
คือการเอา noise มาแสดงเป็น pattern — โมดูลนี้จึงไม่ทำแบบนั้น

**สิ่งที่ตอบได้จริง คือรูปทรง ไม่ใช่ตัวบุคคล**

ทีมไม่ได้เล่นชุดเดิม แต่เล่น **ทรงเดิม** ซึ่งวัดได้และต่างกันอย่างมีนัย

    ank        อัสแซสซิน 2+  55.4%  เทียบลีก 37.8%
    tenacity   แทงค์ 2+      31.2%  เทียบลีก 21.8%
    fs         ไม่มีแทงค์    24.1%  เทียบลีก 16.3%
    bmg        เมจ 2+        33.3%  เทียบลีก 19.8%

**ทำไมใช้ hero_class ไม่ใช่ Composition Engine**

`composition.analyze()` ให้ภาพที่ละเอียดกว่ามาก (engage, peel, cc, poke ...)
แต่ต้องการ attribute ครบทั้ง 5 ตัว ซึ่งกรอกไปแล้ว 30/119 ตัว
ผลคือมันวิเคราะห์คอมพ์จริงได้ **183/1722 = 10.6%** เท่านั้น

และ 183 คอมพ์นั้นไม่ใช่ตัวอย่างสุ่ม — มันคือคอมพ์ที่บังเอิญประกอบด้วย
ฮีโร่ยอดนิยมล้วน (เพราะ 30 ตัวที่กรอกถูกเลือกตามความถี่การใช้งาน)
การสรุปนิสัยทีมจากสไลซ์ที่เอียงแบบนั้นจะผิดอย่างเป็นระบบ

`hero_class` มาจาก Liquipedia ตรง ๆ (filled_kind = derived) ครอบคลุม 117/119 ตัว
คิดเป็น **92.9% ของคอมพ์จริง** จึงเป็นฐานเดียวที่ยืนได้ในตอนนี้

ถ้าวันไหนกรอก attribute ครบ ค่อยเพิ่มชั้นที่ละเอียดกว่านี้ทับลงไป
"""

from __future__ import annotations

import itertools
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from rov.draft.heroes import HeroDB
from rov.draft.importer.parser import SeriesDraft
from rov.draft.scouting import parse_date

# ไม่คัดลอกสูตร Wilson มาไว้ที่นี่ — โปรเจกต์นี้ถือหลัก "สูตรเดียวอยู่ที่เดียว"
# (ดู PHASE B Q6) rankmetrics ไม่ import อะไรจาก rov.draft จึงไม่เกิดวงจร
from rov.eval.rankmetrics import wilson_interval

TEAM_SIZE = 5

# ทีมต้องมีคอมพ์อย่างน้อยเท่านี้จึงจะพูดถึงนิสัยของมันได้
# ต่ำกว่านี้ช่วงความเชื่อมั่นกว้างจนทุกอย่างคลุมค่าลีก แสดงไปก็ไม่ได้ข้อมูล
MIN_COMPS = 40

# จำนวนรอบสับไพ่สำหรับทดสอบว่าคู่ที่เห็นเกินความบังเอิญหรือไม่
SHUFFLE_ROUNDS = 400
SHUFFLE_SEED = 20260911  # ตรึงไว้ให้ผลซ้ำได้ ไม่ใช่ค่าที่เลือกเพราะให้ผลสวย


@dataclass(frozen=True)
class ShapeRule:
    """รูปทรงหนึ่งแบบ — นับจาก hero_class ล้วน ไม่ใช้ attribute ที่ต้องประเมิน"""

    key: str
    label: str
    hero_class: str
    at_least: int | None = None   # มีอย่างน้อยกี่ตัว
    at_most: int | None = None    # มีไม่เกินกี่ตัว
    why: str = ""

    def holds(self, counts: Counter[str]) -> bool:
        n = counts[self.hero_class]
        if self.at_least is not None and n < self.at_least:
            return False
        if self.at_most is not None and n > self.at_most:
            return False
        return True


# รูปทรงที่เลือกมาวัด — ทั้งหมดเป็นทรงที่ผู้เล่นระดับสูงเรียกชื่อได้อยู่แล้ว
# และทั้งหมดตอบได้ด้วย hero_class เพียงอย่างเดียว
#
# ⚠️ ชุดนี้ประกาศไว้ก่อนดูผลรายทีม ไม่ได้เลือกทีหลังเพราะทีมไหนโดดเด่น
SHAPES: tuple[ShapeRule, ...] = (
    ShapeRule(
        "no_tank", "ไม่มีแทงค์", "tank", at_most=0,
        why="ไม่มีใครยืนหน้า แลกกับดาเมจหรือความเร็ว — แพ้ทางคอมพ์ที่บุกเข้ามาตรง ๆ",
    ),
    ShapeRule(
        "two_tank", "แทงค์ 2+", "tank", at_least=2,
        why="ยืนหน้าสองคน เล่นยาวและกินพื้นที่ objective ได้ แต่ดาเมจรวมต่ำลง",
    ),
    ShapeRule(
        "two_mage", "เมจ 2+", "mage", at_least=2,
        why="ดาเมจเวทหนัก ฝั่งตรงข้ามต้องออกไอเทมต้านเวทเร็วกว่าปกติ",
    ),
    ShapeRule(
        "two_assassin", "อัสแซสซิน 2+", "assassin", at_least=2,
        why="เน้นจับคนหลุด จบไว ต้องการการมองแมพที่ดีกว่าจะรับมือ",
    ),
    ShapeRule(
        "no_marksman", "ไม่มีมาร์คแมน", "marksman", at_most=0,
        why="ทิ้งดาเมจต่อเนื่องช่วงท้าย เดิมพันว่าเกมจะจบก่อน",
    ),
    ShapeRule(
        "two_support", "ซัพ 2+", "support", at_least=2,
        why="เพิ่มการป้องกันและคอนโทรล มักคู่กับแผนเล่นรวมกลุ่มแต่เนิ่น ๆ",
    ),
)


# ─────────────────────────────────────────────────────── หน่วยข้อมูลดิบ


@dataclass(frozen=True)
class Comp:
    """คอมพ์หนึ่งชุดของทีมหนึ่งในเกมหนึ่ง

    `heroes` เรียงตาม **ช่อง roster ของ Liquipedia** ซึ่งพิสูจน์แล้วว่าเรียงตามเลน
    (ds · jungle · mid · dragon · support — ดู `lanes.SLOT_LANES`)
    **ไม่ใช่ลำดับการเลือก** จึงห้ามตีความว่า heroes[0] คือตัวที่หยิบก่อน
    """

    team: str
    heroes: tuple[str, ...]
    won: bool
    blue: bool
    # ISO `2026-05-09` ไม่ใช่ wikitext ดิบ — เก็บแบบเรียงได้ตั้งแต่ต้นทาง
    # ถ้าเก็บดิบ ("September 7, 2025 - 18:00 {{Abbr/ICT}}") การเรียงจะกลาย
    # เป็นเรียงตามตัวอักษร แล้ว "September" จะมาก่อน "May" โดยไม่มีใครเห็น
    date: str | None = None
    opponent: str | None = None
    bans: tuple[str, ...] = ()

    @property
    def key(self) -> frozenset[str]:
        return frozenset(self.heroes)


@dataclass
class RepeatStats:
    """ทีมนี้เล่นชุดเดิมซ้ำแค่ไหน — คำตอบมักคือ 'แทบไม่ซ้ำ'"""

    total: int = 0
    distinct: int = 0
    max_repeat: int = 0
    repeated_sets: int = 0        # ชุดที่โผล่มากกว่า 1 ครั้ง

    @property
    def distinct_share(self) -> float:
        return self.distinct / self.total if self.total else 0.0

    @property
    def verdict(self) -> str:
        if not self.total:
            return "ไม่มีข้อมูล"
        if self.max_repeat <= 2:
            return "ไม่เล่นชุดเดิมซ้ำ"
        if self.max_repeat <= 4:
            return "ซ้ำบ้างแต่ไม่พอเรียกว่าสูตรประจำ"
        return "มีชุดที่ใช้ซ้ำจริง"


@dataclass
class ShapeRate:
    """อัตราที่ทีมนี้จัดทรงนี้ เทียบกับลีก"""

    rule: ShapeRule
    hits: int = 0
    n: int = 0
    wins: int = 0
    league_rate: float = 0.0
    lo: float = 0.0
    hi: float = 0.0

    @property
    def rate(self) -> float:
        return self.hits / self.n if self.n else 0.0

    @property
    def win_rate(self) -> float | None:
        """ดิบ ไม่ถ่วงตัวอย่าง — ใช้แสดงเท่านั้น ห้ามใช้จัดอันดับ (docs/01 G8)"""
        return self.wins / self.hits if self.hits else None

    @property
    def diff(self) -> float:
        return self.rate - self.league_rate

    @property
    def notable(self) -> bool:
        """ช่วงความเชื่อมั่นไม่คร่อมค่าลีก = ต่างจริง ไม่ใช่ความผันผวน

        ใช้การที่ช่วงไม่คร่อมค่าลีก ซึ่งเข้มกว่าการทดสอบสองสัดส่วนตามปกติ
        จึงอนุรักษ์นิยม — ประกาศว่า "ต่าง" ยากกว่าที่ควร ดีกว่าประกาศง่ายเกิน
        """
        return self.n >= MIN_COMPS and (self.lo > self.league_rate or self.hi < self.league_rate)

    @property
    def direction(self) -> str:
        return "มากกว่าลีก" if self.diff > 0 else "น้อยกว่าลีก"


@dataclass
class PairBond:
    """คู่ที่ทีมนี้จับมาด้วยกันบ่อยกว่าที่ความบังเอิญอธิบายได้"""

    a: str
    b: str
    together: int
    expected: float
    wins: int

    @property
    def lift(self) -> float:
        return self.together / self.expected if self.expected else 0.0

    @property
    def win_rate(self) -> float | None:
        return self.wins / self.together if self.together else None


@dataclass
class BanSlot:
    """ทีมนี้แบนอะไรที่ตาแบนที่ n

    **ช่อง `t1b1..t1b4` ของ Liquipedia เรียงตามลำดับการแบนจริง**

    ต่างจากช่อง pick ที่เรียงตาม roster (ดู `lanes.py`) — ยืนยันจากข้อมูล
    1,722 ทีมด้วยหลักฐานสามทางที่ชี้ไปทางเดียวกัน

        ช่อง   ตัวที่ต่างกัน  3 ตัวแรกกิน  entropy   presence เฉลี่ย
        b1        45           49.0%      3.95      0.621
        b2        56           30.0%      4.70      0.527
        b3        79           24.6%      5.39      0.379
        b4        84           21.6%      5.60      0.357

    ถ้าช่องไม่มีความหมาย (เป็นเซ็ตไม่เรียง) ทั้งสี่แถวต้องเหมือนกัน
    แต่มันไล่ระดับทุกคอลัมน์ และ 10 ตัวที่ถูกแบนบ่อยสุดใน b1 กิน 80% ของ b1
    แต่กินแค่ 15.9% ของ b4

    รอยต่อเฟสก็เห็นได้ — b1/b2 เป็นตัว must-ban (sinestrea · rouie · elandorr)
    ส่วน b3/b4 เปลี่ยนชุดไปเป็นตัวที่แบนตอบสนอง (florentino · omen · murad)

    ⚠️ นี่คือการยืนยันว่า **ช่องข้อมูลเรียงตามลำดับ** ไม่ใช่การยืนยัน
    ลำดับ ban/pick ตาม rulebook ของรายการ ซึ่งยังไม่มีเอกสารรองรับ
    (ดู configs/draft/format.yaml)
    """

    slot: int                       # 1-based
    picks: Counter[str] = field(default_factory=Counter)
    n: int = 0

    @property
    def top(self) -> list[tuple[str, int]]:
        return self.picks.most_common()

    @property
    def concentration(self) -> float:
        """3 ตัวแรกกินสัดส่วนเท่าไร — ยิ่งสูงยิ่งเดาทางได้"""
        if not self.n:
            return 0.0
        return sum(k for _, k in self.picks.most_common(3)) / self.n


def ban_slots(comps: list[Comp]) -> list[BanSlot]:
    """แยกการแบนของทีมตามลำดับตา"""
    out: dict[int, BanSlot] = {}
    for comp in comps:
        for i, hero in enumerate(comp.bans):
            slot = out.setdefault(i + 1, BanSlot(slot=i + 1))
            slot.picks[hero] += 1
            slot.n += 1
    return [out[k] for k in sorted(out)]


@dataclass
class TeamCompProfile:
    team: str
    comps: list[Comp] = field(default_factory=list)
    repeats: RepeatStats = field(default_factory=RepeatStats)
    shapes: list[ShapeRate] = field(default_factory=list)
    bonds: list[PairBond] = field(default_factory=list)
    bans: list[BanSlot] = field(default_factory=list)
    # เกณฑ์ความบังเอิญที่ได้จากการสับไพ่ — คู่ที่ต่ำกว่านี้ไม่ถูกเก็บเข้า bonds
    bond_threshold: int = 0
    skipped_unknown_class: int = 0

    @property
    def n(self) -> int:
        return len(self.comps)

    @property
    def reliable(self) -> bool:
        return self.n >= MIN_COMPS

    @property
    def notable_shapes(self) -> list[ShapeRate]:
        """เรียงตามขนาดของความต่าง ไม่ใช่ตามอัตราดิบ

        ทรงที่ทุกทีมเล่นบ่อยเท่ากันไม่ได้บอกอะไรเกี่ยวกับทีมนี้
        สิ่งที่บอกคือส่วนที่ **ต่างจากลีก**
        """
        return sorted(
            (s for s in self.shapes if s.notable),
            key=lambda s: -abs(s.diff),
        )


# ────────────────────────────────────────────────────────── การคำนวณ


def _class_counts(heroes: tuple[str, ...], by_id: dict[str, object]) -> Counter[str] | None:
    """นับ class ของคอมพ์ — คืน None ถ้ามีตัวที่ยังไม่รู้ class

    คืน None ไม่ใช่ Counter ว่าง เพราะ "ไม่รู้" กับ "รู้ว่าไม่มี" ต่างกันสิ้นเชิง
    ถ้าเผลอรวมสองอย่างนี้ ทีมที่มีฮีโร่นอกฐานข้อมูลจะถูกนับเป็น "ไม่มีแทงค์"
    """
    counts: Counter[str] = Counter()
    for hid in heroes:
        hero = by_id.get(hid)
        if hero is None or not hero.hero_class:
            return None
        for cls in hero.hero_class:
            counts[cls.value if hasattr(cls, "value") else str(cls)] += 1
    return counts


def collect_comps(all_series: list[SeriesDraft]) -> dict[str, list[Comp]]:
    """ดึงคอมพ์ของทุกทีมออกมาจากเกมที่ข้อมูลครบ"""
    out: dict[str, list[Comp]] = defaultdict(list)
    for series in all_series:
        for game in series.complete_games:
            sides = (
                (game.blue_team, game.blue_picks, game.blue_bans, game.red_team, True),
                (game.red_team, game.red_picks, game.red_bans, game.blue_team, False),
            )
            for team, picks, bans, foe, is_blue in sides:
                if not team or len(picks) != TEAM_SIZE:
                    continue
                out[team].append(
                    Comp(
                        team=team,
                        heroes=tuple(picks),
                        won=team == game.winner_team,
                        blue=is_blue,
                        date=(d.isoformat() if (d := parse_date(series.date)) else None),
                        opponent=foe,
                        bans=tuple(bans),
                    )
                )
    return dict(out)


def newest_first(comps: list[Comp]) -> list[Comp]:
    """เรียงใหม่ไปเก่า โดยดันเกมที่อ่านวันที่ไม่ได้ไปท้ายสุด

    ห้ามใช้ `sorted(..., reverse=True)` ตรง ๆ กับค่าที่อาจเป็น None
    และห้ามแทน None ด้วยสตริงว่าง เพราะ reverse จะดันมันขึ้นมาอยู่บนสุด
    กลายเป็นว่าเกมที่ไม่รู้วันที่ถูกนำเสนอเป็น "ล่าสุด"
    """
    dated = sorted((c for c in comps if c.date), key=lambda c: c.date, reverse=True)
    return dated + [c for c in comps if not c.date]


def repeat_stats(comps: list[Comp]) -> RepeatStats:
    seen = Counter(c.key for c in comps)
    return RepeatStats(
        total=len(comps),
        distinct=len(seen),
        max_repeat=max(seen.values()) if seen else 0,
        repeated_sets=sum(1 for v in seen.values() if v > 1),
    )


def league_shape_rates(
    comps: list[Comp], by_id: dict[str, object]
) -> tuple[dict[str, float], int]:
    """อัตราของแต่ละทรงทั้งลีก — เป็นเส้นฐานที่ใช้เทียบทุกทีม

    ต้องคิดจากคอมพ์ **ทุกทีมรวมกัน** ไม่ใช่ค่าเฉลี่ยของอัตรารายทีม
    เพราะทีมที่เล่นน้อยจะได้น้ำหนักเท่าทีมที่เล่นเยอะ ซึ่งบิดเส้นฐาน
    """
    hits: Counter[str] = Counter()
    n = 0
    for comp in comps:
        counts = _class_counts(comp.heroes, by_id)
        if counts is None:
            continue
        n += 1
        for rule in SHAPES:
            if rule.holds(counts):
                hits[rule.key] += 1
    return ({r.key: hits[r.key] / n for r in SHAPES} if n else {r.key: 0.0 for r in SHAPES}), n


def shape_rates(
    comps: list[Comp], by_id: dict[str, object], league: dict[str, float]
) -> tuple[list[ShapeRate], int]:
    """อัตราของแต่ละทรงสำหรับทีมเดียว พร้อมช่วงความเชื่อมั่น"""
    per: dict[str, ShapeRate] = {
        r.key: ShapeRate(rule=r, league_rate=league.get(r.key, 0.0)) for r in SHAPES
    }
    n = skipped = 0
    for comp in comps:
        counts = _class_counts(comp.heroes, by_id)
        if counts is None:
            skipped += 1
            continue
        n += 1
        for rule in SHAPES:
            if rule.holds(counts):
                per[rule.key].hits += 1
                per[rule.key].wins += comp.won
    for rate in per.values():
        rate.n = n
        rate.lo, rate.hi = wilson_interval(rate.hits, n)
    return list(per.values()), skipped


def chance_threshold(comps: list[Comp], rounds: int = SHUFFLE_ROUNDS) -> int:
    """คู่ต้องมาด้วยกันกี่ครั้งจึงจะเกินความบังเอิญ

    วิธี: เอาฮีโร่ทั้งหมดที่ทีมนี้เคยใช้มากองรวมกัน สับใหม่ แล้วแบ่งเป็นชุดละ 5
    ทำซ้ำหลายรอบ ดูว่า **คู่ที่มาด้วยกันบ่อยที่สุด** ในโลกที่ไม่มีเจตนาเลย
    ได้เท่าไร แล้วใช้ค่าเปอร์เซ็นไทล์ที่ 95 เป็นเกณฑ์

    ทำไมต้องใช้ค่าสูงสุดไม่ใช่ค่าของคู่ใด ๆ: คอมพ์หนึ่งมี 10 คู่ ทีมหนึ่งมีคู่
    ที่เป็นไปได้หลายร้อยคู่ ถ้าทดสอบทีละคู่ด้วยเกณฑ์ 5% จะมีคู่ที่ "ผ่าน"
    เพราะบังเอิญเสมอ การเทียบกับค่าสูงสุดคือการคุมปัญหานั้นไปในตัว

    ข้อจำกัด: การสับแบบนี้คงความถี่ของฮีโร่ไว้ แต่ไม่คงข้อจำกัดของ
    Global Ban-Pick และไม่คงโครงสร้างเลน จึงเป็นเส้นฐานที่ **หลวมกว่า**
    ความจริงเล็กน้อย ผลคืออนุรักษ์นิยม — คู่ที่ผ่านเกณฑ์นี้น่าเชื่อกว่าที่ตัวเลขบอก
    """
    pool = [h for c in comps for h in c.heroes]
    n_comps = len(pool) // TEAM_SIZE
    if n_comps < 2:
        return 0
    rng = random.Random(SHUFFLE_SEED)
    peaks: list[int] = []
    for _ in range(rounds):
        shuffled = pool[:]
        rng.shuffle(shuffled)
        pairs: Counter[tuple[str, str]] = Counter()
        for i in range(n_comps):
            chunk = set(shuffled[i * TEAM_SIZE : (i + 1) * TEAM_SIZE])
            pairs.update(itertools.combinations(sorted(chunk), 2))
        peaks.append(max(pairs.values()) if pairs else 0)
    peaks.sort()
    return peaks[min(len(peaks) - 1, int(len(peaks) * 0.95))]


def pair_bonds(comps: list[Comp], threshold: int, limit: int = 6) -> list[PairBond]:
    """คู่ที่มาด้วยกันเกินเกณฑ์ความบังเอิญ — ส่วนใหญ่จะได้ลิสต์ว่าง

    ลิสต์ว่างคือคำตอบที่ถูกต้อง ไม่ใช่ความล้มเหลว

    ต้องผ่าน **สองด่าน** เพราะแต่ละด่านกันคนละอย่าง

      1. จำนวนครั้ง > `threshold` ที่ได้จากการสับไพ่
         กันปัญหาการทดสอบหลายคู่พร้อมกันแล้วมีคู่ผ่านเพราะบังเอิญ

      2. lift > 1 คือมาด้วยกันบ่อยกว่าที่ความถี่ของแต่ละตัวอธิบายได้
         ถ้าทีมหยิบสองตัวนี้แทบทุกเกมอยู่แล้ว การที่มันอยู่ด้วยกันไม่ใช่
         "ความผูกพัน" แต่เป็นผลพลอยได้ของความนิยมรายตัว — lift จะได้ 1.0 พอดี
         และคู่แบบนั้นต้องไม่ขึ้นหน้าเว็บว่าเป็นคอมโบประจำทีม
    """
    if threshold <= 0:
        return []
    n = len(comps)
    solo = Counter(h for c in comps for h in c.heroes)
    together: Counter[tuple[str, str]] = Counter()
    wins: Counter[tuple[str, str]] = Counter()
    for comp in comps:
        for pair in itertools.combinations(sorted(comp.heroes), 2):
            together[pair] += 1
            wins[pair] += comp.won

    out = []
    for (a, b), k in together.items():
        if k <= threshold:
            continue
        # คาดหวังถ้าสองตัวถูกเลือกอิสระต่อกัน
        expected = solo[a] * solo[b] / n if n else 0.0
        if expected <= 0 or k <= expected:
            continue
        out.append(PairBond(a=a, b=b, together=k, expected=expected, wins=wins[(a, b)]))
    out.sort(key=lambda p: (-p.together, -p.lift))
    return out[:limit]


def team_comp_profiles(
    all_series: list[SeriesDraft],
    hero_db: HeroDB,
    min_comps: int = MIN_COMPS,
) -> dict[str, TeamCompProfile]:
    """โปรไฟล์คอมพ์ของทุกทีมที่มีข้อมูลพอ"""
    by_id = {h.id: h for h in hero_db.heroes}
    per_team = collect_comps(all_series)
    every = [c for rows in per_team.values() for c in rows]
    league, _ = league_shape_rates(every, by_id)

    out: dict[str, TeamCompProfile] = {}
    for team, comps in per_team.items():
        if len(comps) < min_comps:
            continue
        shapes, skipped = shape_rates(comps, by_id, league)
        threshold = chance_threshold(comps)
        out[team] = TeamCompProfile(
            team=team,
            comps=comps,
            repeats=repeat_stats(comps),
            shapes=shapes,
            bonds=pair_bonds(comps, threshold),
            bans=ban_slots(comps),
            bond_threshold=threshold,
            skipped_unknown_class=skipped,
        )
    return out


# ──────────────────────────────────────────────────────────── รายงาน


def report(profile: TeamCompProfile) -> str:
    """รายงานข้อความสำหรับ CLI"""
    p = profile
    lines = [
        f"── คอมพ์ของ {p.team} ──",
        f"  {p.n} คอมพ์ · ชนะ {sum(c.won for c in p.comps)}",
        "",
        "  ชุด 5 ตัวซ้ำไหม",
        f"    ไม่ซ้ำกัน {p.repeats.distinct} แบบ จาก {p.repeats.total} คอมพ์"
        f" ({p.repeats.distinct_share * 100:.0f}%)",
        f"    ชุดที่ใช้ซ้ำมากสุด {p.repeats.max_repeat} ครั้ง → {p.repeats.verdict}",
        "",
        "  รูปทรงที่ต่างจากลีกอย่างมีนัย",
    ]
    notable = p.notable_shapes
    if not notable:
        lines.append("    ไม่มี — ทุกทรงอยู่ในช่วงเดียวกับลีก")
    for s in notable:
        wr = f" · ชนะ {s.win_rate * 100:.0f}%" if s.win_rate is not None else ""
        lines.append(
            f"    {s.rule.label:<14} {s.rate * 100:5.1f}% "
            f"[{s.lo * 100:.1f}, {s.hi * 100:.1f}] "
            f"ลีก {s.league_rate * 100:.1f}% ({s.diff * 100:+.1f}){wr}"
        )
        lines.append(f"      {s.rule.why}")

    lines += ["", "  คู่ที่มาด้วยกันเกินความบังเอิญ"]
    if not p.bonds:
        lines.append(
            f"    ไม่มี — เกณฑ์ความบังเอิญอยู่ที่ {p.bond_threshold} ครั้ง "
            "ไม่มีคู่ไหนเกิน"
        )
    for b in p.bonds:
        wr = f" · ชนะ {b.win_rate * 100:.0f}%" if b.win_rate is not None else ""
        lines.append(
            f"    {b.a} + {b.b}  {b.together} ครั้ง "
            f"(คาด {b.expected:.1f} · {b.lift:.1f}x){wr}"
        )
    lines += ["", "  ตาแบน — ช่องเรียงตามลำดับการแบนจริง"]
    if not p.bans:
        lines.append("    ไม่มีข้อมูลการแบน")
    for slot in p.bans:
        top = " · ".join(f"{h} {k}" for h, k in slot.top[:5])
        lines.append(
            f"    ตาที่ {slot.slot}  ({slot.n} ครั้ง · 3 ตัวแรกกิน "
            f"{slot.concentration * 100:.0f}%)  {top}"
        )

    lines += ["", "  คอมพ์ล่าสุด 5 เกม (ห้าตัวเรียงตามเลน ไม่ใช่ลำดับการเลือก)"]
    for c in newest_first(p.comps)[:5]:
        mark = "ชนะ" if c.won else "แพ้"
        side = "น้ำเงิน" if c.blue else "แดง"
        lines.append(
            f"    {c.date or '??':<10} เจอ {c.opponent or '?':<12} {side:<7} {mark}  "
            + " ".join(c.heroes)
        )

    if p.skipped_unknown_class:
        lines.append("")
        lines.append(
            f"  ⚠️ ข้าม {p.skipped_unknown_class} คอมพ์ที่มีฮีโร่ยังไม่รู้ class"
        )
    return "\n".join(lines)
