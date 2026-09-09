"""Macro Knowledge Base — กฎเรื่องที่มาต้องบังคับได้จริง ไม่ใช่แค่เขียนในเอกสาร

docs/11-macro-planner.md §2 วางกฎไว้สองข้อ
  1. rule ที่เป็น assumption ห้ามมี confidence HIGH
  2. rule ทุกข้อต้องบอกที่มาได้

ถ้ากฎพวกนี้อยู่แต่ในเอกสาร วันหนึ่งจะมีคนเพิ่ม rule ที่ละเมิดมันเข้ามา
เทสต์นี้ทำให้ละเมิดแล้วพังทันที และตรวจคลังจริงที่อยู่ใน knowledge/macro/ ด้วย
"""

from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError
from rov.domain.enums import Confidence, GamePhase
from rov.macro.plays import SOURCE_LABEL, MacroBook, MacroRule

MINIMAL = {
    "rule_id": "T1",
    "name": "ทดสอบ",
    "phase": "EARLY",
    "action": {"summary": "ทำอะไรสักอย่าง"},
    "source": {"type": "literature", "ref": "ที่ไหนสักแห่ง"},
}


def _rule(**over) -> dict:
    out = {**MINIMAL}
    out.update(over)
    return out


# ------------------------------------------------------------------ สคีมา


def test_minimal_rule_loads():
    r = MacroRule.model_validate(MINIMAL)
    assert r.phase is GamePhase.EARLY
    assert r.confidence is Confidence.MEDIUM
    assert r.source.label == SOURCE_LABEL["literature"]


def test_assumption_cannot_claim_high_confidence():
    bad = _rule(
        source={"type": "assumption", "ref": "เดาเอา"}, confidence="HIGH"
    )
    with pytest.raises(ValidationError, match="assumption"):
        MacroRule.model_validate(bad)


def test_assumption_with_lower_confidence_is_allowed():
    ok = _rule(source={"type": "assumption", "ref": "เดาเอา"}, confidence="LOW")
    assert MacroRule.model_validate(ok).confidence is Confidence.LOW


def test_data_source_must_carry_numbers():
    """อ้างว่าคำนวณจากข้อมูลแล้วไม่บอกตัวเลข = ตรวจย้อนไม่ได้"""
    bad = _rule(source={"type": "derived_from_data", "ref": "861 เกม"})
    with pytest.raises(ValidationError, match="detail"):
        MacroRule.model_validate(bad)


def test_claim_our_data_contradicts_cannot_be_high_confidence():
    bad = _rule(
        source={"type": "coach_input", "ref": "โค้ชคนหนึ่ง", "detail": "เขาว่างั้น"},
        data_check={"verdict": "disagrees", "detail": "ข้อมูลบอกตรงข้าม", "n": 90},
        confidence="HIGH",
    )
    with pytest.raises(ValidationError, match="ไม่เห็นด้วย"):
        MacroRule.model_validate(bad)


def test_contradicted_claim_is_fine_at_lower_confidence():
    ok = _rule(
        source={"type": "coach_input", "ref": "โค้ชคนหนึ่ง", "detail": "เขาว่างั้น"},
        data_check={"verdict": "disagrees", "detail": "ข้อมูลบอกตรงข้าม", "n": 90},
        confidence="LOW",
    )
    r = MacroRule.model_validate(ok)
    assert r.data_check.label == "ข้อมูลเราไม่เห็นด้วย"


def test_draft_stage_rules_have_no_phase():
    r = MacroRule.model_validate(_rule(rule_id="D", phase=None))
    assert r.phase is None
    book = MacroBook.model_validate({"rules": [r.model_dump()]})
    assert [x.rule_id for x in book.draft_rules()] == ["D"]


def test_priority_is_bounded():
    with pytest.raises(ValidationError):
        MacroRule.model_validate(_rule(priority=140))


def test_unknown_source_type_is_rejected():
    with pytest.raises(ValidationError):
        MacroRule.model_validate(_rule(source={"type": "ได้ยินมา", "ref": "x"}))


# ------------------------------------------------------------- การโหลดคลัง


def _write(tmp_path, name: str, payload: dict):
    f = tmp_path / name
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")


def test_duplicate_rule_id_is_rejected(tmp_path):
    _write(tmp_path, "a/one.yaml", {"rules": [MINIMAL]})
    _write(tmp_path, "b/two.yaml", {"rules": [MINIMAL]})
    with pytest.raises(ValueError, match="ซ้ำ"):
        MacroBook.load(tmp_path)


