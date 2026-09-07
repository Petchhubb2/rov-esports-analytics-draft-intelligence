"""ส่งออกข้อมูล draft เป็น JSON สำหรับหน้าเว็บ

ทุกตัวเลขมาจากแมตช์จริงที่ดึงจาก Liquipedia ไม่มีค่าที่ตั้งขึ้นเอง
รันใหม่เมื่อดึงข้อมูลรายการเพิ่ม
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "core"))

from rov.cli.console import setup_console  # noqa: E402
from rov.cli.main import KNOWN_TOURNAMENTS, _regions  # noqa: E402
from rov.draft.heroes import HeroDB  # noqa: E402
from rov.draft.lanes import (  # noqa: E402
    MIN_LANE_PAIR_GAMES,
    SLOT_LANES,
    compute_lane_matchups,
    lane_usage,
    slot_evidence,
)
from rov.draft.meta import pool  # noqa: E402
from rov.draft.stats import MIN_GAMES_RELIABLE, SHRINKAGE_K  # noqa: E402

# เก็บเฉพาะคู่ที่มีข้อมูลพอ เพื่อไม่ให้ไฟล์ใหญ่เกินจำเป็น
MIN_PAIR_GAMES = 8


def main() -> int:
    setup_console()
    regions = _regions()
    if not regions:
        print("ยังไม่มีข้อมูลใน cache — รัน rov draft import ก่อน")
        return 1

    pooled = pool(regions)
    stats = pooled.stats
    prior = stats.baseline_win_rate

    # class ของฮีโร่จากไฟล์ที่ seed มาแล้ว (ข้อเท็จจริงจาก Liquipedia)
    classes: dict[str, list[str]] = {}
    names: dict[str, str] = {}
    hero_file = Path("configs/draft/heroes.yaml")
    if hero_file.exists():
        db = HeroDB.load(hero_file)
        for h in db.heroes:
            if h.hero_class:
                classes[h.id] = [c.value for c in h.hero_class]
            if h.name_en:
                names[h.id] = h.name_en

    def display_name(hid: str) -> str:
        """ชื่อที่เอาไว้แสดง — ตัดวงเล็บแก้กำกวมของ Liquipedia ออก

        หน้า Portal ใช้ชื่อแบบ "Max (Arena of Valor hero)" และ "Yue (AoV hero)"
        เพื่อแยกจากหน้าอื่นที่ชื่อซ้ำ ซึ่งไม่ควรโผล่มาให้ผู้ใช้เห็น
        """
        raw = names.get(hid)
        if not raw:
            return hid.replace("_", " ").title()
        clean = re.sub(r"\s*\([^)]*\)", "", raw).strip()
        return clean or raw

    heroes = []
    for h in stats.ranked_by_presence():
        heroes.append(
            {
                "id": h.hero_id,
                "name": display_name(h.hero_id),
                "cls": classes.get(h.hero_id, []),
                "p": h.picks,
                "b": h.bans,
                "w": h.wins,
                "pres": round(stats.presence_rate(h.hero_id), 4),
                "wr": round(h.adjusted_win_rate(prior), 4),
            }
        )

    def pack(table, one_direction: bool):
        out = []
        for (a, b), m in table.items():
            if m.games < MIN_PAIR_GAMES:
                continue
            if one_direction and a > b:
                continue
            out.append([a, b, m.games, m.wins])
        return out

    # ── context=LANE ──────────────────────────────────────────────────
    # ช่อง t1h1..t1h5 ของ Liquipedia เรียงตามเลน ตรวจหลักฐานสดทุกครั้ง
    # ถ้าวันหนึ่งไม่ผ่านเกณฑ์ แปลว่าที่มาข้อมูลเปลี่ยน ต้องหยุดใช้เลข lane
    all_series = [ser for r in regions for ser in r.series]
    evidence = slot_evidence(all_series, classes)
    if not evidence["passes"]:
        print("⚠️ สัดส่วนคลาสต่อช่องไม่ผ่านเกณฑ์ — ไม่ส่งออกข้อมูลแยกเลน")

    lane_pack: list = []
    usage_out: dict = {}
    if evidence["passes"]:
        for (lane, a, b), m in compute_lane_matchups(all_series).items():
            if m.games >= MIN_LANE_PAIR_GAMES:
                lane_pack.append([lane.value, a, b, m.games, m.wins])
        for hero, cnt in lane_usage(all_series).items():
            usage_out[hero] = {ln.value: n for ln, n in cnt.most_common()}

    data = {
        "generated": "2026-09-06",
        "total_games": stats.total_games,
        "min_lane_pair_games": MIN_LANE_PAIR_GAMES,
        "lanes": [lane.value for lane in SLOT_LANES],
        "shrinkage_k": SHRINKAGE_K,
        "min_games_reliable": MIN_GAMES_RELIABLE,
        "min_pair_games": MIN_PAIR_GAMES,
        "baseline_wr": prior,
        "blue_side_wr": round(stats.blue_side_win_rate or 0.5, 4),
        "median_length": round(stats.median_game_length or 0, 1),
        "sources": [
            {"key": k, "label": lbl, "games": pooled.games_by_source.get(lbl, 0)}
            for k, _page, lbl in KNOWN_TOURNAMENTS
            if lbl in pooled.games_by_source
        ],
        "heroes": heroes,
        # matchup เก็บสองทิศทาง เพราะไม่สมมาตรในเชิงความหมาย
        "matchups": pack(pooled.matchups, one_direction=False),
        "synergies": pack(pooled.synergies, one_direction=True),
        # context=LANE — เฉพาะคู่ที่ประกบกันในเลนเดียวกัน (rov/draft/lanes.py)
        "lane_matchups": lane_pack,
        "lane_usage": usage_out,
        "lane_evidence": evidence,
    }

    out_path = Path("data/exports/draft_data.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    size_kb = out_path.stat().st_size / 1024
    print(f"เขียน {out_path}  ({size_kb:.0f} KB)")
    print(f"  เกม        {data['total_games']}")
    print(f"  lane pair  {len(lane_pack)} (>= {MIN_LANE_PAIR_GAMES} เกม) "
          f"· หลักฐานช่อง={'ผ่าน' if evidence['passes'] else 'ไม่ผ่าน'}")
    print(f"  ฮีโร่       {len(heroes)}  (มี class {sum(1 for h in heroes if h['cls'])})")
    print(f"  matchup    {len(data['matchups']):,} คู่ (>= {MIN_PAIR_GAMES} เกม)")
    print(f"  synergy    {len(data['synergies']):,} คู่")
    print(f"  รายการ      {len(data['sources'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
