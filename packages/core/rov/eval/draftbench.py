"""Regression harness สำหรับ Draft Engine — PHASE B

**ทำไมต้องมีก่อนแก้โค้ด**

PHASE B สัญญาไว้ว่า "ทุก factor ใหม่เริ่มที่น้ำหนัก 0 และ weight=0 ต้องไม่เปลี่ยน
อันดับ recommendation" คำสัญญานั้นพิสูจน์ไม่ได้เลยถ้าไม่มีภาพ "ก่อนแก้" เก็บไว้
โมดูลนี้คือเครื่องมือเก็บภาพนั้น

**ทำไมต้องเก็บข้อมูลลง fixture แทนที่จะอ่าน cache สด**

`data/cache/liquipedia/` อยู่ใน .gitignore เทสต์ที่อ่าน cache จึงรันได้เฉพาะ
เครื่องที่เคยดึงข้อมูลมาแล้ว ซึ่งทำให้ regression test ไร้ค่าบน CI หรือเครื่องใหม่
fixture จึงเก็บ **ทั้ง input และ output** ไว้ด้วยกัน เทสต์จึงรันได้ทุกที่
และยังเป็นข้อมูลจริงจากแมตช์จริง ไม่ใช่ของปลอม

**สิ่งที่เก็บลง fixture ครบตามที่ recommend() ใช้จริง**

    stats.total_games           -> presence_rate
    stats.heroes[id]            -> picks/bans/wins -> meta + winrate
    matchups (games >= 8)       -> counter
    synergies (games >= 8)      -> synergy
    lane_usage                  -> role_fit

คู่ที่ต่ำกว่า MIN_PAIR_GAMES ถูก `_counter_against()` ข้ามอยู่แล้ว
การไม่เก็บจึงให้ผลเท่ากันเป๊ะ ไม่ใช่การตัดทอนที่ทำให้ผลเพี้ยน
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rov.draft.importer.parser import SeriesDraft
from rov.draft.lanes import LaneMatchup
from rov.draft.meta import PooledStats
from rov.draft.stats import DraftStats, HeroStat, MatchupStat

# ต้องตรงกับ recommend.MIN_PAIR_GAMES — คู่ที่ต่ำกว่านี้ถูกข้ามอยู่แล้ว
FIXTURE_MIN_PAIR_GAMES = 8

# คู่ในเลนเดียวกันมีตัวอย่างน้อยกว่ามาก เกณฑ์จึงต่ำกว่า — ตรงกับ recommend.MIN_LANE_PAIR
FIXTURE_MIN_LANE_PAIR = 3


@dataclass
class ReplayTurn:
    """ผลของ recommend() ณ ตาหนึ่ง"""

    draft_id: str
    turn_index: int
    team: str
    action: str
    top: list[tuple[str, float]] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.draft_id}#{self.turn_index}"

    @property
    def order(self) -> list[str]:
        return [h for h, _ in self.top]


# ------------------------------------------------------------------ fixture


def pooled_to_dict(
    pooled: PooledStats,
    lane_usage: dict[str, dict[str, int]],
    lane_matchups: dict | None = None,
) -> dict:
    """แปลง PooledStats เป็น dict ที่ round-trip กลับมาได้เหมือนเดิม"""
    st = pooled.stats
    return {
        "total_games": st.total_games,
        "blue_wins": st.blue_wins,
        "heroes": {
            hid: [h.picks, h.bans, h.wins] for hid, h in sorted(st.heroes.items())
        },
        "matchups": sorted(
            [a, b, m.games, m.wins]
            for (a, b), m in pooled.matchups.items()
            if m.games >= FIXTURE_MIN_PAIR_GAMES
        ),
        "synergies": sorted(
            [a, b, m.games, m.wins]
            for (a, b), m in pooled.synergies.items()
            if m.games >= FIXTURE_MIN_PAIR_GAMES
        ),
        "lane_usage": {k: dict(sorted(v.items())) for k, v in sorted(lane_usage.items())},
        "lane_matchups": sorted(
            [str(lane), a, b, m.games, m.wins]
            for (lane, a, b), m in (lane_matchups or {}).items()
            if m.games >= FIXTURE_MIN_LANE_PAIR
        ),
    }


def dict_to_pooled(raw: dict) -> tuple[PooledStats, dict[str, dict[str, int]]]:
    """สร้าง PooledStats กลับจาก fixture

    ไม่เก็บ game_lengths เพราะ recommend() ไม่ได้ใช้ —
    ถ้าวันหนึ่งมี factor ที่ใช้ความยาวเกม ต้องเพิ่มที่นี่และสร้าง fixture ใหม่
    """
    st = DraftStats(total_games=raw["total_games"], blue_wins=raw.get("blue_wins", 0))
    for hid, (picks, bans, wins) in raw["heroes"].items():
        st.heroes[hid] = HeroStat(hero_id=hid, picks=picks, bans=bans, wins=wins)

    def table(rows: list) -> dict[tuple[str, str], MatchupStat]:
        out: dict[tuple[str, str], MatchupStat] = {}
        for a, b, g, w in rows:
            out[(a, b)] = MatchupStat(hero_id=a, enemy_id=b, games=g, wins=w)
        return out

    pooled = PooledStats(
        stats=st,
        matchups=table(raw["matchups"]),
        synergies=table(raw["synergies"]),
        sources=["fixture"],
        games_by_source={"fixture": raw["total_games"]},
    )
    return pooled, raw["lane_usage"]


def dict_to_lane_matchups(raw: dict) -> dict:
    """สร้างตาราง lane matchup กลับจาก fixture

    key เก็บเป็น (str, str, str) ได้ เพราะ LaneRole เป็น StrEnum
    การค้นด้วยสตริงธรรมดาจึงเจอคีย์ที่เก็บด้วย enum ได้ตามปกติ
    """
    out: dict = {}
    for lane, a, b, g, w in raw.get("lane_matchups", []):
        out[(lane, a, b)] = LaneMatchup(
            lane=lane, hero_id=a, enemy_id=b, games=g, wins=w
        )
    return out


def pick_drafts(all_series: list[SeriesDraft], limit: int) -> list[dict]:
    """เลือกดราฟต์จริงมาเป็นชุดทดสอบ

    เลือกเกมที่ข้อมูลครบและมีทั้ง ban และ pick ครบทั้งสองฝั่ง
    เพราะเกมที่ ban ไม่ครบจะ replay ไม่ได้ตามลำดับของ format.yaml

    เรียงตามชื่อทีมและวันที่ ไม่ใช่สุ่ม เพื่อให้ fixture เดิมทุกครั้งที่สร้างใหม่
    """
    rows: list[dict] = []
    for s in sorted(all_series, key=lambda x: (str(x.date), str(x.team1), str(x.team2))):
        for g in s.complete_games:
            if len(g.blue_bans) != 4 or len(g.red_bans) != 4:
                continue
            rows.append(
                {
                    "id": f"{s.team1}_vs_{s.team2}_g{g.game_index}_{s.date}",
                    "blue_team": g.blue_team,
                    "red_team": g.red_team,
                    "winner": g.winner_team,
                    "blue_bans": list(g.blue_bans),
                    "red_bans": list(g.red_bans),
                    "blue_picks": list(g.blue_picks),
                    "red_picks": list(g.red_picks),
                }
            )
            if len(rows) >= limit:
                return rows
    return rows


def draft_move_order(draft: dict, sequence) -> list[str]:
    """เรียงฮีโร่ตามลำดับตาใน format.yaml

    Liquipedia เก็บเป็นช่องของแต่ละทีม ไม่ได้เก็บลำดับรวม เราจึงต้อง
    ประกอบลำดับเองจาก `sequence` — ซึ่งลำดับนั้น**ยังไม่ยืนยัน**
    (ดู configs/draft/format.yaml) แต่ไม่เป็นไรสำหรับ regression test
    เพราะเป้าหมายคือ "ผลก่อนกับหลังแก้โค้ดเหมือนกันไหม" ไม่ใช่
    "ลำดับนี้ตรงกับที่แข่งจริงไหม" — ขอแค่ deterministic ก็พอ
    """
    pools = {
        ("blue", "BAN"): list(draft["blue_bans"]),
        ("red", "BAN"): list(draft["red_bans"]),
        ("blue", "PICK"): list(draft["blue_picks"]),
        ("red", "PICK"): list(draft["red_picks"]),
    }
    out: list[str] = []
    for turn in sequence:
        key = (turn.team, str(turn.action))
        bucket = pools.get(key)
        if not bucket:
            return out  # ข้อมูลไม่พอจะเดินต่อ — คืนเท่าที่ได้
        out.append(bucket.pop(0))
    return out


# ------------------------------------------------------------------ replay


def replay_draft(
    draft: dict,
    fmt,
    pooled: PooledStats,
    lane_usage: dict[str, dict[str, int]],
    lanes: list[str],
    recommend_fn,
    top_k: int = 5,
    min_games: int = 5,
    stop_after: int | None = None,
    lane_matchups: dict | None = None,
) -> list[ReplayTurn]:
    """เดินดราฟต์จริงทีละตา แล้วเก็บคำแนะนำของทุกตา

    `recommend_fn` ส่งเข้ามาเพื่อให้เทสต์ inject ได้ และเพื่อไม่ให้โมดูลนี้
    ผูกกับ signature ของ recommend() แน่นเกินไป
    """
    from rov.draft.state import DraftState

    state = DraftState(
        fmt=fmt,
        pool=set(pooled.stats.heroes),
        blue_name=draft.get("blue_team") or "BLUE",
        red_name=draft.get("red_team") or "RED",
    )
    order = draft_move_order(draft, fmt.sequence)
    out: list[ReplayTurn] = []

    for i, hero in enumerate(order):
        turn = state.current
        if turn is None:
            break
        if stop_after is not None and i >= stop_after:
            break
        sugs = recommend_fn(
            state,
            pooled,
            limit=top_k,
            min_games=min_games,
            lane_usage=lane_usage or None,
            lanes=lanes or None,
            lane_matchups=lane_matchups or None,
        )
        out.append(
            ReplayTurn(
                draft_id=draft["id"],
                turn_index=i,
                team=turn.team,
                action=str(turn.action),
                top=[(s.hero_id, round(s.total, 6)) for s in sugs],
            )
        )
        if hero not in state.legal_moves():
            break  # ฮีโร่ซ้ำหรือถูกล็อกด้วย Global Ban-Pick — หยุดดราฟต์นี้
        state.apply(hero)
    return out


def replay_all(fixture: dict, fmt, recommend_fn, **kw) -> dict[str, list[tuple[str, float]]]:
    """เดินทุกดราฟต์ใน fixture คืน {draft#turn: [(hero, total), ...]}"""
    pooled, lane_usage = dict_to_pooled(fixture["pool"])
    lanes = fixture.get("lanes") or []
    kw.setdefault("lane_matchups", dict_to_lane_matchups(fixture["pool"]))
    out: dict[str, list[tuple[str, float]]] = {}
    for draft in fixture["drafts"]:
        for t in replay_draft(draft, fmt, pooled, lane_usage, lanes, recommend_fn, **kw):
            out[t.key] = t.top
    return out


# ------------------------------------------------------------------ เทียบผล


@dataclass
class Diff:
    """ผลการเทียบ snapshot สองชุด"""

    turns_total: int = 0
    order_changed: list[str] = field(default_factory=list)
    top1_changed: list[str] = field(default_factory=list)
    score_changed: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def identical(self) -> bool:
        return not (
            self.order_changed or self.top1_changed or self.score_changed or self.missing
        )

    def report(self) -> str:
        if self.identical:
            return f"เหมือนเดิมทุกประการ {self.turns_total} ตา"
        lines = [f"เทียบ {self.turns_total} ตา"]
        for label, rows in (
            ("อันดับ 1 เปลี่ยน", self.top1_changed),
            ("ลำดับเปลี่ยน", self.order_changed),
            ("คะแนนเปลี่ยน (ลำดับเท่าเดิม)", self.score_changed),
            ("หายไป", self.missing),
        ):
            if rows:
                lines.append(f"  {label} {len(rows)} ตา: {', '.join(rows[:5])}"
                             + (" ..." if len(rows) > 5 else ""))
        return "\n".join(lines)


def compare(before: dict[str, Any], after: dict[str, Any], tol: float = 1e-9) -> Diff:
    """เทียบ snapshot ก่อน/หลัง

    แยกสามระดับ เพราะความหมายต่างกันมาก
        top1_changed   ตัวที่ระบบเชียร์เปลี่ยน = ผู้ใช้เห็นผลต่างทันที
        order_changed  ลำดับใน top-k สลับ = เห็นผลแต่เบากว่า
        score_changed  คะแนนขยับแต่ลำดับเท่าเดิม = ผู้ใช้แทบไม่เห็น แต่ยังต้องรู้
    """
    d = Diff(turns_total=len(before))
    for key, rows_b in before.items():
        rows_a = after.get(key)
        if rows_a is None:
            d.missing.append(key)
            continue
        order_b = [h for h, _ in rows_b]
        order_a = [h for h, _ in rows_a]
        if order_b != order_a:
            d.order_changed.append(key)
            if order_b[:1] != order_a[:1]:
                d.top1_changed.append(key)
            continue
        if any(abs(sb - sa) > tol for (_, sb), (_, sa) in zip(rows_b, rows_a, strict=True)):
            d.score_changed.append(key)
    return d


# ------------------------------------------------------------------ ไฟล์


def save_fixture(path: str | Path, data: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


def load_fixture(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
