"""Benchmark ของ Draft Engine บนดราฟต์จริง — PHASE B · Q8

**ทำไมต้องมี**

docs/20 §11 เขียนไว้ว่า "ห้ามอ้างว่าฉลาดขึ้นโดยไม่มีตัวเลข"
โมดูลนี้คือตัวเลขนั้น วัดได้ก่อน/หลังทุกครั้งที่แตะ engine

**การแบ่งข้อมูล — แบ่งตามเวลา ไม่ใช่สุ่ม**

เมตาเปลี่ยนตามเวลา การสุ่มแบ่งจะทำให้ engine เห็นเกมที่แข่งทีหลัง
ของเมตาเดียวกัน ซึ่งเป็น leakage ที่ตรวจไม่เจอและทำให้คะแนนดูดีเกินจริง

    train  แมตช์เก่ากว่า cutoff  -> ใช้คำนวณ presence/winrate/matchup/synergy
    eval   แมตช์ใหม่กว่า cutoff  -> ใช้ทดสอบว่าแนะนำตรงกับที่ทีมอาชีพเลือกไหม

`pooled` ของ eval **ต้องสร้างจาก train เท่านั้น** ถ้าเผลอใช้ทั้งชุด
engine จะรู้ผลอนาคต และ top-k hit rate จะพุ่งขึ้นแบบไม่มีความหมาย
`assert_no_leakage()` มีไว้กันเรื่องนี้โดยเฉพาะ

**อ่านตัวเลขอย่างไร**

top-k hit rate วัดว่า "ตรงกับที่ทีมอาชีพเลือกแค่ไหน" ซึ่ง**ไม่ใช่**
"ถูกต้องแค่ไหน" — ทีมอาชีพเลือกผิดได้ และการเลียนแบบ 100% ไม่ใช่เป้าหมาย
ใช้มันเป็น "เกณฑ์ห้ามถอยหลัง" ตอนเพิ่ม factor ไม่ใช่เป้าที่ต้องไล่ให้สูงสุด
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from rov.draft.importer.parser import SeriesDraft
from rov.draft.meta import PooledStats, Region, pool
from rov.draft.scouting import parse_date
from rov.draft.state import DraftFormat, DraftState


class LeakageError(AssertionError):
    """ข้อมูล evaluation รั่วเข้าไปใน training — ผลที่ได้เชื่อไม่ได้"""


def split_by_time(
    all_series: list[SeriesDraft], cutoff: date
) -> tuple[list[SeriesDraft], list[SeriesDraft]]:
    """แบ่ง train/eval ตามวันที่

    ซีรีส์ที่ไม่มีวันที่จะเข้า train เพราะใช้ทดสอบไม่ได้อยู่แล้ว
    (ไม่รู้ว่ามันอยู่ก่อนหรือหลัง cutoff)
    """
    train, ev = [], []
    for s in all_series:
        d = parse_date(s.date)
        if d is not None and d >= cutoff:
            ev.append(s)
        else:
            train.append(s)
    return train, ev


def assert_no_leakage(train: list[SeriesDraft], ev: list[SeriesDraft]) -> None:
    """ยืนยันว่าไม่มีซีรีส์เดียวกันอยู่ทั้งสองฝั่ง และวันที่ไม่คาบกัน"""
    def ident(s: SeriesDraft) -> tuple:
        return (s.team1, s.team2, s.date, len(s.games))

    overlap = {ident(s) for s in train} & {ident(s) for s in ev}
    if overlap:
        raise LeakageError(f"ซีรีส์ซ้ำกันทั้ง train และ eval: {len(overlap)} รายการ")

    train_dates = [d for s in train if (d := parse_date(s.date))]
    eval_dates = [d for s in ev if (d := parse_date(s.date))]
    if train_dates and eval_dates and max(train_dates) >= min(eval_dates):
        raise LeakageError(
            f"ช่วงเวลาคาบกัน — train ล่าสุด {max(train_dates)} "
            f"แต่ eval เริ่ม {min(eval_dates)}"
        )


@dataclass
class Benchmark:
    """ผลการวัด — ทุกช่องมีตัวหารกำกับ ไม่มีเปอร์เซ็นต์ลอย ๆ"""

    n_drafts: int = 0
    n_turns: int = 0
    n_candidates: int = 0

    # B1 — ตัวที่ทีมอาชีพเลือกจริง ติดอันดับเท่าไร
    top1: int = 0
    top3: int = 0
    top5: int = 0
    scored_turns: int = 0          # ตาที่ตัวจริงอยู่ในกลุ่ม candidate ที่ประเมินได้

    # ความครอบคลุมของ factor — นับเฉพาะที่มีข้อมูลจริง (raw != 0)
    with_composition: int = 0
    with_lane_counter: int = 0
    with_trait_counter: int = 0

    # B6 — คำแนะนำอธิบายตัวเองได้แค่ไหน
    with_gaps: int = 0
    all_components_explained: int = 0

    # B7 — ระบบบอก "ไม่รู้" เมื่อไม่รู้จริงไหม
    unknown_reported: int = 0

    notes: list[str] = field(default_factory=list)

    def _pct(self, n: int, d: int) -> str:
        return f"{n}/{d} = {n / d:.1%}" if d else f"{n}/0 = —"

    def report(self) -> str:
        lines = [
            "═══ Draft Engine Benchmark ═══",
            "",
            f"  ดราฟต์ {self.n_drafts} เกม · {self.n_turns} ตา · "
            f"candidate ที่ประเมิน {self.n_candidates}",
            "",
            "  ── ตรงกับที่ทีมอาชีพเลือกแค่ไหน (B1) ──",
            f"  อันดับ 1 ตรง     {self._pct(self.top1, self.scored_turns)}",
            f"  ติด 3 อันดับแรก  {self._pct(self.top3, self.scored_turns)}",
            f"  ติด 5 อันดับแรก  {self._pct(self.top5, self.scored_turns)}",
            "",
            "  ── ความครอบคลุมของ factor ──",
            "  (นับเฉพาะที่มีข้อมูลจริง ไม่ใช่แค่มี component)",
            f"  composition      {self._pct(self.with_composition, self.n_candidates)}",
            f"  lane counter     {self._pct(self.with_lane_counter, self.n_candidates)}",
            f"  trait counter    {self._pct(self.with_trait_counter, self.n_candidates)}",
            "",
            "  ── อธิบายตัวเองได้แค่ไหน (B6) ──",
            f"  มี fills/creates gaps  {self._pct(self.with_gaps, self.n_candidates)}",
            f"  ทุก component บอกที่มา {self._pct(self.all_components_explained, self.n_candidates)}",
            "",
            "  ── ยอมบอกว่าไม่รู้ไหม (B7) ──",
            f"  component ที่บอกว่ายังไม่มีข้อมูล {self.unknown_reported}",
        ]
        if self.notes:
            lines += ["", "  หมายเหตุ"]
            lines += [f"    · {n}" for n in self.notes]
        lines += [
            "",
            "  ⚠ top-k hit rate วัดความ 'ตรงกับทีมอาชีพ' ไม่ใช่ความ 'ถูกต้อง'",
            "    ใช้เป็นเกณฑ์ห้ามถอยหลังตอนเพิ่ม factor ไม่ใช่เป้าที่ต้องไล่ให้สูงสุด",
        ]
        return "\n".join(lines)


def _informative(components: dict, key: str) -> bool:
    """component นี้มีข้อมูลจริงหรือแค่โผล่มาเป็นค่ากลาง

    raw = 0 คือ "ไม่มีคู่ที่ถึงเกณฑ์" ไม่ใช่ "เท่ากันพอดี"
    ถ้านับรวมจะได้ 100% ซึ่งหลอกตัวเองว่า factor นี้ใช้ได้เต็มที่
    """
    x = components.get(key)
    return x is not None and abs(x.raw) > 1e-12


def run(
    train: list[SeriesDraft],
    ev: list[SeriesDraft],
    fmt: DraftFormat,
    recommend_fn,
    *,
    lane_usage: dict | None = None,
    lanes: list[str] | None = None,
    lane_matchups: dict | None = None,
    hero_db=None,
    top_k: int = 5,
    min_games: int = 5,
    max_drafts: int | None = None,
) -> Benchmark:
    """เดินทุกดราฟต์ใน eval แล้ววัดผล โดยใช้สถิติจาก train เท่านั้น"""
    assert_no_leakage(train, ev)

    pooled: PooledStats = pool([Region(key="train", label="train", series=train)])
    bm = Benchmark()
    bm.notes.append(f"สถิติจาก train {pooled.total_games} เกม · eval แยกตามเวลา")

    from rov.eval.draftbench import draft_move_order, pick_drafts

    drafts = pick_drafts(ev, max_drafts or 10**6)
    for d in drafts:
        st = DraftState(fmt=fmt, pool=set(pooled.stats.heroes))
        order = draft_move_order(d, fmt.sequence)
        if not order:
            continue
        bm.n_drafts += 1
        for actual in order:
            if st.current is None:
                break
            sugs = recommend_fn(
                st, pooled, limit=top_k, min_games=min_games,
                lane_usage=lane_usage or None, lanes=lanes or None,
                lane_matchups=lane_matchups or None, hero_db=hero_db,
            )
            bm.n_turns += 1
            bm.n_candidates += len(sugs)

            ids = [s.hero_id for s in sugs]
            # นับเฉพาะตาที่ตัวจริง "มีสิทธิ์" ถูกแนะนำ — ถ้ามันถูกตัดออกไปแล้ว
            # เพราะข้อมูลน้อยกว่า min_games การนับว่าพลาดจะไม่ยุติธรรม
            if actual in st.legal_moves() and pooled.stats.get(actual).picks >= min_games:
                bm.scored_turns += 1
                if ids[:1] == [actual]:
                    bm.top1 += 1
                if actual in ids[:3]:
                    bm.top3 += 1
                if actual in ids[:top_k]:
                    bm.top5 += 1

            for s in sugs:
                c = s.components
                bm.with_composition += _informative(c, "composition")
                bm.with_lane_counter += _informative(c, "lane_counter")
                bm.with_trait_counter += _informative(c, "trait_counter")
                bm.with_gaps += bool(s.fills_gaps or s.creates_gaps)
                bm.all_components_explained += all(x.detail.strip() for x in c.values())
                bm.unknown_reported += sum(
                    1 for x in c.values()
                    if "ยังไม่" in x.detail or "ไม่มีข้อมูล" in x.detail
                )

            if actual not in st.legal_moves():
                break
            st.apply(actual)
    return bm
