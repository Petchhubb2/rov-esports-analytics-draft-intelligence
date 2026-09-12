# 35 — Synergy Knowledge Report

PHASE M2A · 2026-09-12 · ผลของการถอด `synergy.md` เป็น representation ที่ trace ได้

spec: [docs/34](34-synergy-knowledge-spec.md) · audit: [docs/33](33-synergy-knowledge-audit.md) · ล้อ counter: [docs/29](29-counter-knowledge-report.md)

> ทุกตัวเลขในเอกสารนี้อ่านสดจากโค้ด/ข้อมูลจริง ไม่ได้พิมพ์ทับ —
> `python scripts/run_m15_status.py` และเทสต์ 46 ข้อใน `test_synergy_knowledge.py` ยืนยันซ้ำได้

---

## 1. synergy records — 8 ข้อจาก synergy.md §1

| id | pair | type | mechanism | conf | data_check | status |
|---|---|---|---|---|---|---|
| SYN-001 | rouie + capheny | global_warp | recall_warp | MEDIUM | disagree (29 เกม) | inferred |
| SYN-002 | teemee + capheny | gold_boost | gold_accel | MEDIUM | disagree (37 เกม) | inferred |
| SYN-003 | ming + capheny | gold_boost | stat_buff | HIGH | insufficient (4) | inferred |
| SYN-004 | **doria** + tachi | double_ult | ult_reset | LOW | insufficient (alias) | **unknown** |
| SYN-005 | krizzix + liliana | aoe_pull_burst | engage_followup | MEDIUM | disagree (10) | inferred |
| SYN-006 | krizzix + zuka | aoe_pull_burst | engage_followup | HIGH | insufficient (2) | inferred |
| SYN-007 | rouie + marja | global_warp | recall_warp | HIGH | **agree (34)** | **verified** |
| SYN-008 | chaugnar + hayate | front_to_back | cleanse_cover | HIGH | insufficient (3) | inferred |

**7 usable · 1 unknown** (doria+tachi — alias ยังยืนยันไม่ได้)

---

## 2. coverage — รายงานตรง ๆ ไม่ขยายด้วยการเดา

| มิติ | ค่า | เทียบเป้า |
|---|---|---|
| records | **8** | 8 pair ใน synergy.md §1 ครบ |
| **mechanism coverage** | **8/8** | ทุกข้อมี `mechanism` + `mechanism_detail` |
| **condition coverage** | **8/8** | ทุกข้อมี condition cue (unconditional 0) |
| **expected_result coverage** | **8/8** | ทุกข้อบอกผลที่คาด |
| **weakness coverage** | **8/8** | ทุกข้อบอกจุดอ่อน |
| **source coverage** | **8/8** | ทุกข้อมี `source.ref` + `source.detail` (STEP 5) |
| **association coverage** | **7/8** วัดได้ · 4/8 ถึงเกณฑ์ ≥8 เกม | ช่องเดียวที่วัดไม่ได้คือ doria (ไม่มีในข้อมูล) |
| with data_check | 8/8 | |

### 2.1 UNKNOWN coverage — ต้องรายงานตรง ๆ

| | ค่า |
|---|---|
| ฮีโร่ทั้งหมด | 119 |
| ฮีโร่ที่มี synergy record ใช้ได้ | **10** (8.4%) |
| **ฮีโร่ที่ยังไม่รู้** | **109** (91.6%) |
| unknown records (alias) | 1 |

คลังมีแค่ 7 คู่ที่ใช้ได้ · ฮีโร่ส่วนใหญ่ไม่มี synergy record — และระบบ **บอกว่าไม่รู้**
ไม่ใช่แกล้งให้คะแนน 0 (เหมือน counter ที่ครอบคลุมแค่ 24/119 ตัว — docs/29 §5)

---

## 3. distribution

### 3.1 confidence
`HIGH 4 · MEDIUM 3 · LOW 1` — MEDIUM ทั้งสามคือข้อที่ข้อมูลค้าน (ลดจาก HIGH ตาม validator)
LOW คือ doria (ยังยืนยัน entity ไม่ได้)

### 3.2 DataCheck (usable 7 ข้อ · คำนวณสดด้วยสูตรที่ shipping จริง)
`agree 1 · disagree 3 · insufficient 3`

รวม doria (unknown) → `agree 1 · disagree 3 · insufficient 3 · unknown 1`

> **ภายใต้สมมติฐาน doria = dolia** (แบบ docs/32) จะได้ `agree 1 · disagree 4 · insufficient 3`
> — ตรงกับ M1.5 และโจทย์ M2A เป๊ะ · ต่างกันแค่ M2A ถือว่า doria+tachi เป็น unknown ไม่ใช่ disagree

### 3.3 มิติที่ match data กับ mechanism ตอบ — **คนละมิติ** (STEP 4)

`disagree 3 ใน 7` ข้อ **ไม่ได้แปลว่ากลไกผิด** ตัวอย่างที่ชัดที่สุด:

- **rouie + capheny** (disagree −0.81) กลไก recall-warp เป็นข้อเท็จจริงของตัวเกมที่ตรวจได้
  แต่ `rouie` ถูกแบน 565/861 เกม เกมที่เขาได้ลงคือเกมที่อีกฝั่งเลือกจะไม่แบน — ตัวอย่างถูกคัดมาแล้ว
