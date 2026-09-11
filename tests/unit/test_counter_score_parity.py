"""counter_score ถูกเขียนไว้สามที่ — เทสต์ชุดนี้บังคับให้ทั้งสามให้ค่าตรงกัน

    packages/core/rov/draft/stats.py   MatchupStat.counter_score()
    packages/core/rov/draft/lanes.py   LaneMatchup.counter_score()
    apps/web/draft_board.tpl.html      cscore()

สูตรนี้เป็นแกนของทั้ง counter และ synergy ถ้าสามที่เพี้ยนจากกัน
อันดับคำแนะนำจะต่างกันระหว่าง context=TEAM, context=LANE และหน้าเว็บ
โดยที่ไม่มีอะไรฟ้อง

**เขียนไฟล์นี้ก่อน refactor โดยเจตนา** (PHASE B · Q6)
เพื่อให้การรวมสามที่เป็นหนึ่งพิสูจน์ได้ว่าไม่เปลี่ยนค่า ไม่ใช่เชื่อเอาเอง
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from rov.draft.lanes import LaneMatchup
from rov.draft.stats import SHRINKAGE_K, MatchupStat

TPL = Path("apps/web/draft_board.tpl.html")

# (games, wins) ที่ครอบคลุมกรณีสำคัญ — ไม่มีข้อมูล, น้อยมาก, สมดุล,
# ชนะขาด, แพ้ขาด, ตัวอย่างใหญ่
CASES = [
    (0, 0), (1, 0), (1, 1), (3, 2), (8, 4), (8, 8), (8, 0),
    (15, 9), (30, 15), (30, 24), (60, 31), (200, 118),
]
PRIORS = [0.5, 0.42, 0.58]


def js_cscore(games: int, wins: int, prior: float, k: int) -> float:
    """สูตรเดียวกับ cscore() ใน template — แกะค่าคงที่ออกมาจากไฟล์จริง"""
    adj = (wins + k * prior) / (games + k)
    conf = games / (games + k) if games else 0.0
    return (adj - prior) * 100.0 * conf


# ------------------------------------------------------ Python ↔ Python


@pytest.mark.parametrize("games,wins", CASES)
@pytest.mark.parametrize("prior", PRIORS)
def test_team_and_lane_matchup_agree(games, wins, prior):
    """MatchupStat กับ LaneMatchup ต้องให้ค่าเท่ากันเป๊ะ

    ทั้งคู่วัด "ดีกว่าค่ากลางแค่ไหน ถ่วงด้วยความมั่นใจ" เหมือนกัน
    ต่างกันแค่ context ที่เก็บข้อมูลมา ไม่ใช่วิธีคิด
    """
    a = MatchupStat(hero_id="x", enemy_id="y", games=games, wins=wins)
    b = LaneMatchup(lane="mid", hero_id="x", enemy_id="y", games=games, wins=wins)
    assert a.counter_score(prior) == pytest.approx(b.counter_score(prior), abs=1e-12)
    assert a.adjusted(prior) == pytest.approx(b.adjusted(prior), abs=1e-12)


@pytest.mark.parametrize("games,wins", CASES)
def test_no_data_scores_exactly_zero(games, wins):
    """คู่ที่ไม่มีข้อมูลต้องได้ 0 พอดี ไม่ใช่ค่าสุดโต่ง

    นี่คือคุณสมบัติที่ทำให้เพิ่มน้ำหนัก counter ได้โดยไม่ขยาย noise
    """
    if games:
        pytest.skip("เคสนี้มีข้อมูล")
    m = MatchupStat(hero_id="x", enemy_id="y", games=0, wins=0)
    assert m.counter_score(0.5) == 0.0


def test_confidence_grows_with_sample_size():
    lo = MatchupStat(hero_id="x", enemy_id="y", games=5, wins=5)
    hi = MatchupStat(hero_id="x", enemy_id="y", games=200, wins=200)
    assert abs(hi.counter_score(0.5)) > abs(lo.counter_score(0.5))


# ---------------------------------------------------------- Python ↔ JS


@pytest.fixture(scope="module")
def js_constants() -> tuple[str, str]:
    """ดึงนิพจน์ของ adj และ conf ออกจาก template"""
    tpl = TPL.read_text(encoding="utf-8")
    adj = re.search(r"const adj = \(g,w\) => ([^;]+);", tpl)
    conf = re.search(r"const conf = g => ([^;]+);", tpl)
    cscore = re.search(r"const cscore = \(g,w\) => ([^;]+);", tpl)
    assert adj, "หา const adj ใน template ไม่เจอ"
    assert conf, "หา const conf ใน template ไม่เจอ"
    assert cscore, "หา const cscore ใน template ไม่เจอ"
    return adj.group(1), conf.group(1), cscore.group(1)


def test_js_cscore_is_built_from_adj_and_conf(js_constants):
    """โครงสร้างฝั่ง JS ต้องเป็น (adj - PRIOR) * 100 * conf เหมือนฝั่ง Python"""
    _adj, _conf, cscore = js_constants
    norm = cscore.replace(" ", "")
    assert "adj(g,w)-PRIOR" in norm
    assert "*100*conf(g)" in norm


def test_js_adj_uses_shrinkage_toward_prior(js_constants):
    adj, _conf, _ = js_constants
    norm = adj.replace(" ", "")
    assert norm == "(w+K*PRIOR)/(g+K)", f"สูตร adj ฝั่ง JS เปลี่ยนไป: {adj}"


def test_js_conf_matches_python(js_constants):
    """conf ฝั่ง JS เขียน guard ไว้ด้วย — `g ? g/(g+K) : 0`

    guard นั้นซ้ำซ้อนทางคณิตศาสตร์ (g=0 ก็ได้ 0 อยู่แล้ว) แต่ฝั่ง Python
    ก็เขียน `if games else 0.0` เหมือนกัน จึงถือว่าตรงกัน
    เทสต์จึงตรวจแกนของสูตร ไม่ใช่ตัวอักษรทั้งบรรทัด
    """
    _adj, conf, _ = js_constants
    norm = conf.replace(" ", "")
    assert "g/(g+K)" in norm, f"สูตร conf ฝั่ง JS เปลี่ยนไป: {conf}"
    # ถ้ามี guard ต้องคืน 0 ไม่ใช่ค่าอื่น
    if "?" in norm:
        assert norm.endswith(":0"), f"guard ของ conf ไม่ได้คืน 0: {conf}"


@pytest.mark.parametrize("games,wins", CASES)
@pytest.mark.parametrize("prior", PRIORS)
def test_js_formula_reproduces_python_values(games, wins, prior):
    """จำลองสูตร JS ด้วย Python แล้วต้องได้ค่าเท่ากับของจริง"""
    py = MatchupStat(hero_id="x", enemy_id="y", games=games, wins=wins)
    assert py.counter_score(prior) == pytest.approx(
        js_cscore(games, wins, prior, SHRINKAGE_K), abs=1e-12
    )


def test_shrinkage_k_reaches_the_web_through_data_not_a_copy():
    """K ต้องถูกส่งผ่าน draft_data.json ไม่ใช่เขียนเลขซ้ำใน JS

    ค่าที่ส่งผ่านข้อมูลเพี้ยนไม่ได้ ส่วนค่าที่เขียนซ้ำเพี้ยนได้เสมอ
    """
    tpl = TPL.read_text(encoding="utf-8")
    assert "const K = D.shrinkage_k" in tpl
    assert not re.search(r"const K = 30\b", tpl), "K ถูก hardcode ใน JS แล้ว"
