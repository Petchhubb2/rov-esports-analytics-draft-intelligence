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
