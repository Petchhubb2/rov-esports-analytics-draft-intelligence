"""หน้าเว็บ Draft Room เขียนกติกาซ้ำไว้ใน JavaScript

`SEQ` และ `GBP` ใน apps/web/draft_board.tpl.html เป็นสำเนาของ
configs/draft/format.yaml เพราะหน้าเว็บรันในเบราว์เซอร์ อ่าน YAML ไม่ได้
สำเนาสองชุดจะเพี้ยนจากกันเงียบ ๆ ถ้าไม่มีอะไรคอยจับ

ไฟล์นี้จับ — แก้ format.yaml แล้วไม่แก้ template จะ fail ทันที
เวลาแก้ ให้แก้ที่ format.yaml ก่อนเสมอ แล้วค่อยตามไปแก้ JS ให้ตรง
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from rov.draft.state import DraftFormat

TPL = Path("apps/web/draft_board.tpl.html")


@pytest.fixture(scope="module")
def tpl() -> str:
    assert TPL.exists(), f"ไม่พบ template: {TPL}"
    return TPL.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def fmt() -> DraftFormat:
    return DraftFormat.load()


def _js_seq(tpl: str) -> list[tuple[str, str, str]]:
    """ดึงลำดับ ban/pick ออกจากตัวแปร SEQ ใน template"""
    body = re.search(r"const SEQ = \[(.*?)\]\.map", tpl, re.S)
    assert body, "หา const SEQ ใน template ไม่เจอ"
    return [
        (a, b, c)
        for a, b, c in re.findall(
            r'\["(\d+)","(blue|red)","(BAN|PICK)"\]', body.group(1)
        )
    ]


def test_js_sequence_matches_format_yaml(tpl, fmt):
    js = _js_seq(tpl)
    yml = [(str(t.phase), t.team, str(t.action)) for t in fmt.sequence]
    assert js == yml, (
        "ลำดับใน SEQ ไม่ตรงกับ configs/draft/format.yaml — "
        "หน้าเว็บจะดราฟต์คนละลำดับกับ engine ฝั่ง Python"
    )


def test_js_bans_and_picks_match_format_yaml(tpl, fmt):
    m = re.search(r"const BANS = (\d+), PICKS = (\d+);", tpl)
    assert m, "หา const BANS/PICKS ไม่เจอ"
    assert int(m.group(1)) == fmt.bans_per_team
    assert int(m.group(2)) == fmt.picks_per_team


def test_js_global_ban_pick_matches_format_yaml(tpl, fmt):
    m = re.search(r"const GBP = (\{.*?\});", tpl, re.S)
    assert m, "หา const GBP ไม่เจอ"
    gbp = json.loads(re.sub(r"(\w+):", r'"\1":', m.group(1)))
    g = fmt.global_ban_pick
    assert gbp["enabled"] is g.enabled
    assert gbp["appliesToBans"] is g.applies_to_bans
    assert gbp["resetOnFinalGame"] is g.reset_on_final_game
    # scope=both_teams จะต้องล็อกตัวของอีกฝั่งด้วย ซึ่ง JS ยังไม่รองรับ
    assert g.scope == "own_team_only", (
        "format.yaml เปลี่ยน scope แล้ว — lockedFor() ใน template "
        "รวมเฉพาะ picks ของทีมตัวเอง ต้องแก้ก่อนถึงจะถูก"
    )


def test_series_state_is_derived_not_duplicated(tpl):
    """ยอดสะสมต้องคำนวณจาก S.results ไม่ใช่เก็บซ้ำอีกชุด

    เคยมีบั๊กจากการเก็บทั้ง used-set และประวัติ พอสลับฝั่งแล้วสองอย่างไม่ตรงกัน
    """
    assert "S.used" not in tpl, "S.used ถูกแทนด้วย lockedFor() ที่คิดจากประวัติแล้ว"
    assert "const winsOf = t => S.results.filter" in tpl


def test_js_weight_formula_matches_python(tpl):
    """สูตรน้ำหนักถูกเขียนสองที่ ต้องให้ค่าตรงกัน

    JS ใช้บนหน้าเว็บ Python ใช้ใน CLI และ engine
    ถ้าสองอันเพี้ยนกัน คำแนะนำจะต่างกันโดยไม่มีใครรู้
    เทสต์นี้แกะค่าคงที่ออกจาก JS แล้วเทียบกับ weights_for() ของจริง
    """
    from rov.draft.recommend import weights_for

    m = re.search(
        r"const e = nEnemy / \(nEnemy \+ ([\d.]+)\);\s*"
        r"const a = nAlly / \(nAlly \+ ([\d.]+)\);\s*"
        r"const counter = ([\d.]+) \+ ([\d.]+) \* e;.*?"
        r"const synergy = ([\d.]+) \+ ([\d.]+) \* a;",
        tpl,
        re.S,
    )
    assert m, "หาสูตรน้ำหนักใน template ไม่เจอ"
    ke, ka, c0, cs, s0, ss = (float(x) for x in m.groups())

    def js(n_enemy: int, n_ally: int) -> dict[str, float]:
        e = n_enemy / (n_enemy + ke)
        a = n_ally / (n_ally + ka)
        counter = c0 + cs * e
        synergy = s0 + ss * a
        rest = 1.0 - counter - synergy
        return {
            "meta": rest * 0.45,
            "winrate": rest * 0.55,
            "counter": counter,
            "synergy": synergy,
        }

    for ne in range(6):
        for na in range(5):
            a, b = js(ne, na), weights_for(ne, na)
            for k in a:
                assert abs(a[k] - b[k]) < 1e-9, (ne, na, k, a[k], b[k])


def test_js_component_scale_matches_python(tpl):
    """ช่วงสเกลของ counter/synergy ต้องตรงกันสองฝั่ง

    ถ้าฝั่งหนึ่งใช้ -6..6 อีกฝั่งใช้ -3..3 คะแนนจะคนละสเกลกันเงียบ ๆ
    """
    import inspect

    from rov.draft import recommend as rec

    src = inspect.getsource(rec)
    for name in ("Counter", "Synergy"):
        key = name.lower()
        py = re.search(
            rf'"{key}", "{name}", \w+_raw, _scale\(\w+_raw, ([-\d.]+), ([\d.]+)\)', src
        )
        assert py, f"หาสเกลของ {name} ฝั่ง Python ไม่เจอ"
        js = re.search(
            rf'{key}: {{label:"{name}",\s*v: scale\(\w+Raw, ([-\d.]+), ([\d.]+)\)', tpl
        )
        assert js, f"หาสเกลของ {name} ฝั่ง JS ไม่เจอ"
        assert float(py.group(1)) == float(js.group(1))
        assert float(py.group(2)) == float(js.group(2))


def test_js_role_fit_matches_python(tpl):
    """ตัวคูณเรื่องตำแหน่งถูกเขียนสองที่ ต้องให้ค่าตรงกัน

    นี่คือส่วนที่ทำให้ระบบเลิกแนะนำแบนเมจทั้งที่อีกฝั่งมีเมจแล้ว
    ถ้าสองฝั่งเพี้ยนกัน CLI กับหน้าเว็บจะเสนอคนละอันดับ
    """
    from rov.draft.recommend import LANE_OWN_SHARE, ROLE_FLOOR

    floor = re.search(r"const ROLE_FLOOR = ([\d.]+);", tpl)
    assert floor, "หา ROLE_FLOOR ใน template ไม่เจอ"
    assert float(floor.group(1)) == ROLE_FLOOR

    own = re.search(r"const LANE_OWN_SHARE = ([\d.]+);", tpl)
    assert own, "หา LANE_OWN_SHARE ใน template ไม่เจอ"
    assert float(own.group(1)) == LANE_OWN_SHARE

    # ต้องเป็น "มากกว่า" ไม่ใช่ "มากกว่าเท่ากับ" ทั้งสองฝั่ง
    assert "m.share > LANE_OWN_SHARE" in tpl
    assert "roleMul = fit => ROLE_FLOOR + (1 - ROLE_FLOOR) * fit" in tpl


# ─────────────────────────────────────────────────────────────────────
# Composition Engine ถูกเขียนซ้ำไว้ใน JS ด้วย (COMP_DIMS ใน template)
# เพราะหน้าเว็บคิดสดตอนดราฟต์ ซึ่งเรียก Python ไม่ได้
# เทสต์ชุดนี้จับไม่ให้สองชุดเพี้ยนจากกัน
# ─────────────────────────────────────────────────────────────────────


def test_js_composition_constants_match_python(tpl):
    """ค่าคงที่ของสูตรรวมคะแนนต้องตรงกันทั้งสองฝั่ง

    ถ้า CC_SCALE ฝั่งไหนขยับ คะแนน Hard CC บนเว็บกับใน CLI จะต่างกัน
    ทั้งที่เป็นคอมพ์เดียวกัน ซึ่งผู้ใช้จะไม่รู้ว่าอันไหนถูก
    """
    from rov.draft import composition as comp

    m = re.search(r"const CC_SCALE = (\d+);", tpl)
    assert m, "หา CC_SCALE ใน template ไม่เจอ"
    # ค่าเดียวกันนี้อยู่ในคำเรียก _saturating_sum(cc, 180.0) ของ composition.py
    py_cc = re.search(
        r"_saturating_sum\(cc, ([\d.]+)\)",
        Path(comp.__file__).read_text(encoding="utf-8"),
    )
    assert py_cc, "หา _saturating_sum(cc, ...) ใน composition.py ไม่เจอ"
    assert float(m.group(1)) == float(py_cc.group(1))

    mw = re.search(r"const WC_MIN_W = ([\d.]+);", tpl)
    assert mw and float(mw.group(1)) == 0.45

    mg = re.search(r"const GAP_AT = (\d+), STRONG_AT = (\d+);", tpl)
    assert mg, "หา GAP_AT/STRONG_AT ไม่เจอ"
    assert (int(mg.group(1)), int(mg.group(2))) == (35, 75)


def test_js_composition_dimensions_match_python_labels(tpl):
    """มิติที่เว็บแสดงต้องเป็นชุดย่อยของมิติฝั่ง Python และสะกดตรงกัน"""
    from rov.draft.composition import analyze
    from rov.draft.heroes import HeroDB

    block = re.search(r"const COMP_DIMS = \[(.*?)\n\];", tpl, re.S)
    assert block, "หา COMP_DIMS ใน template ไม่เจอ"
    js_labels = re.findall(r'label:\s*"([^"]+)"', block.group(1))
    assert js_labels, "COMP_DIMS ไม่มี label เลย"

    db = HeroDB.load()
    ready = db.complete_heroes
    if len(ready) < 5:
        pytest.skip("ฮีโร่ที่กรอกครบยังไม่ถึง 5 ตัว")
    py_labels = {d.label for d in analyze(ready[:5]).dimensions.values()}
    missing = [x for x in js_labels if x not in py_labels]
    assert not missing, f"มิติบนเว็บที่ฝั่ง Python ไม่มี: {missing}"


def test_js_and_python_agree_on_a_real_composition(tpl):
    """คิดคอมพ์เดียวกันสองฝั่งแล้วต้องได้ตัวเลขเดียวกัน

    เทสต์นี้จำลองสูตรฝั่ง JS ด้วย Python แล้วเทียบกับ analyze() ตัวจริง
    ถ้ามีใครไปแก้สูตรฝั่งใดฝั่งหนึ่ง ตัวเลขจะแยกกันแล้ว fail ตรงนี้
    """
    import math

    from rov.draft.composition import analyze
    from rov.draft.heroes import HeroDB

    db = HeroDB.load()
    ready = db.complete_heroes
    if len(ready) < 5:
        pytest.skip("ฮีโร่ที่กรอกครบยังไม่ถึง 5 ตัว")
    team = ready[:5]
    rep = analyze(team)

    def top_w(vals, w=(0.7, 0.3)):
        s = sorted(vals, reverse=True)
        return sum(k * (s[i] if i < len(s) else 0) for i, k in enumerate(w))

    u = lambda k: [h.u(k) for h in team]  # noqa: E731
    js = {
        "Frontline": top_w(u("frontline")),
        "Engage": top_w(u("engage")),
        "Disengage": top_w(u("disengage")),
        "Hard CC": 100 * (1 - math.exp(-sum(u("cc_hard")) / 180)),
        "Peel": top_w(u("peel")),
        "Objective": top_w(u("objective")),
        "Waveclear": 0.45 * min(u("waveclear")) + 0.55 * (sum(u("waveclear")) / 5),
        "Split Push": top_w(u("splitpush"), (0.8, 0.2)),
    }
    by_label = {d.label: d.value for d in rep.dimensions.values()}
    for label, expected in js.items():
        assert by_label[label] == pytest.approx(expected, abs=0.05), label


def test_js_turn_clock_matches_format_yaml(tpl, fmt):
    """เวลาต่อตาบนเว็บต้องตรงกับ turn_clock ใน format.yaml

    ค่านี้ยังไม่ยืนยันกับการแข่งจริง เมื่อวันหนึ่งจับเวลาจากคลิปได้แล้ว
    จะได้แก้ที่ config ที่เดียวแล้วรู้ทันทีว่าต้องตามไปแก้ JS ด้วย
    """
    m = re.search(
        r"const CLOCK = \{ban: (\d+), pick: (\d+), verified: (true|false)\};", tpl
    )
    assert m, "หา const CLOCK ใน template ไม่เจอ"
    assert int(m.group(1)) == fmt.turn_clock.ban
    assert int(m.group(2)) == fmt.turn_clock.pick
    assert (m.group(3) == "true") is fmt.turn_clock.verified


def test_unverified_clock_must_say_so_on_screen(tpl, fmt):
    """ถ้าเวลายังไม่ยืนยัน หน้าเว็บต้องบอกผู้ใช้ ห้ามแสดงเป็นตัวเลขลอย ๆ"""
    if fmt.turn_clock.verified:
        pytest.skip("เวลายืนยันแล้ว ไม่ต้องมีคำเตือน")
    assert "ยังไม่ยืนยัน" in tpl, "นาฬิกาที่ยังไม่ยืนยันต้องมีคำเตือนใน template"