def test_load_walks_subdirectories(tmp_path):
    _write(tmp_path, "x/one.yaml", {"rules": [_rule(rule_id="A")]})
    _write(tmp_path, "y/z/two.yaml", {"rules": [_rule(rule_id="B", phase="BATTLE")]})
    book = MacroBook.load(tmp_path)
    assert {r.rule_id for r in book.rules} == {"A", "B"}
    assert [r.rule_id for r in book.by_phase(GamePhase.BATTLE)] == ["B"]


def test_by_phase_sorts_by_priority(tmp_path):
    _write(tmp_path, "a.yaml", {"rules": [
        _rule(rule_id="LOW", priority=10),
        _rule(rule_id="HIGH", priority=90),
    ]})
    assert [r.rule_id for r in MacroBook.load(tmp_path).by_phase(GamePhase.EARLY)] == [
        "HIGH", "LOW"
    ]


def test_for_heroes_matches_only_bound_rules(tmp_path):
    _write(tmp_path, "a.yaml", {"rules": [
        _rule(rule_id="GEN"),
        _rule(rule_id="ROUIE", heroes=["rouie"]),
    ]})
    book = MacroBook.load(tmp_path)
    assert [r.rule_id for r in book.for_heroes({"rouie", "toro"})] == ["ROUIE"]
    assert book.for_heroes({"toro"}) == []


def test_audit_lists_assumptions(tmp_path):
    _write(tmp_path, "a.yaml", {"rules": [
        _rule(rule_id="OK"),
        _rule(rule_id="GUESS", source={"type": "assumption", "ref": "เดา"},
              confidence="LOW"),
    ]})
    assert [r.rule_id for r in MacroBook.load(tmp_path).audit()] == ["GUESS"]


# ------------------------------------------------------------- คลังของจริง


def test_shipped_knowledge_base_is_valid():
    book = MacroBook.load()
    assert book.rules, "knowledge/macro/ ว่างเปล่า"
    for r in book.rules:
        assert r.action.summary, f"{r.rule_id}: ต้องสรุปเป็นภาษาคนได้"
        assert r.source.ref, f"{r.rule_id}: ต้องบอกที่มา"
        for c in r.conditions:
            assert c.cue, f"{r.rule_id}: เงื่อนไขต้องมี cue ที่คนอ่านรู้เรื่อง"


def test_shipped_rules_cover_every_phase():
    """แผนต้องครอบทุกช่วงเกม ไม่ใช่มีแต่ช่วงที่เขียนง่าย"""
    book = MacroBook.load()
    missing = [p.value for p in GamePhase if not book.by_phase(p)]
    assert not missing, f"ยังไม่มีแผนของช่วง {missing}"


def test_shipped_rules_are_not_mostly_guesses():
    """ทุกชนิดที่ไม่ใช่ assumption ถือว่ามีที่มา รวม coach_input ด้วย

    coach_input ตรวจอัตโนมัติไม่ได้ แต่มันระบุตัวคนพูดและคลิปต้นทางได้
    ต่างจาก assumption ที่ไม่มีอะไรรองรับเลย
    """
    book = MacroBook.load()
    counts = book.counts_by_source()
    guesses = counts.get("assumption", 0)
    assert guesses * 2 <= len(book.rules), (
        "สมมติฐานเกินครึ่งคลัง — ต้องหาที่มาให้แน่นกว่านี้ก่อนเอาไปใช้"
    )


def test_coach_rules_quote_the_source():
    """rule จากคลิปต้องยกคำพูดต้นทางมา ไม่งั้นย้อนไปเช็คไม่ได้ว่าตีความถูกไหม"""
    for r in MacroBook.load().rules:
        if r.source.type == "coach_input":
            assert r.source.detail, f"{r.rule_id}: coach_input ต้องมี detail ที่ยกคำพูดมา"


def test_contradicted_rules_are_surfaced_not_hidden():
    book = MacroBook.load()
    for r in book.contradicted():
        assert r.confidence is not Confidence.HIGH
        assert r.data_check.detail, f"{r.rule_id}: ต้องบอกว่าข้อมูลค้านยังไง"


def test_data_check_verdicts_carry_numbers():
    for r in MacroBook.load().rules:
        dc = r.data_check
        if dc and dc.verdict in ("agrees", "disagrees"):
            assert dc.n, f"{r.rule_id}: ตัดสินว่า{dc.verdict}แล้วต้องบอกจำนวนเกม"


def test_external_sources_link_back():
    """rule จากบทวิเคราะห์ต้องมีลิงก์ ไม่งั้นตรวจไม่ได้ว่ามาจากไหนจริง"""
    for r in MacroBook.load().rules:
        if r.source.type == "literature":
            assert r.source.url, f"{r.rule_id}: literature ต้องมี url"
