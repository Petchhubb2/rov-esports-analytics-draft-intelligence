"""ทดสอบการเทียบเมต้าข้ามลีกและการรวมข้อมูล"""

from __future__ import annotations

import pytest
from rov.draft.importer.crawl import normalize_title
from rov.draft.importer.parser import GameDraft, SeriesDraft
from rov.draft.meta import Region, compare_regions, counter_report, pool, top_counters


def _game(idx: int, blue: list[str], red: list[str], winner_blue: bool, length=900.0):
    return GameDraft(
        game_index=idx,
        blue_team="A",
        red_team="B",
        winner_team="A" if winner_blue else "B",
        blue_picks=blue,
        red_picks=red,
        blue_bans=[],
        red_bans=[],
        length_sec=length,
    )


def _series(games: list[GameDraft]) -> SeriesDraft:
    return SeriesDraft(team1="A", team2="B", best_of=len(games), date=None, games=games)


FIVE_A = ["a1", "a2", "a3", "a4", "a5"]
FIVE_B = ["b1", "b2", "b3", "b4", "b5"]


# ----------------------------------------------------------- normalize title


def test_underscore_and_space_are_the_same_page():
    """MediaWiki ถือว่าเหมือนกัน ถ้าไม่รวมจะดึงหน้าเดียวกันสองครั้ง เปลืองโควตา"""
    assert normalize_title("A/Regular_Season") == normalize_title("A/Regular Season")


def test_first_letter_is_capitalised():
    assert normalize_title("garena/x") == "Garena/x"


def test_repeated_spaces_collapse():
    assert normalize_title("a  b___c") == "A b c"


# ------------------------------------------------------------------- region


def test_region_computes_lazily_and_caches():
    r = Region("TH", "ไทย", [_series([_game(1, FIVE_A, FIVE_B, True)])])
    assert r.stats is None
    s1 = r.compute()
    assert s1.total_games == 1
    assert r.compute() is s1


# -------------------------------------------------------------- comparison


def test_presence_difference_is_detected():
    """ฮีโร่ที่เล่นเฉพาะภูมิภาคเดียวต้องถูกจับได้"""
    th = Region("TH", "ไทย", [_series([_game(i, FIVE_A, FIVE_B, True) for i in range(1, 11)])])
    tw_a = ["x1", "a2", "a3", "a4", "a5"]
    tw = Region("TW", "ไต้หวัน", [_series([_game(i, tw_a, FIVE_B, True) for i in range(1, 11)])])

    diffs = {d.hero_id: d for d in compare_regions(th, tw)}
    assert diffs["a1"].presence_delta == pytest.approx(1.0)
    assert diffs["x1"].presence_delta == pytest.approx(-1.0)
    assert diffs["a2"].presence_delta == pytest.approx(0.0)


def test_comparison_sorted_by_absolute_difference():
    th = Region("TH", "ไทย", [_series([_game(i, FIVE_A, FIVE_B, True) for i in range(1, 11)])])
    tw = Region("TW", "ไต้หวัน", [
        _series([_game(i, ["x1", "a2", "a3", "a4", "a5"], FIVE_B, True) for i in range(1, 11)])
    ])
    diffs = compare_regions(th, tw)
    mags = [abs(d.presence_delta) for d in diffs]
    assert mags == sorted(mags, reverse=True)


def test_low_presence_heroes_are_filtered_out():
    big = [_game(i, FIVE_A, FIVE_B, True) for i in range(1, 100)]
    big.append(_game(100, ["rare", "a2", "a3", "a4", "a5"], FIVE_B, True))
    th = Region("TH", "ไทย", [_series(big)])
    tw = Region("TW", "ไต้หวัน", [_series([_game(1, FIVE_A, FIVE_B, True)])])
    ids = {d.hero_id for d in compare_regions(th, tw, min_presence=0.05)}
    assert "rare" not in ids
    assert "a1" in ids


def test_both_reliable_flag():
    th = Region("TH", "ไทย", [_series([_game(i, FIVE_A, FIVE_B, True) for i in range(1, 21)])])
    tw = Region("TW", "ไต้หวัน", [_series([_game(1, FIVE_A, FIVE_B, True)])])
    d = next(d for d in compare_regions(th, tw) if d.hero_id == "a1")
    assert d.games_a == 20
    assert d.games_b == 1
    assert not d.both_reliable


# ------------------------------------------------------------------- pool


def test_pool_sums_games_across_regions():
    th = Region("TH", "ไทย", [_series([_game(i, FIVE_A, FIVE_B, True) for i in range(1, 6)])])
    tw = Region("TW", "ไต้หวัน", [_series([_game(i, FIVE_A, FIVE_B, False) for i in range(1, 4)])])
    p = pool([th, tw])
    assert p.total_games == 8
    assert p.games_by_source == {"ไทย": 5, "ไต้หวัน": 3}
    assert len(p.sources) == 2


def test_pooling_gives_matchups_more_samples():
    """เหตุผลหลักของการรวมข้อมูล — คู่ที่เจอกันน้อยจะมีตัวอย่างพอเร็วขึ้น"""
    th = Region("TH", "ไทย", [_series([_game(i, FIVE_A, FIVE_B, True) for i in range(1, 6)])])
    tw = Region("TW", "ไต้หวัน", [_series([_game(i, FIVE_A, FIVE_B, True) for i in range(1, 6)])])
    solo = pool([th]).matchups[("a1", "b1")].games
    both = pool([th, tw]).matchups[("a1", "b1")].games
    assert both == solo * 2


# --------------------------------------------------------------- counters


def test_counters_split_into_good_and_bad():
    games = []
    # a1 ชนะ b1 บ่อย และแพ้ b2 บ่อย
    for i in range(1, 41):
        games.append(_game(i, FIVE_A, ["b1", "z", "z2", "z3", "z4"], True))
    for i in range(41, 81):
        games.append(_game(i, FIVE_A, ["b2", "z", "z2", "z3", "z4"], False))
    p = pool([Region("X", "x", [_series(games)])])
    good, bad = top_counters(p, "a1", min_games=10)
    assert good[0][0] == "b1"
    assert good[0][2] > 0
    assert bad[0][0] == "b2"
    assert bad[0][2] < 0


def test_counters_respect_min_games():
    games = [_game(i, FIVE_A, FIVE_B, True) for i in range(1, 6)]
    p = pool([Region("X", "x", [_series(games)])])
    assert top_counters(p, "a1", min_games=50) == ([], [])


def test_counter_report_states_its_limitation():
    """ต้องบอกชัดว่าเป็น context=TEAM ไม่ใช่การดวลกันในเลน"""
    games = [_game(i, FIVE_A, FIVE_B, True) for i in range(1, 31)]
    p = pool([Region("X", "x", [_series(games)])])
    text = counter_report(p, "a1", min_games=10)
    assert "context=TEAM" in text
    assert "เลนเดียวกัน" in text
