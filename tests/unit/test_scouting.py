"""ทดสอบ scouting ต่อทีม — rov/draft/scouting.py

ใช้ข้อมูลที่สร้างขึ้นเองทั้งหมด ไม่แตะ cache จริง เพื่อให้เทสต์ไม่พึ่งเครือข่าย
และไม่พังเมื่อข้อมูลใน cache เปลี่ยน
"""

from __future__ import annotations

from datetime import date

import pytest
from rov.domain.enums import LaneRole
from rov.draft.importer.parser import GameDraft, SeriesDraft
from rov.draft.scouting import (
    MIN_TEAM_GAMES,
    NARROW_SHARE,
    date_range,
    filter_since,
    find_team,
    parse_date,
    report,
    target_bans,
    team_profiles,
)


def game(idx, blue, red, blue_picks, red_picks, winner, blue_bans=None, red_bans=None):
    return GameDraft(
        game_index=idx,
        blue_team=blue,
        red_team=red,
        winner_team=winner,
        blue_picks=list(blue_picks),
        red_picks=list(red_picks),
        blue_bans=list(blue_bans or []),
        red_bans=list(red_bans or []),
        length_sec=900.0,
    )


# ช่องเรียงตามเลน: ds, jungle, mid, dragon, support
A_PICKS = ["marja", "tachi", "lorion", "capheny", "toro"]
B_PICKS = ["qi", "billow", "annette", "hayate", "ybneth"]


def series(team1, team2, n_games, date_str, winner=None):
    games = [
        game(i, team1, team2, A_PICKS, B_PICKS, winner or team1)
        for i in range(1, n_games + 1)
    ]
    return SeriesDraft(team1=team1, team2=team2, best_of=n_games, date=date_str, games=games)


# ------------------------------------------------------------------ วันที่


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("January 31, 2026 - 12:00 {{Abbr/ICT}}", date(2026, 1, 31)),
        ("September 6, 2025", date(2025, 9, 6)),
        ("May 1, 2026 - 15:00", date(2026, 5, 1)),
    ],
)
def test_parse_date_reads_liquipedia_format(raw, expected):
    assert parse_date(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "เร็ว ๆ นี้", "2026-01-31", "Foobruary 3, 2026"])
def test_parse_date_returns_none_instead_of_guessing(raw):
    """อ่านไม่ออกต้องคืน None ห้ามเดาเป็นวันนี้

    ถ้าเดา ตัวถ่วงตามความใหม่จะผิดแบบเงียบ ๆ ซึ่งหาไม่เจอตอนใช้งาน
    """
    assert parse_date(raw) is None


def test_filter_since_drops_series_without_a_date():
    keep = series("a", "b", 2, "June 1, 2026")
    old = series("a", "b", 2, "January 1, 2026")
    undated = series("a", "b", 2, None)
    out = filter_since([keep, old, undated], date(2026, 5, 1))
    assert out == [keep]


def test_date_range_ignores_unparsable_dates():
    lo, hi = date_range(
        [series("a", "b", 1, "March 3, 2026"), series("a", "b", 1, None)]
    )
    assert (lo, hi) == (date(2026, 3, 3), date(2026, 3, 3))


# ------------------------------------------------------------------ โปรไฟล์


def test_team_profile_counts_games_wins_and_side():
    profs = team_profiles([series("aaa", "bbb", 4, "June 1, 2026", winner="aaa")])
    a, b = profs["aaa"], profs["bbb"]
    assert a.games == 4 and a.wins == 4
    assert b.games == 4 and b.wins == 0
    # ทีม 1 อยู่ฝั่งน้ำเงินทุกเกมในของจำลองชุดนี้
    assert a.blue_games == 4 and a.blue_wins == 4
    assert b.blue_games == 0


def test_lane_pool_follows_roster_slot_order():
    profs = team_profiles([series("aaa", "bbb", 3, "June 1, 2026")])
    a = profs["aaa"]
    assert a.lane_pool(LaneRole.DS).most_common(1) == [("marja", 3)]
    assert a.lane_pool(LaneRole.JUNGLE).most_common(1) == [("tachi", 3)]
    assert a.lane_pool(LaneRole.DRAGON).most_common(1) == [("capheny", 3)]


def test_incomplete_games_are_excluded():
    """เกมที่ช่องไม่ครบ 5 ต้องไม่เข้าโปรไฟล์

    ถ้าปล่อยเข้า parser จะเลื่อนช่องชิดกันแล้วเลนเพี้ยนทั้งชุด
    """
    bad = game(1, "aaa", "bbb", ["marja", "tachi"], B_PICKS, "aaa")
    s = SeriesDraft(team1="aaa", team2="bbb", best_of=1, date="June 1, 2026", games=[bad])
    assert team_profiles([s]) == {}


