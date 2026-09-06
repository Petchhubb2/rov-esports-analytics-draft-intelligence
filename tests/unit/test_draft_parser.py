"""ทดสอบตัวแยก wikitext และ draft parser

ใช้ fixture ที่คัดมาจากข้อมูลจริงของ RoV Pro League 2026 Summer
จึงรันได้โดยไม่ต้องต่อเน็ตและไม่กินโควตา API
"""

from __future__ import annotations

from pathlib import Path

import pytest
from rov.draft.importer.parser import (
    BANS_PER_TEAM,
    PICKS_PER_TEAM,
    parse_page,
    summarize,
)
from rov.draft.importer.wikitext import (
    find_templates,
    iter_nested,
    parse_template,
    strip_comments,
)

FIXTURE = Path("tests/fixtures/liquipedia_rpl_sample.wikitext")


@pytest.fixture(scope="module")
def wikitext() -> str:
    return FIXTURE.read_text(encoding="utf-8")


# ------------------------------------------------------------------ wikitext


def test_strip_comments_removes_html_comments():
    assert strip_comments("a<!-- x -->b") == "ab"
    assert strip_comments("a<!-- ไม่ปิด") == "a"
    assert strip_comments("ไม่มีอะไร") == "ไม่มีอะไร"


def test_parse_simple_template():
    t = parse_template("{{Map|winner=1|length=11:58}}")
    assert t.name == "Map"
    assert t.get("winner") == "1"
    assert t.get("length") == "11:58"


def test_positional_parameters():
    t = parse_template("{{TeamOpponent|fs}}")
    assert t.positional == ["fs"]


def test_pipe_inside_nested_template_is_not_a_separator():
    """เหตุผลที่ต้องเขียน parser เอง แทนการ split ด้วย |"""
    raw = "{{Match|opponent1={{TeamOpponent|fs|extra={{Sub|a|b}}}}|bestof=5}}"
    t = parse_template(raw)
    assert t.get("bestof") == "5"
    assert t.get("opponent1").startswith("{{TeamOpponent")
    assert "fs" in t.get("opponent1")


def test_sub_returns_nested_template():
    t = parse_template("{{Match|opponent1={{TeamOpponent|godji check}}}}")
    sub = t.sub("opponent1")
    assert sub is not None
    assert sub.name == "TeamOpponent"
    assert sub.positional == ["godji check"]


def test_iter_nested_finds_deeply_nested():
    raw = "{{Match|map1={{Map|t1h1=skud}}|map2={{Map|t1h1=murad}}}}"
    maps = iter_nested(raw, "Map")
    assert len(maps) == 2
    assert maps[0].get("t1h1") == "skud"
    assert maps[1].get("t1h1") == "murad"


def test_iter_nested_does_not_match_similar_names():
    """Match ต้องไม่ไปจับ Matchlist"""
    raw = "{{Matchlist|id=x}}{{Match|bestof=3}}"
    found = iter_nested(raw, "Match")
    assert len(found) == 1
    assert found[0].get("bestof") == "3"


def test_unbalanced_braces_do_not_hang():
    assert find_templates("{{Broken|a=1") == []


# --------------------------------------------------------------- draft parser


def test_parses_expected_number_of_series(wikitext):
    series = parse_page(wikitext)
    assert len(series) == 2


def test_first_series_teams_and_format(wikitext):
    s = parse_page(wikitext)[0]
    assert s.team1 == "fs"
    assert s.team2 == "godji check"
    assert s.best_of == 5
    assert s.date is not None


def test_game_one_draft_matches_source(wikitext):
    """ตรวจกับค่าที่อ่านจาก wikitext จริงทีละตัว"""
    g = parse_page(wikitext)[0].games[0]
    assert g.blue_team == "fs"
    assert g.red_team == "godji check"
    assert g.winner_team == "fs"
    assert g.blue_picks == ["skud", "billow", "rouie", "hayate", "toro"]
    assert g.red_picks == ["murad", "keera", "lorion", "wisp", "y'bneth"]
    assert g.blue_bans == ["annette", "eland'orr", "qi", "florentino"]
    assert g.red_bans == ["sinestrea", "zata", "mganga", "marja"]


def test_side_swap_is_read_per_game_not_assumed(wikitext):
    """opponent1 ไม่เท่ากับ blue เสมอ — เกม 2 สลับฝั่ง

    ถ้าอ่านผิดตรงนี้ สถิติ blue-side win rate จะผิดทั้งหมด
    """
    games = parse_page(wikitext)[0].games
    assert games[0].blue_team == "fs"
    assert games[1].blue_team == "godji check", "เกม 2 ต้องสลับฝั่ง"
    assert games[1].red_team == "fs"
    # ผู้ชนะยังเป็น fs เหมือนเดิม แม้จะย้ายไปฝั่งแดง
    assert games[1].winner_team == "fs"
    assert games[1].red_picks == ["taara", "zephys", "mganga", "stuart", "dolia"]


def test_length_parsed_to_seconds(wikitext):
    g = parse_page(wikitext)[0].games[0]
    assert g.length_sec == 718  # 11:58


def test_counts_match_confirmed_format(wikitext):
    """ยืนยันจากข้อมูลจริง: แบน 4 ตัวต่อทีม เลือก 5 ตัวต่อทีม"""
    for s in parse_page(wikitext):
        for g in s.complete_games:
            assert len(g.blue_picks) == PICKS_PER_TEAM
            assert len(g.red_picks) == PICKS_PER_TEAM
            assert len(g.blue_bans) == BANS_PER_TEAM
            assert len(g.red_bans) == BANS_PER_TEAM


def test_empty_placeholder_games_are_marked_incomplete(wikitext):
    """ซีรีส์ Bo5 ที่จบ 3-0 ยังมี map4/map5 ว่างอยู่ ต้องไม่นับเป็นเกมจริง"""
    s = parse_page(wikitext)[0]
    assert len(s.games) > len(s.complete_games)
    for g in s.games:
        if not g.complete:
            assert g.blue_picks == [] or g.winner_team is None


def test_no_hero_appears_on_both_sides_in_one_game(wikitext):
    """ฮีโร่ตัวเดียวกันอยู่สองฝั่งพร้อมกันไม่ได้ — ตรวจว่า parser ไม่สลับข้อมูล"""
    for s in parse_page(wikitext):
        for g in s.complete_games:
            assert not (set(g.blue_picks) & set(g.red_picks))


def test_banned_hero_is_not_picked_in_same_game(wikitext):
    for s in parse_page(wikitext):
        for g in s.complete_games:
            banned = set(g.blue_bans) | set(g.red_bans)
            assert not (banned & set(g.blue_picks))
            assert not (banned & set(g.red_picks))


def test_global_ban_pick_rule_holds_on_real_data(wikitext):
    """ทีมห้ามใช้ฮีโร่ที่ตัวเองเคยเลือกในซีรีส์เดียวกัน

    เป็นการตรวจสองทางพร้อมกัน: ยืนยันว่า parser จับคู่ทีมกับ pick ถูก
    และยืนยันว่ารายการนี้ใช้กติกา Global Ban-Pick จริง
    (docs/08-game-reference.md §7)
    """
    for s in parse_page(wikitext):
        assert s.global_ban_pick_check() == []


def test_summary_counts(wikitext):
    s = summarize(parse_page(wikitext))
    assert s.series == 2
    assert s.complete_games >= 5
    assert len(s.heroes) > 20
    assert "fs" in s.teams


def test_summary_report_is_printable(wikitext):
    text = summarize(parse_page(wikitext)).report()
    assert "ซีรีส์" in text
    assert "เกมที่ข้อมูลครบ" in text
