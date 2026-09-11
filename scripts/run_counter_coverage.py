"""วัดว่า Counter Knowledge ครอบคลุมแค่ไหนจริง — PHASE M1 · STEP 9

    python scripts/run_counter_coverage.py

⚠️ **รอบนี้ยังไม่ fit weight** `counter_evidence` ยังน้ำหนัก 0
สคริปต์นี้ตอบคำถามเดียว: "ความรู้ที่ใส่เข้าไปไปถึงตาจริงกี่ตา"
ไม่ได้ตอบว่าเปิดน้ำหนักแล้วจะดีขึ้นไหม — นั่นเป็นงานของเฟสถัดไป
และต้องใช้หน้าต่าง evaluation ใหม่ที่ยังไม่เคยดู
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "core"))

from rov.cli.console import setup_console  # noqa: E402
from rov.cli.main import _hero_classes, _regions  # noqa: E402
from rov.draft.counterknowledge import CounterBook, coverage  # noqa: E402
from rov.draft.heroes import HeroDB  # noqa: E402
from rov.draft.lanes import (  # noqa: E402
    SLOT_LANES,
    compute_lane_matchups,
    lane_usage,
    slot_evidence,
)
from rov.draft.meta import pool  # noqa: E402
from rov.draft.recommend import recommend  # noqa: E402
from rov.draft.state import DraftFormat, DraftState  # noqa: E402
from rov.eval.draftbench import draft_move_order, pick_drafts  # noqa: E402


def main() -> int:
    setup_console()
    regions = _regions()
    if not regions:
        print("ยังไม่มีข้อมูลใน cache")
        return 1
    all_series = [s for r in regions for s in r.series]
    pooled = pool(regions)
    book = CounterBook.load()
    db = HeroDB.load("configs/draft/heroes.yaml")
    hero_ids = [h.id for h in db.heroes]

    print("══ 1. คลังความรู้ ══\n")
    cov = coverage(book, hero_ids)
    print(f"  evidence ทั้งหมด      {cov['evidence']}")
    print(f"  ฮีโร่ที่เป็น target     {cov['targets']}")
    print(f"  ฮีโร่ที่เป็น counter    {cov['counters']}")
    print(f"  รู้ threat            {cov['threat_known']}/{cov['heroes']} "
          f"= {cov['threat_share'] * 100:.1f}%")
    print(f"  รู้ mechanism         {cov['mechanism_known']}/{cov['heroes']} "
          f"= {cov['mechanism_share'] * 100:.1f}%")
    print(f"  ยังไม่รู้อะไรเลย        {cov['unknown_heroes']}/{cov['heroes']} "
          f"= {cov['unknown_heroes'] / cov['heroes'] * 100:.1f}%")
    print()
    print(f"  มี data_check         {cov['with_data_check']}/{cov['evidence']}")
    print(f"    verified (ข้อมูลเห็นด้วย)   {cov['verified']}")
    print(f"    inferred (ยังยืนยันไม่ได้)  {cov['inferred']}")
    verdicts = Counter(
        e.data_check.verdict for e in book.evidence if e.data_check
    )
    for v, n in verdicts.most_common():
        print(f"      {v:<14} {n}")

    print("\n══ 2. ความครบของแต่ละ record ══\n")
    full = sum(
        1
        for e in book.evidence
        if e.mechanism_detail.strip() and e.risk.strip() and e.source.ref.strip()
    )
    cond = sum(1 for e in book.evidence if e.condition or e.unconditional)
    print(f"  มีกลไก + ความเสี่ยง + ที่มา ครบ   {full}/{len(book.evidence)}")
    print(f"  มีเงื่อนไข (หรือประกาศว่าไม่มี)    {cond}/{len(book.evidence)}")
    print(f"  ประเมินเงื่อนไขอัตโนมัติได้        "
          f"{sum(1 for e in book.evidence if e.counter_type == 'lane')}/"
          f"{len(book.evidence)}  (เฉพาะ lane counter)")

    # ── 3. ไปถึงตาจริงกี่ตา ──────────────────────────────────────────
    evidence_cls = _hero_classes()
    ev = slot_evidence(all_series, evidence_cls)
    lu = (
        {h: {x.value: n for x, n in c.most_common()} for h, c in lane_usage(all_series).items()}
        if ev["passes"] else {}
    )
    lanes = [x.value for x in SLOT_LANES] if ev["passes"] else []
    lmu = compute_lane_matchups(all_series) if ev["passes"] else {}
    fmt = DraftFormat.load()

    drafts = pick_drafts(all_series, limit=200)
    turns = with_ev = pick_turns = ban_turns = 0
    pick_ev = ban_ev = 0
    routes: Counter[str] = Counter()
    conds: Counter[str] = Counter()
    confs: Counter[str] = Counter()
    identical = changed = 0

    for draft in drafts:
        st = DraftState(fmt=fmt, pool=set(pooled.stats.heroes))
        for hero in draft_move_order(draft, fmt.sequence):
            turn = st.current
            if turn is None:
                break
            base = recommend(
                st, pooled, limit=8, lane_usage=lu, lanes=lanes, lane_matchups=lmu
            )
            withk = recommend(
                st, pooled, limit=8, lane_usage=lu, lanes=lanes, lane_matchups=lmu,
                counter_book=book,
            )
            if [(s.hero_id, s.total) for s in base] == [
                (s.hero_id, s.total) for s in withk
            ]:
                identical += 1
            else:
                changed += 1

            turns += 1
            is_ban = turn.action.value == "BAN"
            pick_turns += not is_ban
            ban_turns += is_ban
            hit = any(s.counter_matches for s in withk)
            with_ev += hit
            pick_ev += hit and not is_ban
            ban_ev += hit and is_ban
            for s in withk:
                for m in s.counter_matches:
                    routes[m.route] += 1
                    conds[m.condition_state] += 1
                    confs[m.confidence.value] += 1
            if hero in st.legal_moves():
                st.apply(hero)
            else:
                break

    print("\n══ 3. ไปถึงตาจริงกี่ตา ══\n")
    print(f"  ดราฟต์ {len(drafts)} · ตาทั้งหมด {turns}")
    print(f"  ตาที่มีหลักฐานอย่างน้อยหนึ่งชิ้นใน 8 อันดับแรก  "
          f"{with_ev}/{turns} = {with_ev / max(1, turns) * 100:.1f}%")
    print(f"    ตาเลือก  {pick_ev}/{pick_turns} = {pick_ev / max(1, pick_turns) * 100:.1f}%")
    print(f"    ตาแบน   {ban_ev}/{ban_turns} = {ban_ev / max(1, ban_turns) * 100:.1f}%")
    print()
    print(f"  หลักฐานที่ยิงออกมา  direct {routes['direct']} · mechanism {routes['mechanism']}")
    print(f"  เงื่อนไข            ผ่าน {conds['met']} · ยังตรวจไม่ได้ {conds['unchecked']}")
    print("  ความมั่นใจ          " + " · ".join(f"{k} {v}" for k, v in confs.most_common()))

    print("\n══ 4. ไม่ถดถอย ══\n")
    print(f"  ตาที่คะแนนเหมือนเดิมเป๊ะ  {identical}/{turns}")
    print(f"  ตาที่เปลี่ยน              {changed}")
    if changed:
        print("  ⛔ น้ำหนักควรเป็น 0 แต่อันดับขยับ — ต้องหยุดและหาสาเหตุ")
        return 1
    print("  ✅ weight = 0 แปลว่าไม่เปลี่ยนจริง")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
