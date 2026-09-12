"""Synergy Knowledge — PHASE M2A · STEP 8

**สามคุณสมบัติที่ไฟล์นี้ปกป้องเหนืออย่างอื่น**

    1. UNKNOWN ต้องเป็น UNKNOWN — ไม่รู้ = ไม่มี component ไม่ใช่ component ที่ค่า 0
    2. weight = 0 ต้องไม่เปลี่ยนอันดับ — representation ใหม่เข้ามาได้โดยไม่กระทบของเดิม
    3. association ≠ mechanism — co-occurrence ต้องไม่ถูกเรียกว่า synergy โดยอัตโนมัติ
       และ alias ที่ยังยืนยันไม่ได้ (doria) ต้องไม่มีวันถูกนำมา match/score

ถ้าข้อ 1 หลุด ระบบจะบอกว่า "ตรวจแล้ว ไม่เข้ากัน" ทั้งที่ความจริงคือไม่เคยรู้
ถ้าข้อ 2 หลุด การเพิ่มความรู้จะกลายเป็นการเปลี่ยนคำแนะนำโดยไม่มีใครตั้งใจ (M2A ห้าม)
ถ้าข้อ 3 หลุด เรากลับไปทำผิดแบบเดิมที่ docs/32 เพิ่งพิสูจน์ว่าพลิก 15.9% ของคู่
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError
from rov.domain.enums import Confidence
from rov.draft.heroes import HeroDB
from rov.draft.recommend import EXTRA_WEIGHTS, recommend, report
from rov.draft.state import DraftFormat, DraftState
from rov.draft.synergyknowledge import (
    KNOWLEDGE_DIR,
    SynergyBook,
    SynergyContext,
    SynergyEvidence,
    coverage,
    data_check_from_association,
    explain,
    find_matches,
    measure_association,
    quality_table,
    summarize,
)
from rov.eval.draftbench import (
    dict_to_pooled,
    draft_move_order,
    load_fixture,
)

FIXTURE = Path("tests/fixtures/recommend_regression.json")


@pytest.fixture(scope="module")
def book() -> SynergyBook:
    b = SynergyBook.load()
    if not b.evidence:
        pytest.skip("ยังไม่มีความรู้ใน knowledge/synergy/")
    return b


@pytest.fixture(scope="module")
def ctx():
    if not FIXTURE.exists():
        pytest.skip("ยังไม่มี fixture")
    fx = load_fixture(FIXTURE)
    pooled, lu = dict_to_pooled(fx["pool"])
    return fx, pooled, lu, DraftFormat.load()


def rec(ctx, st, **kw):
    fx, pooled, lu, _ = ctx
    return recommend(st, pooled, limit=12, lane_usage=lu, lanes=fx["lanes"], **kw)


def walk_to(ctx, n: int) -> DraftState:
    fx, pooled, _lu, fmt = ctx
    st = DraftState(fmt=fmt, pool=set(pooled.stats.heroes))
    for h in draft_move_order(fx["drafts"][0], fmt.sequence)[:n]:
        if h in st.legal_moves():
            st.apply(h)
    return st


def ev(**kw) -> dict:
    """evidence ขั้นต่ำที่ผ่าน validator — เทสต์เอาไปดัดต่อ"""
    base = dict(
        evidence_id="T-001", entity_a="rouie", entity_b="marja",
        synergy_type="global_warp", mechanism="recall_warp",
        mechanism_detail="วาร์ปดึงกลับบ้าน ดันสองทาง",
        expected_result="กดดันสองเลนพร้อมกัน", weakness="โดนเบิร์สหนัก",
        confidence=Confidence.HIGH, objective_scope="both",
        source={"type": "coach_input", "ref": "คลิปสอน"},
    )
    base.update(kw)
    return base


# ───────────────────────────────── ความรู้จริงในไฟล์ต้องมีที่มาครบ


def test_the_knowledge_directory_is_the_one_the_module_reads():
    assert KNOWLEDGE_DIR == Path("knowledge/synergy")


def test_every_evidence_has_a_source(book):
    for e in book.evidence:
        assert e.source.ref.strip(), f"{e.evidence_id} ไม่มีที่มา"
        assert e.source.detail, f"{e.evidence_id} ไม่ได้อ้างกลับไปที่ synergy.md"


def test_every_evidence_carries_mechanism_result_and_weakness(book):
    """synergy ที่บอกไม่ได้ว่าช่วยกันอย่างไร คือตัวเลขที่ปลอมเป็นความรู้"""
    for e in book.evidence:
        assert e.mechanism_detail.strip(), f"{e.evidence_id} ไม่บอกกลไก"
        assert e.expected_result.strip(), f"{e.evidence_id} ไม่บอกผลที่คาด"
        assert e.weakness.strip(), f"{e.evidence_id} ไม่บอกจุดอ่อน"


def test_every_evidence_declares_its_objective_scope(book):
    for e in book.evidence:
        assert e.objective_scope in ("pick", "ban", "both")


def test_knowledge_only_names_heroes_that_exist_or_are_unresolved():
    """กัน typo ไม่ให้กลายเป็นความรู้ผีที่ไม่มีวันถูก match —

    ยกเว้น entity ที่ประกาศไว้ว่า unresolved (เช่น doria) ซึ่ง**ตั้งใจ**ให้ยังไม่ตรง id
    """
    b = SynergyBook.load()
    if not b.evidence:
        pytest.skip("ยังไม่มีความรู้")
    ids = {h.id for h in HeroDB.load("configs/draft/heroes.yaml").heroes}
    for e in b.evidence:
        for name in e.pair:
            if name in e.unresolved:
                continue
            assert name in ids, f"{e.evidence_id}: ไม่มีฮีโร่ '{name}' และไม่ได้ประกาศ unresolved"


# ──────────────────────────────────────── validator ที่บังคับ provenance


def test_an_assumption_cannot_be_high_confidence():
    with pytest.raises(ValidationError):
        SynergyEvidence(**ev(source={"type": "assumption", "ref": "เดาเอา"}))


def test_a_claim_our_data_contradicts_cannot_be_high_confidence():
    """★ docs/32 §4 — disagree 4 ใน 8 ข้อ"""
    with pytest.raises(ValidationError):
        SynergyEvidence(
            **ev(data_check={"verdict": "disagrees", "detail": "-1.96 จาก 37 เกม", "n": 37})
        )


def test_the_same_claim_is_allowed_once_confidence_is_lowered():
    e = SynergyEvidence(
        **ev(
            confidence=Confidence.MEDIUM,
            data_check={"verdict": "disagrees", "detail": "-1.96", "n": 37},
        )
    )
    assert e.status == "inferred"


def test_a_hero_cannot_synergize_with_itself():
    with pytest.raises(ValidationError):
        SynergyEvidence(**ev(entity_b="rouie"))


def test_unresolved_must_name_one_of_the_two_entities():
    with pytest.raises(ValidationError):
        SynergyEvidence(**ev(unresolved=["ghost"], confidence=Confidence.LOW))


def test_an_unresolved_entity_cannot_be_high_confidence():
    """★ STEP 6 — ยังไม่รู้ด้วยซ้ำว่าเป็นฮีโร่ตัวไหน จะมั่นใจสูงไม่ได้"""
    with pytest.raises(ValidationError):
        SynergyEvidence(**ev(entity_a="doria", unresolved=["doria"]))


# ───────────────────────────────────── status มาจากหลักฐาน ไม่ได้ตั้งเอง


def test_status_comes_from_the_data_check_not_a_field():
    assert SynergyEvidence(**ev()).status == "inferred"
    agrees = SynergyEvidence(**ev(data_check={"verdict": "agrees", "detail": "+1.71", "n": 34}))
    assert agrees.status == "verified"
    thin = SynergyEvidence(**ev(data_check={"verdict": "insufficient", "detail": "4 เกม", "n": 4}))
    assert thin.status == "inferred", "ข้อมูลไม่พอ ยังประกาศ verified ไม่ได้"


def test_an_unresolved_record_is_unknown_and_unusable():
    """★★ หัวใจของ STEP 6 — alias ยืนยันไม่ได้ = unknown = ห้ามใช้"""
    e = SynergyEvidence(**ev(entity_a="doria", unresolved=["doria"], confidence=Confidence.LOW))
    assert e.status == "unknown"
    assert not e.usable
    # แม้จะมี data_check agrees ก็ยังต้อง unknown เพราะไม่รู้ว่าวัดถูกตัวไหม
    e2 = SynergyEvidence(
        **ev(entity_a="doria", unresolved=["doria"], confidence=Confidence.LOW,
             data_check={"verdict": "agrees", "detail": "x", "n": 40})
    )
    assert e2.status == "unknown" and not e2.usable


def test_duplicate_evidence_ids_are_rejected(tmp_path):
    (tmp_path / "a.yaml").write_text(
        "evidence:\n"
        "  - evidence_id: X\n    entity_a: rouie\n    entity_b: marja\n"
        "    synergy_type: global_warp\n    mechanism: recall_warp\n"
        "    mechanism_detail: ก\n    expected_result: ข\n    weakness: ค\n"
        "    confidence: MEDIUM\n    objective_scope: both\n"
        "    source: {type: coach_input, ref: ง}\n"
        "  - evidence_id: X\n    entity_a: rouie\n    entity_b: capheny\n"
        "    synergy_type: global_warp\n    mechanism: recall_warp\n"
        "    mechanism_detail: ก\n    expected_result: ข\n    weakness: ค\n"
        "    confidence: MEDIUM\n    objective_scope: both\n"
        "    source: {type: coach_input, ref: ง}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="ซ้ำ"):
        SynergyBook.load(tmp_path)


# ───────────────────────────────────── matching แบบไม่มีทิศทาง


def test_a_pair_is_found_from_either_side(book):
    """★ synergy ไม่มีทิศทาง — ถาม candidate ฝั่งไหนก็ต้องเจอคู่เดียวกัน"""
    a = find_matches(book, "rouie", SynergyContext(allies=["marja"]))
    b = find_matches(book, "marja", SynergyContext(allies=["rouie"]))
    assert a and b
    assert a[0].evidence.evidence_id == b[0].evidence.evidence_id


def test_an_unknown_candidate_produces_nothing(book):
    assert find_matches(book, "ยังไม่รู้จัก", SynergyContext(allies=["marja"])) == []


def test_an_unknown_ally_produces_nothing(book):
    assert find_matches(book, "rouie", SynergyContext(allies=["ยังไม่รู้จัก"])) == []


def test_no_allies_means_no_synergy(book):
    assert find_matches(book, "rouie", SynergyContext(allies=[])) == []


def test_an_unresolved_record_never_matches(book):
    """★★ doria+tachi ต้องไม่โผล่ ไม่ว่าจะถามด้วย dolia หรือ doria"""
    assert find_matches(book, "dolia", SynergyContext(allies=["tachi"])) == []
    assert find_matches(book, "doria", SynergyContext(allies=["tachi"])) == []
    assert find_matches(book, "tachi", SynergyContext(allies=["dolia"])) == []


def test_scope_filters_out_evidence_that_does_not_apply():
    pick_only = SynergyEvidence(**ev(evidence_id="P-1", objective_scope="pick"))
    b = SynergyBook(evidence=[pick_only])
    assert find_matches(b, "rouie", SynergyContext(allies=["marja"], objective="pick"))
    assert not find_matches(b, "rouie", SynergyContext(allies=["marja"], objective="ban"))


def test_a_human_readable_condition_is_unchecked_not_met(book):
    """★ เงื่อนไขที่ระบบยังตรวจไม่ได้ ต้องบอกตรง ๆ ไม่ใช่แกล้งทำเป็นผ่าน"""
    got = find_matches(book, "rouie", SynergyContext(allies=["marja"]))
    assert got and got[0].condition_state == "unchecked"
    assert got[0].counts, "ตรวจไม่ได้ ยังนับ แต่ต้องติดป้ายว่ายังไม่ได้ตรวจ"


def test_an_unconditional_rule_is_met_without_checking():
    e = SynergyEvidence(**ev(unconditional=True))
    b = SynergyBook(evidence=[e])
    m = find_matches(b, "rouie", SynergyContext(allies=["marja"]))
    assert m and m[0].condition_state == "met"


# ─────────────────── association ≠ mechanism (STEP 3) — วัด ไม่ใช่ประกาศ


def test_association_is_measured_separately_from_the_claim(ctx):
    """★ STEP 3 — co-occurrence เป็นตัวเลขที่วัดได้ ไม่ใช่ข้ออ้าง synergy"""
    _fx, pooled, _lu, _ = ctx
    a = measure_association(pooled, "rouie", "marja")
    assert a is not None
    assert a.games > 0 and 0.0 <= a.raw_win_rate <= 1.0
    # raw (association) กับ adjusted_score (สัญญาณจริง) เป็นคนละค่า
    assert a.expected != a.raw_win_rate or a.adjusted_score == pytest.approx(0.0, abs=2.0)


def test_measure_association_reuses_expected_synergy_not_a_reimplementation():
    """ห้าม duplicate สูตร odds — ต้องเรียก expected_synergy() เดิมใน stats.py"""
    src = inspect.getsource(measure_association)
    assert "expected_synergy" in src
    assert "math.sqrt" not in src, "เขียนสูตร odds ซ้ำแทนที่จะเรียกของเดิม"


def test_a_pair_never_seen_together_is_insufficient_not_zero(ctx):
    _fx, pooled, _lu, _ = ctx
    a = measure_association(pooled, "rouie", "doria")  # doria ไม่มีในข้อมูล
    dc = data_check_from_association(a)
    assert dc.verdict == "insufficient"


def test_the_data_check_in_the_file_matches_a_live_recompute(ctx, book):
    """★★ ตัวเลข data_check ที่ commit ไว้ ต้องตรงกับที่คำนวณสดจาก 861 เกม

    ใช้ pool ใน fixture (คือชุด 861 เกมเต็ม) จึงไม่ต้องพึ่ง cache
    """
    _fx, pooled, _lu, _ = ctx
    checked = 0
    for e in book.evidence:
        if e.data_check is None or e.status == "unknown":
            continue  # doria+tachi วัดไม่ได้เพราะ entity ยังไม่ยืนยัน
        live = data_check_from_association(measure_association(pooled, e.entity_a, e.entity_b))
        assert live.verdict == e.data_check.verdict, (
            f"{e.evidence_id}: ไฟล์บอก {e.data_check.verdict} แต่คำนวณสดได้ {live.verdict}"
        )
        checked += 1
    assert checked >= 5, "ต้องมีข้อที่ตรวจได้จริงพอสมควร"


def test_the_agreeing_pair_really_agrees_and_a_disagreeing_one_disagrees(ctx):
    _fx, pooled, _lu, _ = ctx
    marja = data_check_from_association(measure_association(pooled, "rouie", "marja"))
    capheny = data_check_from_association(measure_association(pooled, "rouie", "capheny"))
    assert marja.verdict == "agrees"
    assert capheny.verdict == "disagrees"


# ──────────────────────────────────── summary / explain / coverage


def test_summary_counts_direct_and_reports_known(book):
    s = summarize(find_matches(book, "rouie", SynergyContext(allies=["marja"])))
    assert s.direct >= 1 and s.total == s.direct and s.known


def test_an_empty_summary_reports_unknown_not_zero():
    s = summarize([])
    assert not s.known and s.best is None


def test_explain_states_mechanism_result_weakness_source_and_our_data(book):
    m = find_matches(book, "rouie", SynergyContext(allies=["marja"]))[0]
    text = explain(m)
    assert m.evidence.source.ref in text
    for label in ("กลไก", "ผลที่คาด", "จุดอ่อน", "ความมั่นใจ", "ที่มา", "ข้อมูลเรา"):
        assert label in text, f"explain ขาดช่อง {label}"


def test_pick_and_ban_produce_different_sentences(book):
    m = find_matches(book, "rouie", SynergyContext(allies=["marja"]))[0]
    pick, ban = explain(m, "pick"), explain(m, "ban")
    assert pick != ban
    assert "เข้าคู่กับ" in pick
    assert "ถ้าปล่อย" in ban and "ให้ศัตรู" in ban


def test_a_contradicted_claim_says_so_out_loud(book):
    """docs — ถ้าข้อมูลเราค้าน ต้องขึ้นว่าค้าน ไม่ใช่ซ่อน"""
    m = find_matches(book, "rouie", SynergyContext(allies=["capheny"]))
    assert m
    assert "ข้อมูลเราไม่เห็นด้วย" in explain(m[0])


def test_coverage_reports_the_unknown_share_honestly(book):
    ids = [h.id for h in HeroDB.load("configs/draft/heroes.yaml").heroes]
    cov = coverage(book, ids)
    assert cov["heroes"] == len(ids)
    assert cov["unknown_heroes"] > 0, "อย่ารายงานว่ารู้ครบทั้งที่ยังไม่รู้"
    assert cov["evidence"] == len(book.evidence)
    assert cov["verified"] + cov["inferred"] + cov["unknown_records"] == cov["evidence"]
    assert cov["unknown_records"] >= 1, "doria+tachi ต้องนับเป็น unknown"


def test_quality_table_keeps_both_the_mechanism_and_the_data_side(book):
    rows = quality_table(book)
    assert len(rows) == len(book.evidence)
    for r in rows:
        assert r.mechanism_claim.strip(), "ต้องเก็บฝั่งความรู้ (กลไก)"
        assert r.association_detail.strip(), "ต้องเก็บฝั่งข้อมูล (association)"
        assert r.verdict in ("agree", "disagree", "partial", "insufficient", "unknown")


def test_a_disagreeing_rule_still_stands(book):
    """★ disagree ≠ synergy invalid — ข้ออ้างทุกข้อยังอยู่"""
    rows = quality_table(book)
    bad = [r for r in rows if r.verdict == "disagree"]
    assert bad, "ตอนนี้ควรมีข้อที่ข้อมูลค้านอยู่จริง"
    assert all(r.rule_still_stands for r in bad)
    assert all(r.confidence is not Confidence.HIGH for r in bad), "แต่ต้องไม่ HIGH"


# ────────────────────────────── ต่อเข้า engine โดยไม่เปลี่ยนอันดับ (STEP 8)


def test_synergy_evidence_starts_at_weight_zero():
    assert EXTRA_WEIGHTS["synergy_evidence"] == 0.0


def test_passing_the_book_never_changes_the_ranking(ctx, book):
    """★★ คุณสมบัติหลักของ M2A

    representation ใหม่ทั้งก้อนเข้ามาแล้ว อันดับและคะแนนต้องไม่ขยับแม้แต่หลักทศนิยมที่ 12
    """
    checked = 0
    _fx, _p, _lu, fmt = ctx
    for i in range(len(fmt.sequence)):
        st = walk_to(ctx, i)
        if st.current is None:
            break
        before = [(s.hero_id, s.total) for s in rec(ctx, st)]
        after = [(s.hero_id, s.total) for s in rec(ctx, st, synergy_book=book)]
        assert after == before, f"อันดับเปลี่ยนที่ตา {i}"
        checked += 1
    assert checked >= 10


def test_the_two_knowledge_layers_together_still_change_nothing(ctx, book):
    """counter_book + synergy_book พร้อมกัน ก็ยังต้องน้ำหนัก 0 ทั้งคู่"""
    from rov.draft.counterknowledge import CounterBook

    cb = CounterBook.load()
    st = walk_to(ctx, 8)
    if st.current is None:
        pytest.skip("เดินไม่ถึงตา")
    before = [(s.hero_id, round(s.total, 12)) for s in rec(ctx, st)]
    after = [
        (s.hero_id, round(s.total, 12))
        for s in rec(ctx, st, counter_book=cb, synergy_book=book)
    ]
    assert after == before


def test_without_the_book_there_is_no_component_at_all(ctx):
    """★ UNKNOWN — ไม่ส่งความรู้มา = ไม่มี component ไม่ใช่ component ที่ค่า 0"""
    st = walk_to(ctx, 8)
    for s in rec(ctx, st):
        assert "synergy_evidence" not in s.components


def test_a_hero_with_no_knowledge_gets_no_component(ctx, book):
    st = walk_to(ctx, 8)
    got = rec(ctx, st, synergy_book=book)
    without = [s for s in got if "synergy_evidence" not in s.components]
    assert without, "ต้องมีตัวที่ยังไม่มีความรู้ — คลังมีแค่ 7 คู่"


def test_the_component_explains_itself_when_it_exists(ctx, book):
    _fx, _p, _lu, fmt = ctx
    found = 0
    for i in range(len(fmt.sequence)):
        st = walk_to(ctx, i)
        if st.current is None:
            break
        for s in rec(ctx, st, synergy_book=book):
            c = s.components.get("synergy_evidence")
            if c is None:
                continue
            found += 1
            assert c.detail.strip(), f"{s.hero_id} ไม่บอกที่มาของคะแนน"
            assert s.synergy_matches, "มี component แต่ไม่มี match แนบมา"
    if not found:
        pytest.skip("ดราฟต์ตัวอย่างนี้ไม่มีฮีโร่ที่อยู่ในคลังความรู้")
    assert found >= 1


def test_opening_the_weight_changes_the_ranking(ctx, book):
    """★ พิสูจน์ว่าไม่ใช่ dead code — ถ้าเปิดน้ำหนักแล้วไม่มีตาไหนขยับ แปลว่าไม่ได้ต่อจริง"""
    _fx, _p, _lu, fmt = ctx
    changed = False
    for i in range(len(fmt.sequence)):
        st = walk_to(ctx, i)
        if st.current is None:
            break
        base = [s.hero_id for s in rec(ctx, st, synergy_book=book)]
        opened = [
            s.hero_id
            for s in rec(ctx, st, synergy_book=book, extra_weights={"synergy_evidence": 0.9})
        ]
        if base != opened:
            changed = True
            break
    assert changed, "เปิดน้ำหนักแล้วอันดับไม่เปลี่ยนเลย — factor ไม่ได้ถูกใช้จริง"


def test_report_can_print_the_evidence(ctx, book):
    _fx, _p, _lu, fmt = ctx
    for i in range(len(fmt.sequence)):
        st = walk_to(ctx, i)
        if st.current is None:
            break
        sugs = rec(ctx, st, synergy_book=book)
        if sugs and sugs[0].synergy_matches:
            text = report(sugs, st)
            assert "หลักฐาน synergy" in text
            assert "ผลที่คาด" in text and "ที่มา" in text
            return
    pytest.skip("อันดับ 1 ของทุกตาไม่มีหลักฐาน synergy")


# ─────────────────────────────── STEP 7 · marja counter representation


def test_marja_now_has_a_threat_tag():
    """★ docs/31 §4.2 — เดิม marja เป็น target แต่ไม่มี threat จึง mechanism match ไม่ได้"""
    from rov.draft.counterknowledge import CounterBook

    cb = CounterBook.load()
    if not cb.evidence:
        pytest.skip("ยังไม่มีความรู้ counter")
    assert cb.threats_of("marja"), "marja ต้องมี threat tag แล้ว (STEP 7)"


def test_there_is_a_sourced_answer_to_marjas_threat():
    from rov.draft.counterknowledge import CounterBook

    cb = CounterBook.load()
    if not cb.evidence:
        pytest.skip("ยังไม่มีความรู้ counter")
    for threat in cb.threats_of("marja"):
        answers = cb.answers_for(threat)
        assert answers, f"threat {threat} ของ marja ยังไม่มีวิธีตอบ"
        for a in answers:
            assert a.source.ref.strip(), "วิธีตอบต้องมีที่มา"


def test_mechanism_matching_now_reaches_marja():
    """★★ หัวใจ STEP 7 — ตัวที่มี lane_trade ต้อง match marja ผ่านเส้น mechanism ได้"""
    from rov.draft.counterknowledge import CounterBook, CounterContext
    from rov.draft.counterknowledge import find_matches as cf

    cb = CounterBook.load()
    if not cb.evidence:
        pytest.skip("ยังไม่มีความรู้ counter")
    m = cf(cb, "mina", CounterContext(enemies=["marja"], phase=2))
    assert m, "mina มี lane_trade · marja มี split_push · ต้องเจอกัน"
    assert any(x.route == "mechanism" for x in m), "ต้องมีเส้น mechanism ไม่ใช่แค่ direct"
