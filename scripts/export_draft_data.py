"""ส่งออกข้อมูล draft เป็น JSON สำหรับหน้าเว็บ

ทุกตัวเลขมาจากแมตช์จริงที่ดึงจาก Liquipedia ไม่มีค่าที่ตั้งขึ้นเอง
รันใหม่เมื่อดึงข้อมูลรายการเพิ่ม
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "core"))

from rov.cli.console import setup_console  # noqa: E402
from rov.cli.main import KNOWN_TOURNAMENTS, _regions  # noqa: E402
from rov.draft.heroes import REQUIRED_UTILITY, HeroDB  # noqa: E402
from rov.draft.lanes import (  # noqa: E402
    MIN_LANE_PAIR_GAMES,
    SLOT_LANES,
    compute_lane_matchups,
    lane_usage,
    slot_evidence,
)
from rov.draft.meta import pool  # noqa: E402
from rov.draft.scouting import (  # noqa: E402
    MIN_TEAM_GAMES,
    date_range,
    filter_since,
    target_bans,
    team_profiles,
)
from rov.draft.stats import MIN_GAMES_RELIABLE, SHRINKAGE_K  # noqa: E402
from rov.macro.plays import MacroBook  # noqa: E402

# เก็บเฉพาะคู่ที่มีข้อมูลพอ เพื่อไม่ให้ไฟล์ใหญ่เกินจำเป็น
MIN_PAIR_GAMES = 8

# หน้าต่าง scouting นับย้อนจากแมตช์ล่าสุดในชุดข้อมูล ไม่ใช่วันนี้
# เพราะไฟล์ export อาจถูกสร้างทิ้งไว้หลายเดือนก่อนเปิดดู ถ้านับจากวันนี้จะกลายเป็นช่วงว่าง
RECENT_DAYS = 120


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
    attrs: dict[str, dict] = {}
    hero_file = Path("configs/draft/heroes.yaml")
    if hero_file.exists():
        db = HeroDB.load(hero_file)
        for h in db.heroes:
            if h.hero_class:
                classes[h.id] = [c.value for c in h.hero_class]
            if h.name_en:
                names[h.id] = h.name_en
            # ส่งเฉพาะตัวที่กรอกครบ — ตัวที่ขาดบางช่องจะทำให้หน้าเว็บคิดคะแนนผิด
            # การส่งครึ่ง ๆ มาแล้วให้หน้าเว็บเติมเอง คือสิ่งที่โครงการนี้ห้ามมาตลอด
            if h.complete:
                attrs[h.id] = {
                    "lanes": [ln.value for ln in h.lane_roles],
                    "range": h.range,
                    "dmg": h.damage.type.value if h.damage.type else None,
                    "profile": h.damage.profile,
                    "target": h.damage.target,
                    "scaling": {
                        "early": h.scaling.early,
                        "mid": h.scaling.mid,
                        "late": h.scaling.late,
                    },
                    "u": {k: getattr(h.utility, k) for k in REQUIRED_UTILITY},
                    "tags": [t.value for t in h.macro_tags],
                    "by": h.filled_by,
                    "kind": h.filled_kind,
                    "notes": h.notes,
                }

    def display_name(hid: str) -> str:
        """ชื่อที่เอาไว้แสดง — ตัดวงเล็บแก้กำกวมของ Liquipedia ออก

        หน้า Portal ใช้ชื่อแบบ "Max (Arena of Valor hero)" และ "Yue (AoV hero)"
        เพื่อแยกจากหน้าอื่นที่ชื่อซ้ำ ซึ่งไม่ควรโผล่มาให้ผู้ใช้เห็น

        และใช้ชื่อแบบ "Flowborn/Marksman" เมื่อฮีโร่ตัวเดียวมีหลายร่าง
        ส่วนหลังทับเป็นชื่อหน้าย่อยของวิกิ ไม่ใช่ชื่อที่คนเรียกกันในเกม
        """
        raw = names.get(hid)
        if not raw:
            return hid.replace("_", " ").title()
        clean = re.sub(r"\s*\([^)]*\)", "", raw).strip()
        clean = clean.split("/")[0].strip()
        return clean or raw

    st_tendency = stats.game_length_tendency

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
                # สัญญาณช่วงเกมที่วัดจากความยาวเกมที่ชนะเทียบกับที่แพ้
                # None แปลว่าข้อมูลไม่พอ — หน้าเว็บต้องไม่เดาแทน
                "tempo": (lambda t: None if t[0] is None else round(t[0], 3))(
                    st_tendency(h.hero_id)
                ),
                "tempo_n": st_tendency(h.hero_id)[1],
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

    # ── macro knowledge base ─────────────────────────────────────────
    book = MacroBook.load()
    macro_rules = []
    for r in book.rules:
        macro_rules.append({
            "id": r.rule_id,
            "name": r.name,
            # None = ใช้ตอนหน้าดราฟต์ ก่อนเกมเริ่ม
            "phase": r.phase.value if r.phase else None,
            "priority": r.priority,
            "conf": r.confidence.value,
            "patch": r.patch,
            "heroes": r.heroes,
            "cues": [c.cue for c in r.conditions],
            "summary": r.action.summary,
            "shape": r.action.shape.value if r.action.shape else None,
            "assign": [
                {"role": a.role.value, "goto": a.goto, "note": a.note}
                for a in r.action.assignments
            ],
            "src": r.source.type,
            "src_label": r.source.label,
            "src_ref": r.source.ref,
            "src_detail": r.source.detail,
            "src_url": r.source.url,
            "check": (
                {
                    "verdict": r.data_check.verdict,
                    "label": r.data_check.label,
                    "detail": r.data_check.detail,
                    "n": r.data_check.n,
                }
                if r.data_check
                else None
            ),
            "notes": r.notes,
        })

    # ── scouting ต่อทีม ─────────────────────────────────
    #
    # ส่งสองช่วง — ทั้งหมด กับ เฉพาะช่วงล่าสุด
    # เพราะ hero pool ของทีมกว้างขึ้นตามช่วงเวลาที่รวม การดูทั้งปี
    # จะทำให้คิดว่าทีมเล่นกว้างกว่าความจริง หน้าเว็บจึงต้องสลับดูได้
    recent_cutoff = None
    lo, hi = date_range(all_series)
    if hi:
        recent_cutoff = hi - timedelta(days=RECENT_DAYS)

    def pack_teams(sers):
        out = {}
        for name, prof in team_profiles(sers).items():
            if prof.games < MIN_TEAM_GAMES:
                continue
            out[name] = {
                "games": prof.games,
                "wins": prof.wins,
                "blue_games": prof.blue_games,
                "blue_wins": prof.blue_wins,
                "first": prof.first_seen.isoformat() if prof.first_seen else None,
                "last": prof.last_seen.isoformat() if prof.last_seen else None,
                "picks": dict(prof.pick_counts.most_common(40)),
                "bans": dict(prof.ban_counts.most_common(20)),
                "lanes": {
                    lane.value: dict(pool.most_common(12))
                    for lane, pool in prof.lane_pools.items()
                },
                "bans_vs": [
                    {
                        "h": t.hero_id,
                        "lane": t.lane.value if t.lane else None,
                        "n": t.team_picks,
                        "share": round(t.team_share, 3),
                        "lift": round(t.lift, 2),
                        "score": round(t.score, 1),
                        "why": t.reason,
                    }
                    for t in target_bans(prof, league_pick_rate, limit=10)
                ],
            }
        return out

    league_pick_rate = {h: stats.pick_rate(h) for h in stats.heroes}
    teams_all = pack_teams(all_series)
    teams_recent = (
        pack_teams(filter_since(all_series, recent_cutoff)) if recent_cutoff else {}
    )

    data = {
        "generated": date.today().isoformat(),
        # ช่วงวันที่ของข้อมูล — หน้าเว็บต้องเตือนว่านี่คือข้อมูลข้ามแพตช์
        "span": {
            "from": lo.isoformat() if lo else None,
            "to": hi.isoformat() if hi else None,
            "recent_from": recent_cutoff.isoformat() if recent_cutoff else None,
            "recent_days": RECENT_DAYS,
        },
        "hero_attrs": attrs,
        "teams": teams_all,
        "teams_recent": teams_recent,
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
        # คลังความรู้มาโคร — ทุกข้อมี source ติดมาด้วยเสมอ
        "macro_rules": macro_rules,
        "macro_sources": book.counts_by_source(),
        "macro_unverified": [r.rule_id for r in book.audit()],
        "macro_contradicted": [r.rule_id for r in book.contradicted()],
    }

    out_path = Path("data/exports/draft_data.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    size_kb = out_path.stat().st_size / 1024
    print(f"เขียน {out_path}  ({size_kb:.0f} KB)")
    print(f"  เกม        {data['total_games']}")
    print(f"  macro      {len(macro_rules)} rule · {book.counts_by_source()}")
    print(f"             หน้าดราฟต์ {len(book.draft_rules())} · "
          f"ข้อมูลเราค้าน {len(book.contradicted())} · "
          f"สมมติฐาน {len(book.audit())}")
    print(f"  lane pair  {len(lane_pack)} (>= {MIN_LANE_PAIR_GAMES} เกม) "
          f"· หลักฐานช่อง={'ผ่าน' if evidence['passes'] else 'ไม่ผ่าน'}")
    print(f"  ฮีโร่       {len(heroes)}  (มี class {sum(1 for h in heroes if h['cls'])})")
    print(f"  matchup    {len(data['matchups']):,} คู่ (>= {MIN_PAIR_GAMES} เกม)")
    print(f"  synergy    {len(data['synergies']):,} คู่")
    print(f"  รายการ      {len(data['sources'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
