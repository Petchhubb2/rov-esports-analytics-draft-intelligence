"""แปลง wikitext ของ Liquipedia เป็นข้อมูล draft ที่ใช้งานได้

รูปแบบจริงที่ตรวจสอบแล้วจากหน้า RoV Pro League/2026/Summer/Group Stage

    {{Match
      |bestof=5
      |date=January 31, 2026 - 12:00 {{Abbr/ICT}}
      |opponent1={{TeamOpponent|fs}}
      |opponent2={{TeamOpponent|godji check}}
      |map1={{Map|team1side=blue|team2side=red|length=11:58|winner=1
        |t1h1=skud|t1h2=billow|t1h3=rouie|t1h4=hayate|t1h5=toro
        |t2h1=murad|t2h2=keera|t2h3=lorion|t2h4=wisp|t2h5=y'bneth
        |t1b1=annette|t1b2=eland'orr|t1b3=qi|t1b4=florentino
        |t2b1=sinestrea|t2b2=zata|t2b3=mganga|t2b4=marja
      }}
    }}

ข้อเท็จจริงที่ยืนยันจากข้อมูลจริง
  - แบน 4 ตัวต่อทีม รวม 8 ตัวต่อเกม
  - เลือก 5 ตัวต่อทีม
  - ฝั่ง blue/red สลับได้ในแต่ละเกมของซีรีส์เดียวกัน

ข้อจำกัดที่ต้องรู้: Liquipedia เก็บ ban เป็นช่องของแต่ละทีม (t1b1..t1b4)
ไม่ได้เก็บลำดับการสลับกันแบนระหว่างสองทีม จึงสร้าง turn_order ที่แท้จริงไม่ได้
ต้องถือว่าลำดับภายในทีมถูกต้อง แต่การสลับระหว่างทีมเป็นการประมาณ
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rov.draft.importer.wikitext import Template, iter_nested

BANS_PER_TEAM = 4
PICKS_PER_TEAM = 5


@dataclass(slots=True)
class GameDraft:
    """หนึ่งเกมในซีรีส์"""

    game_index: int
    blue_team: str | None
    red_team: str | None
    winner_team: str | None
    blue_picks: list[str] = field(default_factory=list)
    red_picks: list[str] = field(default_factory=list)
    blue_bans: list[str] = field(default_factory=list)
    red_bans: list[str] = field(default_factory=list)
    length_sec: float | None = None
    vod: str | None = None

    @property
    def complete(self) -> bool:
        """ข้อมูลครบพอจะใช้ทำสถิติหรือไม่"""
        return (
            len(self.blue_picks) == PICKS_PER_TEAM
            and len(self.red_picks) == PICKS_PER_TEAM
            and self.winner_team is not None
        )

    def all_heroes(self) -> set[str]:
        return set(self.blue_picks) | set(self.red_picks)


@dataclass(slots=True)
class SeriesDraft:
    """หนึ่งซีรีส์ (Bo1/Bo3/Bo5)"""

    team1: str | None
    team2: str | None
    best_of: int | None
    date: str | None
    games: list[GameDraft] = field(default_factory=list)

    @property
    def complete_games(self) -> list[GameDraft]:
        return [g for g in self.games if g.complete]

    def global_ban_pick_check(self) -> list[str]:
        """ตรวจกติกา Global Ban-Pick — ทีมห้ามใช้ฮีโร่ที่ตัวเองเคยเลือกในซีรีส์

        ดู docs/08-game-reference.md §7
        คืนรายการที่ผิดกติกา ถ้าว่างแปลว่าข้อมูลสอดคล้องกับกติกา
        ใช้ตรวจว่า parser อ่านถูกหรือไม่ และตรวจว่ารายการนั้นใช้กติกานี้จริง
        """
        problems: list[str] = []
        used: dict[str, set[str]] = {}
        for g in self.games:
            for team, picks in ((g.blue_team, g.blue_picks), (g.red_team, g.red_picks)):
                if not team:
                    continue
                seen = used.setdefault(team, set())
                repeated = seen & set(picks)
                if repeated:
                    problems.append(
                        f"เกม {g.game_index}: ทีม {team} ใช้ซ้ำ {sorted(repeated)}"
                    )
                seen |= set(picks)
        return problems


def _length_to_sec(raw: str | None) -> float | None:
    if not raw:
        return None
    m = re.fullmatch(r"\s*(\d+):(\d{2})\s*", raw)
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def _team_name(tpl: Template | None) -> str | None:
    """ดึงชื่อทีมจาก {{TeamOpponent|ชื่อทีม|...}}"""
    if tpl is None:
        return None
    for p in tpl.positional:
        cleaned = p.strip()
        if cleaned and "{{" not in cleaned and "=" not in cleaned:
            return cleaned
    return None


# ชื่อที่หน้าแมตช์เขียนต่างจากชื่อหลัก จนกติกาข้างบนรวมให้ไม่ได้
#
# ทุกบรรทัดมีหลักฐานจากข้อมูลจริง 861 เกม และจากหน้า
# Portal:Heroes/Arena of Valor ของ Liquipedia ห้ามเติมโดยเดา
#
#   flw_mm      37 pick   Portal เขียนว่า "Flowborn/Marksman"
#                         หน้าแมตช์ย่อเหลือแค่ MM จึงจับคู่กันไม่ติด
#   sikong       1 pick   คือตัวเดียวกับ bolt_baron (44 pick)
#                         Portal: link=Sikong Zhen แสดงผลว่า Bolt Baron
#   diaochan     1 pick   คู่กับ diao_chan (2 pick)
#   lubu         2 pick   คู่กับ lu_bu (2 pick)
#
# เลือก id หลักตามไฟล์รูปใน data/assets/heroes/_manifest.json
# เพราะกระดานเว็บหารูปจาก id นี้โดยตรง
#
# ⚠️ Flowborn มีสองร่าง (Mage / Marksman) ที่ Portal นับเป็นคนละตัว
#    ข้อมูลที่มีตอนนี้มีแต่ร่าง Marksman จึงรวมเข้า flowborn ได้
#    ถ้าวันหนึ่งเห็นร่าง Mage โผล่มา มันจะกลายเป็น id ที่ไม่รู้จัก
#    แล้วโผล่ใน rov draft heroes-init — ตอนนั้นต้องแยก id ใหม่ให้มัน
HERO_ALIASES: dict[str, str] = {
    "flw_mm": "flowborn",
    "flowborn/marksman": "flowborn",
    "sikong": "sikong_zhen",
    "bolt_baron": "sikong_zhen",
    "diaochan": "diao_chan",
    "lubu": "lu_bu",
}


def normalize_hero_id(raw: str) -> str:
    """ทำชื่อฮีโร่ให้เป็นรูปแบบเดียว

    จำเป็นเพราะข้อมูลใน Liquipedia เขียนชื่อเดียวกันได้หลายแบบ
    ตรวจพบจริงในชุด RPL 2026 Summer

        eland'orr (2 pick) กับ elandorr (82 pick)  = ฮีโร่ตัวเดียวกัน
        y'bneth   (3 pick) กับ ybneth   (83 pick)  = ฮีโร่ตัวเดียวกัน

    ถ้าไม่รวมกัน สถิติจะถูกแยกเป็นสองก้อนแบบเงียบ ๆ
    และฮีโร่ที่ถูกแบนบ่อยที่สุดจะดูเหมือนถูกแบนน้อยกว่าความจริง

    กติกา: ตัวพิมพ์เล็ก · ตัด ' . - ทิ้ง · ช่องว่างเป็น _
    จากนั้นส่งผ่านตารางชื่อพ้อง HERO_ALIASES อีกชั้น
    """
    s = raw.strip().lower()
    for ch in ("'", "’", ".", "-"):
        s = s.replace(ch, "")
    s = "_".join(s.split())
    return HERO_ALIASES.get(s, s)


def _slots(tpl: Template, prefix: str, count: int) -> list[str]:
    """ดึงค่าจากช่องที่เรียงเลข เช่น t1h1..t1h5 — ข้ามช่องที่ว่าง"""
    out: list[str] = []
    for i in range(1, count + 1):
        v = normalize_hero_id(tpl.get(f"{prefix}{i}") or "")
        if v:
            out.append(v)
    return out


def parse_map(tpl: Template, index: int, team1: str | None, team2: str | None) -> GameDraft:
    side1 = (tpl.get("team1side") or "").strip().lower()
    side2 = (tpl.get("team2side") or "").strip().lower()

    t1_picks = _slots(tpl, "t1h", PICKS_PER_TEAM)
    t2_picks = _slots(tpl, "t2h", PICKS_PER_TEAM)
    t1_bans = _slots(tpl, "t1b", BANS_PER_TEAM)
    t2_bans = _slots(tpl, "t2b", BANS_PER_TEAM)

    # opponent1/2 ไม่ได้แปลว่า blue/red — ต้องอ่านจาก team1side ของแต่ละเกม
    if side1 == "red" or side2 == "blue":
        blue_team, red_team = team2, team1
        blue_picks, red_picks = t2_picks, t1_picks
        blue_bans, red_bans = t2_bans, t1_bans
    else:
        blue_team, red_team = team1, team2
        blue_picks, red_picks = t1_picks, t2_picks
        blue_bans, red_bans = t1_bans, t2_bans

    winner_raw = (tpl.get("winner") or "").strip()
    winner_team = None
    if winner_raw == "1":
        winner_team = team1
    elif winner_raw == "2":
        winner_team = team2

    return GameDraft(
        game_index=index,
        blue_team=blue_team,
        red_team=red_team,
        winner_team=winner_team,
        blue_picks=blue_picks,
        red_picks=red_picks,
        blue_bans=blue_bans,
        red_bans=red_bans,
        length_sec=_length_to_sec(tpl.get("length")),
        vod=tpl.get("vod"),
    )


def parse_match(tpl: Template) -> SeriesDraft:
    team1 = _team_name(tpl.sub("opponent1"))
    team2 = _team_name(tpl.sub("opponent2"))

    best_of = None
    if (raw := tpl.get("bestof")) and raw.isdigit():
        best_of = int(raw)

    series = SeriesDraft(
        team1=team1, team2=team2, best_of=best_of, date=tpl.get("date")
    )

    idx = 1
    while (raw_map := tpl.get(f"map{idx}")) is not None:
        maps = iter_nested(raw_map, "Map")
        if maps:
            series.games.append(parse_map(maps[0], idx, team1, team2))
        idx += 1
        if idx > 9:  # กันวนไม่รู้จบถ้าข้อมูลผิดรูป
            break
    return series


def parse_page(wikitext: str) -> list[SeriesDraft]:
    """แยกทุกซีรีส์จากหน้าหนึ่งหน้า"""
    return [parse_match(t) for t in iter_nested(wikitext, "Match")]


# --------------------------------------------------------------------------


@dataclass
class ImportSummary:
    series: int = 0
    games: int = 0
    complete_games: int = 0
    heroes: set[str] = field(default_factory=set)
    teams: set[str] = field(default_factory=set)
    rule_violations: list[str] = field(default_factory=list)

    def report(self) -> str:
        lines = [
            f"ซีรีส์           {self.series}",
            f"เกมทั้งหมด        {self.games}",
            f"เกมที่ข้อมูลครบ    {self.complete_games}",
            f"ฮีโร่ที่พบ         {len(self.heroes)}",
            f"ทีมที่พบ          {len(self.teams)}",
        ]
        if self.rule_violations:
            lines.append(
                f"\nขัดกติกา Global Ban-Pick {len(self.rule_violations)} รายการ "
                "(อาจเป็นรายการที่ไม่ได้ใช้กติกานี้ หรือ parser อ่านผิด):"
            )
            lines.extend(f"  · {v}" for v in self.rule_violations[:8])
        return "\n".join(lines)


def summarize(all_series: list[SeriesDraft]) -> ImportSummary:
    s = ImportSummary(series=len(all_series))
    for series in all_series:
        s.games += len(series.games)
        s.complete_games += len(series.complete_games)
        for t in (series.team1, series.team2):
            if t:
                s.teams.add(t)
        for g in series.games:
            s.heroes |= g.all_heroes()
            s.heroes |= set(g.blue_bans) | set(g.red_bans)
        s.rule_violations.extend(series.global_ban_pick_check())
    return s
