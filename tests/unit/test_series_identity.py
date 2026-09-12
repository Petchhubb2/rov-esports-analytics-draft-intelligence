"""Series Identity & Global Ban-Pick — PHASE M2A.5 · property tests

บังคับ invariant 9 ข้อจาก docs/37 §4 ด้วย **series จริงที่ commit ไว้**
(`tests/fixtures/series_identity.json` — ไม่พึ่ง data/cache/ ที่ gitignore)

หัวใจ: series history / lock / wins ต้อง key ด้วย **team identity** ไม่ใช่ side
เมื่อ BO3/BO5 สลับฝั่ง ฮีโร่ที่ทีมใช้ต้องตามทีมไป ไม่ใช่ตามสี
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from rov.domain.enums import Team
from rov.draft.series import (
    GameRecord,
    GameSideAssignment,
    SeriesState,
    TeamIdentity,
)
from rov.draft.state import DraftFormat, DraftState

FIXTURE = Path("tests/fixtures/series_identity.json")


@pytest.fixture(scope="module")
def fmt() -> DraftFormat:
    return DraftFormat.load()


@pytest.fixture(scope="module")
def raw() -> dict:
    if not FIXTURE.exists():
        pytest.skip("ยังไม่มี fixture series_identity.json")
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def build_series(fx: dict, upto: int | None = None) -> SeriesState:
    """สร้าง SeriesState จาก fixture · upto = จำนวนเกมที่บันทึกแล้ว (None = ทั้งหมด)"""
    t1, t2 = fx["team1"], fx["team2"]
    teams = {t1: TeamIdentity(t1, t1), t2: TeamIdentity(t2, t2)}
    src = fx["games"] if upto is None else fx["games"][:upto]
    games = [
        GameRecord(
            game_no=i,
            assignment=GameSideAssignment(
                blue_team_id=g["blue_team"], red_team_id=g["red_team"]
            ),
            blue_picks=tuple(g["blue_picks"]),
            red_picks=tuple(g["red_picks"]),
            blue_bans=tuple(g["blue_bans"]),
            red_bans=tuple(g["red_bans"]),
            winner_team_id=g["winner_team"],
        )
        for i, g in enumerate(src, 1)
    ]
    return SeriesState(
        teams=teams,
        games=games,
        current_assignment=games[-1].assignment if games else None,
        best_of=fx["best_of"],
    )


# ─────────────────────────── fixture เป็นข้อมูลจริง · side มาจาก assignment


def test_fixture_covers_real_side_swaps(raw):
    assert raw["series"], "fixture ว่าง"
    for fx in raw["series"]:
        # identity คงที่: ทุกเกม blue/red ต้องเป็นหนึ่งในสองทีมของซีรีส์
        for g in fx["games"]:
            assert {g["blue_team"], g["red_team"]} == {fx["team1"], fx["team2"]}
        assert len(fx["t1_side_by_game"]) == len(fx["games"])
    # ต้องมีอย่างน้อยหนึ่งซีรีส์ที่ side ไม่เป็น odd/even (side ติดกันสองเกม)
    non_parity = [
        fx for fx in raw["series"]
        if any(
            fx["t1_side_by_game"][i] == fx["t1_side_by_game"][i - 1]
            for i in range(1, len(fx["t1_side_by_game"]))
        )
    ]
    assert non_parity, "fixture ต้องมีเคส non-parity (side ติดกัน) เพื่อพิสูจน์ว่าไม่ใช่ odd/even"


def test_side_comes_from_assignment_not_game_number(raw):
    """★ พิสูจน์ตรง ๆ: อ่าน side จาก GameRecord.assignment ไม่ใช่จากเลขเกม"""
    for fx in raw["series"]:
        s = build_series(fx)
        for i, g in enumerate(fx["games"]):
            rec = s.games[i]
            assert rec.assignment.side_for_team(g["blue_team"]) is Team.BLUE
            assert rec.assignment.side_for_team(g["red_team"]) is Team.RED


# ─────────────────────────────────────────────── invariant 1-8 (Python)


def test_inv1_history_follows_team_identity(raw):
    """1. used heroes ตาม team_id ไม่ใช่ side — รวม pick จากทุก side ที่ทีมเคยอยู่"""
    for fx in raw["series"]:
        s = build_series(fx)
        for tid in s.teams:
            expected = set()
            for g in fx["games"]:
                if g["blue_team"] == tid:
                    expected |= set(g["blue_picks"])
                if g["red_team"] == tid:
                    expected |= set(g["red_picks"])
            assert s.heroes_used_by(tid) == expected


def test_inv1_swapping_team_used_heroes_from_both_sides(raw):
    """★ ทีมที่สลับ side — used ต้องมี pick ตอนเป็น blue และตอนเป็น red"""
    fx = next(f for f in raw["series"] if f["id"].startswith("fs"))
    s = build_series(fx)
    fs = fx["team1"]
    blue_game = next(g for g in fx["games"] if g["blue_team"] == fs)
    red_game = next(g for g in fx["games"] if g["red_team"] == fs)
    used = s.heroes_used_by(fs)
    assert set(blue_game["blue_picks"]) <= used
    assert set(red_game["red_picks"]) <= used


def test_inv2_renaming_display_name_changes_nothing(raw, fmt):
    """2. เปลี่ยน display_name ไม่ขยับ history/locks/wins"""
    fx = raw["series"][0]
    s = build_series(fx)
    tid = fx["team1"]
    used, lock, wins = (
        s.heroes_used_by(tid),
        s.locked_heroes_for(tid, fmt),
        s.wins_of(tid),
    )
    s.teams[tid] = TeamIdentity(tid, "ชื่อใหม่คนละเรื่องเลย")
    assert s.heroes_used_by(tid) == used
    assert s.locked_heroes_for(tid, fmt) == lock
    assert s.wins_of(tid) == wins


def test_inv3_swap_twice_is_identity():
    """3. swap(swap(assignment)) == assignment"""
    a = GameSideAssignment(blue_team_id="A", red_team_id="B")
    assert a.swapped().swapped() == a
    assert a.swapped() != a


def test_inv4_side_swap_does_not_mutate_records(raw):
    """4. สลับ side ของเกมปัจจุบัน ห้ามแตะ GameRecord เก่า (records เป็น frozen)"""
    fx = raw["series"][0]
    s = build_series(fx)
    before = list(s.games)
    s.current_assignment = s.current_assignment.swapped()
    assert s.games == before, "records ต้องไม่ขยับเมื่อสลับ assignment ปัจจุบัน"
    with pytest.raises(FrozenInstanceError):
        s.games[0].winner_team_id = "X"  # type: ignore[misc]


def test_inv5_used_hero_stays_with_team_under_any_side(raw, fmt):
    """5. ถ้า Team A ใช้ hero X → X ผูกกับ A ทุก side assignment ถัดไป"""
    fx = next(f for f in raw["series"] if f["id"].startswith("fs"))
    s = build_series(fx, upto=1)  # เกม 1 เท่านั้น (fs เป็น blue ใช้ X)
    fs = fx["team1"]
    x = next(iter(set(fx["games"][0]["blue_picks"]) - set(fx["games"][0]["red_picks"])))
    assert x in s.heroes_used_by(fs)
    # สมมติเกมถัดไป fs ย้ายไป red
    s.current_assignment = GameSideAssignment(blue_team_id=fx["team2"], red_team_id=fs)
    assert x in s.locked_heroes_for(fs, fmt)


def test_inv6_team_b_never_inherits_team_a_locks(raw, fmt):
    """6. Team B ไม่รับ locks ของ Team A (scope own_team_only)"""
    for fx in raw["series"]:
        s = build_series(fx)
        a, b = fx["team1"], fx["team2"]
        a_only = s.heroes_used_by(a) - s.heroes_used_by(b)
        assert not (a_only & s.locked_heroes_for(b, fmt)), (
            f"{b} รับ lock ของ {a} มา — history รั่วข้ามทีม"
        )


def test_inv7_series_wins_follow_team_identity(raw):
    """7. series wins ตาม team_id ไม่ใช่ side"""
    for fx in raw["series"]:
        s = build_series(fx)
        for tid in s.teams:
            expected = sum(1 for g in fx["games"] if g["winner_team"] == tid)
            assert s.wins_of(tid) == expected


def test_inv8_locks_independent_of_display_side(raw, fmt):
    """8. replay ซีรีส์เดิม → locks ต่อ identity เท่าเดิม ไม่ว่าจะแสดง side ไหน"""
    for fx in raw["series"]:
        s = build_series(fx)
        for tid in s.teams:
            base = s.locked_heroes_for(tid, fmt)
            s.current_assignment = s.current_assignment.swapped()
            assert s.locked_heroes_for(tid, fmt) == base
            s.current_assignment = s.current_assignment.swapped()


# ───────────────────── DraftState integration — the actual bug being fixed


def test_draftstate_locks_follow_team_through_a_side_swap(raw, fmt):
    """★★ หัวใจของบั๊ก: fs ใช้ X ตอนเป็น blue (เกม 1) · เกม 2 fs ย้ายไป red

    locked_by_series(RED) ต้องมี X (เพราะ RED เกมนี้คือ fs) ·
    locked_by_series(BLUE) ต้องไม่มี X (นั่นคืออีกทีม) — โมเดล side-keyed เดิมจะสลับผิด
    """
    fx = next(f for f in raw["series"] if f["id"].startswith("fs"))
    s = build_series(fx, upto=1)
    fs = fx["team1"]
    x = next(iter(set(fx["games"][0]["blue_picks"]) - set(fx["games"][0]["red_picks"])))

    g2 = fx["games"][1]  # เกม 2: fs = red ตาม fixture
    assert g2["red_team"] == fs, "fixture เกม 2 fs ต้องเป็น red"
    cur = GameSideAssignment(blue_team_id=g2["blue_team"], red_team_id=g2["red_team"])
    s.current_assignment = cur
    st = DraftState(fmt=fmt, pool=set(), sides=cur, series=s)

    assert x in st.locked_by_series(Team.RED), "X ต้อง lock ให้ fs (ฝั่ง RED เกมนี้)"
    assert x not in st.locked_by_series(Team.BLUE), "X ต้องไม่ lock ให้อีกทีม (BLUE)"


def test_draftstate_team_name_follows_identity_not_side(raw, fmt):
    """display name ตามทีมที่อยู่ฝั่งนั้นในเกมนี้ (ผ่าน identity)"""
    fx = next(f for f in raw["series"] if f["id"].startswith("fs"))
    s = build_series(fx, upto=1)
    g2 = fx["games"][1]
    cur = GameSideAssignment(blue_team_id=g2["blue_team"], red_team_id=g2["red_team"])
    s.current_assignment = cur
    st = DraftState(fmt=fmt, pool=set(), sides=cur, series=s)
    assert st.team_name(Team.RED) == s.teams[fx["team1"]].display_name
    assert st.team_name(Team.BLUE) == s.teams[fx["team2"]].display_name


def test_single_game_state_has_no_series_locks(fmt):
    """ไม่ส่ง series/sides = เกมเดี่ยว → ไม่มี lock (ของเดิมไม่พัง)"""
    st = DraftState(fmt=fmt, pool={"a", "b"})
    assert st.locked_by_series(Team.BLUE) == set()
    assert st.locked_by_series(Team.RED) == set()


# ─────────────────────── invariant 9 · Python / JS parity (รัน JS จริง)

import shutil  # noqa: E402
import subprocess  # noqa: E402

TPL = Path("apps/web/draft_board.tpl.html")


def _js_locks(results, assign, bo):
    """รัน helper lock ของ template จริงใน node แล้วคืน locks/used/wins

    ดึงบล็อกโค้ดจริง (const TEAM_IDS ... function lockedFor) มา eval — ไม่ได้เขียนซ้ำ
    """
    node = shutil.which("node")
    if node is None:
        pytest.skip("ไม่มี node — ข้าม parity ที่รัน JS จริง")
    tpl = TPL.read_text(encoding="utf-8")
    start = tpl.index("const TEAM_IDS")
    end = tpl.index("return heroesUsedBy(S.assign[side]);")
    end = tpl.index("}", end) + 1
    region = tpl[start:end]
    s_obj = {"results": results, "assign": assign, "bo": bo, "moves": [], "names": {}}
    harness = (
        "const SEQ = [];\n"
        f"const S = {json.dumps(s_obj)};\n"
        f"{region}\n"
        "console.log(JSON.stringify({"
        "lock_blue:[...lockedFor('blue')].sort(),"
        "lock_red:[...lockedFor('red')].sort(),"
        "used:Object.fromEntries([...new Set(S.results.flatMap(r=>r.moves.map(m=>m.teamId)))]"
        ".map(t=>[t,[...heroesUsedBy(t)].sort()])),"
        "wins:Object.fromEntries([...new Set(S.results.map(r=>r.winnerId))].map(t=>[t,winsOf(t)])),"
        "}));"
    )
    r = subprocess.run([node, "-e", harness], capture_output=True, text=True)
    assert r.returncode == 0, f"node error: {r.stderr}"
    return json.loads(r.stdout)


def _js_results_from_fixture(fx, upto):
    """แปลง fixture → S.results รูปแบบ JS (moves by teamId + assignment snapshot)"""
    out = []
    for g in fx["games"][:upto]:
        moves = (
            [{"teamId": g["blue_team"], "action": "PICK", "hero": h} for h in g["blue_picks"]]
            + [{"teamId": g["red_team"], "action": "PICK", "hero": h} for h in g["red_picks"]]
            + [{"teamId": g["blue_team"], "action": "BAN", "hero": h} for h in g["blue_bans"]]
            + [{"teamId": g["red_team"], "action": "BAN", "hero": h} for h in g["red_bans"]]
        )
        out.append(
            {
                "winnerId": g["winner_team"],
                "assignment": {"blue": g["blue_team"], "red": g["red_team"]},
                "moves": moves,
            }
        )
    return out


def test_inv9_python_and_js_agree_on_locks_through_side_swap(raw, fmt):
    """9. ★ Python (SeriesState) และ JS (template จริง) ตรงกัน: used · wins · locks

    ใช้ fs vs godji: fs = blue เกม 1, red เกม 2 · เกม 3 fs = blue อีกครั้ง
    lock ของฝั่ง blue เกม 3 ต้องเป็นของ fs (ตาม identity) ทั้งสองภาษา
    """
    fx = next(f for f in raw["series"] if f["id"].startswith("fs"))
    upto = 2  # บันทึกเกม 1-2 · เกม 3 กำลังจะดราฟต์
    fs, godji = fx["team1"], fx["team2"]
    g3 = fx["games"][2]
    assign = {"blue": g3["blue_team"], "red": g3["red_team"]}  # เกม 3: fs = blue

    js = _js_locks(_js_results_from_fixture(fx, upto), assign, fx["best_of"])

    s = build_series(fx, upto=upto)
    s.current_assignment = GameSideAssignment(
        blue_team_id=g3["blue_team"], red_team_id=g3["red_team"]
    )

    # used heroes ตรงกันทุกทีม
    assert set(js["used"][fs]) == s.heroes_used_by(fs)
    assert set(js["used"][godji]) == s.heroes_used_by(godji)
    # wins ตรงกัน (by identity)
    assert js["wins"][fs] == s.wins_of(fs)
    # locks ต่อ side (เกม 3) ตรงกัน และตาม identity
    assert set(js["lock_blue"]) == s.locked_heroes_for(g3["blue_team"], fmt)
    assert set(js["lock_red"]) == s.locked_heroes_for(g3["red_team"], fmt)
    # และ fs (blue เกม 3) ถูก lock ด้วยฮีโร่ที่ใช้ตอนเป็น red เกม 2 ด้วย
    assert set(fx["games"][1]["red_picks"]) <= set(js["lock_blue"])