def test_narrowness_flags_a_one_trick_lane():
    profs = team_profiles([series("aaa", "bbb", MIN_TEAM_GAMES + 2, "June 1, 2026")])
    a = profs["aaa"]
    share, n_heroes, n_games = a.narrowness(LaneRole.JUNGLE)
    assert n_heroes == 1
    assert share == pytest.approx(1.0)
    assert LaneRole.JUNGLE in [lane for lane, *_ in a.narrow_lanes()]


def test_narrow_lanes_needs_enough_games():
    """ทีมที่เล่นแค่ 2 เกมต้องไม่ถูกสรุปว่า pool แคบ"""
    profs = team_profiles([series("aaa", "bbb", 2, "June 1, 2026")])
    assert profs["aaa"].narrow_lanes() == []
    assert not profs["aaa"].reliable


def test_find_team_is_case_insensitive_and_refuses_ambiguity():
    profs = team_profiles(
        [series("Alpha", "Alpine", 6, "June 1, 2026")]
    )
    assert find_team(profs, "alpha").team == "Alpha"
    # "alp" ตรงทั้งสองทีม ต้องคืน None ไม่ใช่เดาเอาตัวแรก
    assert find_team(profs, "alp") is None


# ------------------------------------------------------------------ target ban


def test_target_bans_prefers_heroes_the_team_over_uses():
    """ตัวที่ทีมหยิบบ่อยกว่าลีกมาก ต้องได้อันดับสูงกว่าตัวที่ลีกก็หยิบพอกัน"""
    profs = team_profiles([series("aaa", "bbb", 10, "June 1, 2026")])
    league = {"marja": 0.50, "tachi": 0.05, "lorion": 0.50, "capheny": 0.50, "toro": 0.50}
    out = target_bans(profs["aaa"], league)
    assert out[0].hero_id == "tachi"
    assert out[0].lift > 1.0
    assert out[0].lane is LaneRole.JUNGLE


def test_target_bans_ignores_rarely_picked_heroes():
    """หยิบน้อยกว่าเกณฑ์ต้องไม่ขึ้นมา แม้ lift จะสูงลิ่ว

    lift ของตัวอย่างขนาดเล็กเป็นสัญญาณรบกวนล้วน ๆ
    """
    profs = team_profiles([series("aaa", "bbb", 10, "June 1, 2026")])
    out = target_bans(profs["aaa"], {}, min_team_picks=999)
    assert out == []


def test_target_bans_respects_exclude():
    profs = team_profiles([series("aaa", "bbb", 10, "June 1, 2026")])
    out = target_bans(profs["aaa"], {}, exclude={"tachi"})
    assert all(t.hero_id != "tachi" for t in out)


def test_target_bans_on_empty_profile_is_empty():
    profs = team_profiles([series("aaa", "bbb", 10, "June 1, 2026")])
    p = profs["aaa"]
    p.games = 0
    assert target_bans(p, {}) == []


# ------------------------------------------------------------------ รายงาน


def test_report_always_states_the_team_level_limitation():
    """รายงานต้องบอกข้อจำกัดเสมอ ตามหลัก 'ระบบต้องบอกว่าไม่รู้'"""
    profs = team_profiles([series("aaa", "bbb", 8, "June 1, 2026")])
    text = report(profs["aaa"], target_bans(profs["aaa"], {}))
    assert "ไม่ใช่ระดับผู้เล่น" in text
    assert "8 เกม" in text


def test_report_warns_when_sample_is_too_small():
    profs = team_profiles([series("aaa", "bbb", 2, "June 1, 2026")])
    assert "ยังสรุปสไตล์ไม่ได้" in report(profs["aaa"])


def test_narrow_share_threshold_is_documented_constant():
    """กันไม่ให้ใครแอบขยับเกณฑ์โดยไม่ตั้งใจ"""
    assert 0.5 < NARROW_SHARE < 1.0


def test_date_range_ignores_matches_not_yet_played():
    """Liquipedia ลงตารางล่วงหน้า — วันของนัดที่ยังไม่แข่งต้องไม่ลากช่วงไปอนาคต

    ถ้านับรวม หน้าต่าง "N วันล่าสุด" จะเลื่อนตามอนาคตแล้วกินแมตช์จริงน้อยลง
    """
    played = series("a", "b", 2, "June 1, 2026")
    scheduled = SeriesDraft(
        team1="a", team2="b", best_of=3, date="December 31, 2026", games=[]
    )
    assert date_range([played, scheduled]) == (date(2026, 6, 1), date(2026, 6, 1))
    assert date_range([played, scheduled], played_only=False)[1] == date(2026, 12, 31)
