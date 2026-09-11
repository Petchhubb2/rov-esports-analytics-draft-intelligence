"""Counter Knowledge — PHASE M1 · STEP 8

**สองคุณสมบัติที่ไฟล์นี้ปกป้องเหนืออย่างอื่น**

    1. UNKNOWN ต้องเป็น UNKNOWN — ไม่รู้ = ไม่มี component ไม่ใช่ component ที่ค่า 0
    2. weight = 0 ต้องไม่เปลี่ยนอันดับ — ความรู้ใหม่เข้ามาได้โดยไม่กระทบของเดิม

ถ้าข้อ 1 หลุด ระบบจะบอกผู้ใช้ว่า "ตรวจแล้ว ไม่ได้เปรียบ" ทั้งที่ความจริงคือไม่เคยรู้
ถ้าข้อ 2 หลุด การเพิ่มความรู้จะกลายเป็นการเปลี่ยนคำแนะนำโดยไม่มีใครตั้งใจ
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from rov.domain.enums import Confidence, DraftAction, LaneRole
from rov.draft.counterknowledge import (
    KNOWLEDGE_DIR,
    CounterBook,
    CounterContext,
    CounterEvidence,
    coverage,
    explain,
    find_matches,
    summarize,
)
from rov.draft.heroes import HeroDB
from rov.draft.recommend import EXTRA_WEIGHTS, recommend, report
from rov.draft.state import DraftFormat, DraftState
from rov.eval.draftbench import (
    dict_to_lane_matchups,
    dict_to_pooled,
    draft_move_order,
    load_fixture,
)

FIXTURE = Path("tests/fixtures/recommend_regression.json")


@pytest.fixture(scope="module")
def book() -> CounterBook:
    b = CounterBook.load()
    if not b.evidence:
        pytest.skip("ยังไม่มีความรู้ใน knowledge/counter/")
    return b


@pytest.fixture(scope="module")
def ctx():
    if not FIXTURE.exists():
        pytest.skip("ยังไม่มี fixture")
    fx = load_fixture(FIXTURE)
    pooled, lu = dict_to_pooled(fx["pool"])
    return fx, pooled, lu, dict_to_lane_matchups(fx["pool"]), DraftFormat.load()


def rec(ctx, st, **kw):
    fx, pooled, lu, lmu, _ = ctx
    return recommend(
        st, pooled, limit=12, lane_usage=lu, lanes=fx["lanes"],
        lane_matchups=lmu, **kw
    )


def walk_to(ctx, n: int) -> DraftState:
    fx, pooled, _lu, _lmu, fmt = ctx
    st = DraftState(fmt=fmt, pool=set(pooled.stats.heroes))
    for h in draft_move_order(fx["drafts"][0], fmt.sequence)[:n]:
        if h in st.legal_moves():
            st.apply(h)
    return st


def first_turn_of(ctx, action: DraftAction, phase: int) -> DraftState:
    _fx, _p, _lu, _lmu, fmt = ctx
    for i in range(len(fmt.sequence)):
        st = walk_to(ctx, i)
        t = st.current
        if t is not None and t.action is action and t.phase == phase:
            return st
    pytest.skip(f"ไม่มีตา {action} เฟส {phase}")


def ev(**kw) -> dict:
    """evidence ขั้นต่ำที่ผ่าน validator — เทสต์เอาไปดัดต่อ"""
    base = dict(
        evidence_id="T-001", target="rouie", counter="billow",
        counter_type="burst", threat="recall_warp", mechanism="burst",
        mechanism_detail="เบิร์สต์ก่อนวงวาร์ปทำงาน",
        risk="เข้าไม่ถึงถ้าแผงหน้าหนา", confidence=Confidence.HIGH,
        objective_scope="both",
        source={"type": "coach_input", "ref": "คลิปสอน"},
    )
    base.update(kw)
    return base


# ───────────────────────────────── ความรู้จริงในไฟล์ต้องมีที่มาครบ


def test_the_knowledge_directory_is_the_one_the_module_reads():
    assert KNOWLEDGE_DIR == Path("knowledge/counter")


def test_every_evidence_has_a_source(book):
    for e in book.evidence:
        assert e.source.ref.strip(), f"{e.evidence_id} ไม่มีที่มา"
        assert e.source.detail, f"{e.evidence_id} ไม่ได้อ้างกลับไปที่ counter.md"


def test_every_evidence_has_a_mechanism_and_a_risk(book):
    """counter ที่บอกไม่ได้ว่าใช้กลไกอะไร คือตัวเลขที่ปลอมเป็นความรู้"""
    for e in book.evidence:
        assert e.mechanism_detail.strip(), f"{e.evidence_id} ไม่บอกกลไก"
        assert e.risk.strip(), f"{e.evidence_id} ไม่บอกความเสี่ยง"


def test_every_evidence_declares_its_objective_scope(book):
    for e in book.evidence:
        assert e.objective_scope in ("pick", "ban", "both")


def test_every_threat_and_capability_has_a_source(book):
    for row in [*book.threats, *book.capabilities, *book.answers]:
        assert row.source.ref.strip()


def test_knowledge_only_mentions_heroes_that_exist():
    """กัน typo ไม่ให้กลายเป็นความรู้ผีที่ไม่มีวันถูก match"""
    b = CounterBook.load()
    if not b.evidence:
        pytest.skip("ยังไม่มีความรู้")
    ids = {h.id for h in HeroDB.load("configs/draft/heroes.yaml").heroes}
    named = (
        {e.target for e in b.evidence}
        | {e.counter for e in b.evidence}
        | {t.hero for t in b.threats}
        | {c.hero for c in b.capabilities}
    )
    assert not (named - ids), f"ไม่มีฮีโร่เหล่านี้ในฐานข้อมูล: {sorted(named - ids)}"


# ──────────────────────────────────────── validator ที่บังคับ provenance


def test_an_assumption_cannot_be_high_confidence():
    with pytest.raises(ValidationError):
        CounterEvidence(**ev(source={"type": "assumption", "ref": "เดาเอา"}))


def test_a_claim_our_data_contradicts_cannot_be_high_confidence():
    """★ docs/27 §3 — เกิดขึ้นจริง 6 ใน 15 ข้อ"""
    with pytest.raises(ValidationError):
        CounterEvidence(
            **ev(data_check={"verdict": "disagrees", "detail": "-5.05 จาก 51 เกม", "n": 51})
        )


def test_the_same_claim_is_allowed_once_confidence_is_lowered():
    e = CounterEvidence(
        **ev(
            confidence=Confidence.MEDIUM,
            data_check={"verdict": "disagrees", "detail": "-5.05", "n": 51},
        )
    )
    assert e.status == "inferred"


def test_a_hero_cannot_counter_itself():
    with pytest.raises(ValidationError):
        CounterEvidence(**ev(counter="rouie"))


def test_a_lane_counter_must_say_which_lane():
    with pytest.raises(ValidationError):
        CounterEvidence(**ev(counter_type="lane", threat=None, mechanism="lane_trade"))
    ok = CounterEvidence(
        **ev(counter_type="lane", threat=None, mechanism="lane_trade", lane=LaneRole.DS)
    )
    assert ok.lane is LaneRole.DS


def test_status_comes_from_the_data_check_not_from_a_field():
    assert CounterEvidence(**ev()).status == "inferred"
    agrees = CounterEvidence(**ev(data_check={"verdict": "agrees", "detail": "+2.89", "n": 14}))
    assert agrees.status == "verified"
    thin = CounterEvidence(**ev(data_check={"verdict": "insufficient", "detail": "4 เกม", "n": 4}))
    assert thin.status == "inferred", "ข้อมูลไม่พอ ยังประกาศ verified ไม่ได้"


def test_duplicate_evidence_ids_are_rejected(tmp_path):
    (tmp_path / "a.yaml").write_text(
        "evidence:\n"
        "  - evidence_id: X\n    target: rouie\n    counter: billow\n"
        "    counter_type: burst\n    mechanism: burst\n"
        "    mechanism_detail: ก\n    risk: ข\n    confidence: HIGH\n"
        "    objective_scope: both\n    source: {type: coach_input, ref: ค}\n"
        "  - evidence_id: X\n    target: rouie\n    counter: omen\n"
        "    counter_type: burst\n    mechanism: burst\n"
        "    mechanism_detail: ก\n    risk: ข\n    confidence: HIGH\n"
        "    objective_scope: both\n    source: {type: coach_input, ref: ค}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="ซ้ำ"):
        CounterBook.load(tmp_path)


# ───────────────────────────────────────────────── direct hero counter


def test_a_direct_counter_is_found(book):
    m = find_matches(book, "billow", CounterContext(enemies=["rouie"], phase=2))
    assert m and any(x.route == "direct" for x in m)
    assert m[0].evidence.target == "rouie"


def test_direct_route_keeps_the_declared_confidence(book):
    m = [
        x
        for x in find_matches(book, "billow", CounterContext(enemies=["rouie"], phase=2))
        if x.route == "direct"
    ]
    assert m and m[0].confidence is m[0].evidence.confidence


# ──────────────────────────────────────────────────── mechanism match


def test_mechanism_route_links_threat_to_capability(book):
    """★ STEP 3 — ไม่ใช่แค่ A counters B แต่เดิน threat → mechanism → capability"""
    m = find_matches(book, "chaugnar", CounterContext(enemies=["ybneth"], phase=2))
    assert m, "chaugnar มี cleanse · ybneth มี heavy_cc · ต้องเจอกัน"
    top = m[0]
    assert top.threat == "heavy_cc"
    assert top.evidence.mechanism == "cleanse"


def test_mechanism_route_lowers_confidence_by_one_step(book):
    """อนุมานข้ามคู่ ต้องมั่นใจน้อยกว่าคำกล่าวตรง ๆ ของ source"""
    rank = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}
    got = [
        m
        for m in find_matches(book, "omen", CounterContext(enemies=["rouie"], phase=2))
        if m.route == "mechanism"
    ]
    assert got, "ต้องมีเส้นทาง mechanism ให้ทดสอบ"
    for m in got:
        assert rank[m.confidence] <= rank[m.evidence.confidence]


def test_a_capability_that_does_not_answer_the_threat_finds_nothing(book):
    """cleanse ไม่ได้ตอบ recall_warp — ต้องไม่มี match หลุดมา"""
    m = find_matches(book, "chaugnar", CounterContext(enemies=["rouie"], phase=2))
    assert m == [], "จับคู่กลไกผิดประเภทหลุดเข้ามา"


def test_an_unknown_candidate_produces_nothing(book):
    """★ UNKNOWN — ไม่รู้กลไกของตัวนี้ ต้องไม่เดาจาก hero_class"""
    assert find_matches(book, "ยังไม่รู้จัก", CounterContext(enemies=["rouie"])) == []


def test_an_unknown_enemy_produces_nothing(book):
    assert find_matches(book, "billow", CounterContext(enemies=["ยังไม่รู้จัก"])) == []


def test_no_enemies_means_no_evidence(book):
    assert find_matches(book, "billow", CounterContext(enemies=[])) == []


# ─────────────────────────────────────────────────────────── condition


def test_a_lane_condition_that_is_not_met_is_marked_unmet(book):
    """Mina เป็น lane counter ของ ds — ถ้า candidate ไปลงเลนอื่น ต้องไม่นับ"""
    got = find_matches(
        book,
        "mina",
        CounterContext(enemies=["marja"], phase=2, candidate_lane=LaneRole.MID),
    )
    assert got, "ต้องเจอ evidence ก่อนถึงจะทดสอบเงื่อนไขได้"
    assert all(m.condition_state == "unmet" for m in got)
    assert all(not m.counts for m in got)


def test_the_same_evidence_counts_once_the_lane_matches(book):
    got = find_matches(
        book,
        "mina",
        CounterContext(enemies=["marja"], phase=2, candidate_lane=LaneRole.DS),
    )
    assert got and all(m.condition_state == "met" for m in got)
    assert all(m.counts for m in got)


def test_a_human_readable_condition_is_unchecked_not_met(book):
    """★ เงื่อนไขที่ระบบยังตรวจไม่ได้ ต้องบอกตรง ๆ ไม่ใช่แกล้งทำเป็นผ่าน"""
    got = [
        m
        for m in find_matches(book, "billow", CounterContext(enemies=["rouie"], phase=2))
        if m.route == "direct"
    ]
    assert got and got[0].condition_state == "unchecked"
    assert got[0].counts, "ตรวจไม่ได้ ยังนับ แต่ต้องติดป้ายว่ายังไม่ได้ตรวจ"


def test_an_unconditional_rule_is_met_without_checking():
    e = CounterEvidence(**ev(unconditional=True))
    book = CounterBook(evidence=[e])
    m = find_matches(book, "billow", CounterContext(enemies=["rouie"]))
    assert m and m[0].condition_state == "met"


# ──────────────────────────────────────────── confidence / source ไหลถึง


def test_confidence_propagates_into_the_summary(book):
    s = summarize(find_matches(book, "billow", CounterContext(enemies=["rouie"], phase=2)))
    assert s.best is Confidence.HIGH


def test_summary_separates_direct_from_mechanism(book):
    """★ STEP 6 — ห้ามยุบเป็นเลขเดียวตั้งแต่ต้น"""
    s = summarize(find_matches(book, "omen", CounterContext(enemies=["rouie"], phase=2)))
    assert s.direct >= 1 and s.mechanism >= 1
    assert s.total == s.direct + s.mechanism
    assert s.known


def test_an_empty_summary_reports_unknown_not_zero():
    s = summarize([])
    assert not s.known and s.best is None


def test_source_propagates_into_the_explanation(book):
    m = find_matches(book, "chaugnar", CounterContext(enemies=["ybneth"], phase=2))
    text = explain(m[0])
    assert m[0].evidence.source.ref in text
    assert "ความมั่นใจ" in text and "ความเสี่ยง" in text and "ที่มา" in text


def test_the_explanation_always_states_what_our_own_data_says(book):
    """docs/28 §8 บังคับบรรทัดนี้ — ถ้าข้อมูลเราค้าน ต้องขึ้นว่าค้าน"""
    for hero, enemy in (("billow", "rouie"), ("chaugnar", "ybneth"), ("tachi", "rouie")):
        for m in find_matches(book, hero, CounterContext(enemies=[enemy], phase=2)):
            assert "ข้อมูลเรา:" in explain(m)


def test_a_contradicted_claim_says_so_out_loud(book):
    got = [
        m
        for m in find_matches(book, "tachi", CounterContext(enemies=["rouie"], phase=2))
        if m.route == "direct"
    ]
    assert got
    assert "ข้อมูลเราไม่เห็นด้วย" in explain(got[0])


# ───────────────────────────────────────────────────── pick กับ ban


def test_pick_and_ban_produce_different_sentences(book):
    m = find_matches(book, "billow", CounterContext(enemies=["rouie"], phase=2))[0]
    pick, ban = explain(m, "pick"), explain(m, "ban")
    assert pick != ban
    assert "ช่วยเราแก้" in pick
    assert "ถ้าปล่อย" in ban and "ให้ศัตรู" in ban


def test_scope_filters_out_evidence_that_does_not_apply():
    pick_only = CounterEvidence(**ev(evidence_id="P-1", objective_scope="pick"))
    book = CounterBook(evidence=[pick_only])
    assert find_matches(book, "billow", CounterContext(enemies=["rouie"], objective="pick"))
    assert not find_matches(book, "billow", CounterContext(enemies=["rouie"], objective="ban"))


# ────────────────────────────────── ต่อเข้ากับ engine โดยไม่เปลี่ยนอันดับ


def test_counter_evidence_starts_at_weight_zero():
    assert EXTRA_WEIGHTS["counter_evidence"] == 0.0


def test_passing_the_book_never_changes_the_ranking(ctx, book):
    """★★ คุณสมบัติหลักของ M1

    ความรู้ใหม่ทั้งก้อนเข้ามาแล้ว อันดับและคะแนนต้องไม่ขยับแม้แต่หลักทศนิยมที่ 12
    """
    checked = 0
    _fx, _p, _lu, _lmu, fmt = ctx
    for i in range(len(fmt.sequence)):
        st = walk_to(ctx, i)
        if st.current is None:
            break
        before = [(s.hero_id, s.total) for s in rec(ctx, st)]
        after = [(s.hero_id, s.total) for s in rec(ctx, st, counter_book=book)]
        assert after == before, f"อันดับเปลี่ยนที่ตา {i}"
        checked += 1
    assert checked >= 10


def test_without_the_book_there_is_no_component_at_all(ctx):
    """★ UNKNOWN — ไม่ส่งความรู้มา = ไม่มี component ไม่ใช่ component ที่ค่า 0"""
    st = first_turn_of(ctx, DraftAction.PICK, 2)
    for s in rec(ctx, st):
        assert "counter_evidence" not in s.components


def test_a_hero_with_no_knowledge_gets_no_component(ctx, book):
    st = first_turn_of(ctx, DraftAction.PICK, 2)
    got = rec(ctx, st, counter_book=book)
    without = [s for s in got if "counter_evidence" not in s.components]
    assert without, "ต้องมีตัวที่ยังไม่มีความรู้ — ครอบคลุมแค่ 24/119 ตัว"


def test_the_component_explains_itself_when_it_exists(ctx, book):
    _fx, _p, _lu, _lmu, fmt = ctx
    found = 0
    for i in range(len(fmt.sequence)):
        st = walk_to(ctx, i)
        if st.current is None:
            break
        for s in rec(ctx, st, counter_book=book):
            c = s.components.get("counter_evidence")
            if c is None:
                continue
            found += 1
            assert c.detail.strip(), f"{s.hero_id} ไม่บอกที่มาของคะแนน"
            assert s.counter_matches, "มี component แต่ไม่มี match แนบมา"
    if not found:
        pytest.skip("ดราฟต์ตัวอย่างนี้ไม่มีฮีโร่ที่อยู่ในคลังความรู้")


def test_report_can_print_the_evidence(ctx, book):
    _fx, _p, _lu, _lmu, fmt = ctx
    for i in range(len(fmt.sequence)):
        st = walk_to(ctx, i)
        if st.current is None:
            break
        sugs = rec(ctx, st, counter_book=book)
        if sugs and sugs[0].counter_matches:
            text = report(sugs, st)
            assert "หลักฐาน counter" in text
            assert "ความเสี่ยง" in text and "ที่มา" in text
            return
    pytest.skip("อันดับ 1 ของทุกตาไม่มีหลักฐาน counter")


# ────────────────────────────────────────────────────────── coverage


def test_coverage_reports_the_unknown_share_honestly(book):
    ids = [h.id for h in HeroDB.load("configs/draft/heroes.yaml").heroes]
    cov = coverage(book, ids)
    assert cov["heroes"] == len(ids)
    assert cov["unknown_heroes"] > 0, "อย่ารายงานว่ารู้ครบทั้งที่ยังไม่รู้"
    assert cov["evidence"] == len(book.evidence)
    assert cov["verified"] + cov["inferred"] == cov["evidence"]


def test_most_heroes_are_still_unknown(book):
    """ตัวเลขนี้ต้องรายงานตรง ๆ ไม่ใช่ขยายด้วยการเดา"""
    ids = [h.id for h in HeroDB.load("configs/draft/heroes.yaml").heroes]
    cov = coverage(book, ids)
    assert cov["mechanism_share"] < 0.5