- **rouie + marja** (agree +1.71) เป็นคู่เดียวที่ผลแพ้ชนะหนุน — น่าสนใจว่ามันคือ split-push
  duo ที่ทั้ง synergy.md และข้อมูลเห็นตรงกัน

match data วัด "ฝ่ายที่มีคู่นี้ชนะบ่อยไหม" (มีตัวแปรแทรกเต็มไปหมด) · mechanism วัด "กลไกทำงานไหม"
**ห้ามเอาอย่างแรกไปเขียนทับอย่างหลัง** — เก็บทั้งคู่ ลด confidence เมื่อค้าน

---

## 4. unresolved alias — Doria (STEP 6)

| | |
|---|---|
| ปัญหา | synergy.md เขียน "Doria (ดอเรีย)" · ฐานข้อมูลมีแต่ `dolia` · ไม่มี alias mapping |
| การจัดการ | `unresolved: [doria]` → `status = unknown` → **ไม่ถูก match/score/benchmark** |
| ความรู้ | กลไก ult-reset **ไม่ถูกลบ** เก็บไว้แต่ปิดใช้งาน |
| ปลดล็อกเมื่อ | ยืนยันว่า doria = dolia → เพิ่ม `HERO_ALIASES` แล้วแก้ record (docs/34 §6) |

เทสต์ `test_an_unresolved_record_never_matches` ยืนยันว่า doria+tachi ไม่โผล่ ไม่ว่าจะถามด้วย
`dolia` หรือ `doria`

---

## 5. STEP 7 — marja counter representation ✅

| ก่อน | หลัง |
|---|---|
| marja เป็น target (CTR-002/004) แต่ **ไม่มี threat tag** | มี `threats: [split_push]` · **source = synergy.md Pair 7 "Dual Side Push"** |
| mechanism matching เอื้อมไม่ถึง marja (docs/31 §4.2) | `find_matches("mina", enemies=["marja"])` เดินเส้น mechanism ได้ |
| — | MechanismAnswer `split_push → lane_trade` · **source = counter.md CTR-004** (lane/poke) |

**provenance แยกตาม field:** split_push (Marja เป็น split pusher) ← synergy.md Pair 7 §3 [FACT 22,102,110,114] ·
lane_trade (วิธีแก้ในเลนก่อนดาบ Z) ← counter.md CTR-004 [FACT 23,25,42,63] · CTR-004 เป็น poke/lane counter
**ไม่ได้ระบุ split push** จึงไม่ถูกใช้เป็น source ของ threat (แก้ตามรีวิว provenance ก่อน commit)

counter book: evidence 15 · threats 9 (เพิ่ม marja) · **น้ำหนัก counter_evidence ยัง 0 → อันดับไม่ขยับ**

---

## 6. ★★ ยืนยันว่า ranking ไม่เปลี่ยน (STEP 8)

| หลักฐาน | ผล |
|---|---|
| `test_passing_the_book_never_changes_the_ranking` | ✅ ทุกตาใน fixture (18 ตา) totals เท่าเดิมถึงทศนิยมที่ 12 |
| `test_the_two_knowledge_layers_together_still_change_nothing` | ✅ counter_book + synergy_book พร้อมกันก็ไม่ขยับ |
| `test_recommend_regression.py` (snapshot 216 ตา) | ✅ ผ่านเหมือนเดิม (ไม่แตะเส้นที่ไม่ส่ง book) |
| full suite | ✅ **650 passed · 11 skipped** (เดิม 604 → +46 ของ synergy) |
| `test_opening_the_weight_changes_the_ranking` | ✅ เปิดน้ำหนักแล้วขยับจริง — ไม่ใช่ dead code |

`synergy_evidence` weight = **0.0** · `synergy_adj` = 0 · `synergy` เท่าเดิม · ไม่มี threshold tuning

---

## 7. test count

`tests/unit/test_synergy_knowledge.py` — **46 ข้อ** ครอบคลุม: provenance · validator · status/unknown ·
undirected matching · association≠mechanism · DataCheck สดตรงกับไฟล์ · summary/explain/coverage/quality ·
engine integration (weight 0 / not dead code) · STEP 7 marja

---

## 8. deliverable ครบ

| STEP | ผล |
|---|---|
| 1 audit | [docs/33](33-synergy-knowledge-audit.md) |
| 2 data model | `SynergyEvidence` — 12 field ตามสเปค |
| 3 association ↔ mechanism | แยกเป็น `SynergyAssociation` vs `SynergyEvidence` ระดับ type |
| 4 DataCheck | เทียบ expected_synergy · ไม่ตัดสิน mechanistic truth |
| 5 source | 8/8 มี source · ไม่มีก็ UNKNOWN (ไม่มีข้อไหนต้อง) |
| 6 alias | doria → unresolved/unknown · ไม่ assume |
| 7 marja | threat + answer + mechanism matching ทำงาน |
| 8 no score change | weight 0 · 650 passed · อันดับไม่ขยับ |

### ทำต่อได้เมื่อมีหน้าต่างสะอาด (ไม่ใช่งาน M2A)
1. ยืนยัน doria = dolia → ปลดล็อก SYN-004
2. เปิดน้ำหนัก `synergy_adj` / `synergy_evidence` เมื่อ benchmark บอกว่าควรเท่าไร
3. เปลี่ยนตัวเทียบของ `synergy` จาก prior เป็น expected (docs/32 §8 ข้อ 6)
