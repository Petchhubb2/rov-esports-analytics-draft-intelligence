# 34 — Synergy Knowledge Spec

PHASE M2A · STEP 2-8 · 2026-09-12 · **representation ล้วน · น้ำหนัก 0 · อันดับไม่ขยับ**

audit ที่นำมาสู่สเปคนี้อยู่ใน [docs/33](33-synergy-knowledge-audit.md) · ยกโครงมาจาก counter ([docs/28](28-counter-knowledge-spec.md))

---

## 1. หลักการเดียวที่คุมทุกอย่าง — association ≠ mechanism

docs/32 พิสูจน์ว่า **co-occurrence ไม่ใช่ synergy** (34/214 คู่พลิกเครื่องหมายเมื่อหัก expected)
สเปคนี้จึงแยกสองสิ่งนี้ออกจากกัน **ในระดับ type** ไม่ใช่แค่ตักเตือนในคอมเมนต์

| | association | mechanism |
|---|---|---|
| คำถาม | "สองตัวนี้ถูกเลือกด้วยกันบ่อย + คู่นี้ชนะกี่ %" | "สองตัวนี้ช่วยกันทำอะไร" |
| ที่มา | **วัด**จาก `compute_synergies()` (ข้อมูล) | **ความรู้**จาก synergy.md (มี source) |
| เก็บที่ | `SynergyAssociation` (dataclass, คำนวณสด) | `SynergyEvidence` (pydantic, ในไฟล์ YAML) |
| สะพาน | `DataCheck` — เอาสองฝั่งมายืนคู่กัน **โดยไม่ทับกัน** | |

> STEP 2 field list **ไม่มี** ช่อง `association` โดยเจตนา — มันถูกวัด ไม่ได้ถูกประกาศ

---

## 2. `SynergyEvidence` — schema (STEP 2)

[`rov/draft/synergyknowledge.py`](../packages/core/rov/draft/synergyknowledge.py)

| field | ชนิด | หมายเหตุ |
|---|---|---|
| `evidence_id` | str | อ้างกลับ `SYN-00n-a-b` |
| `entity_a` · `entity_b` | str | **ไม่มีทิศทาง** — `pair` เป็น `frozenset` |
| `synergy_type` | `SynergyType` | §6 Synergy Tag System (7 ป้าย) |
| `mechanism` | `SynergyMechanism` | กลไก enabler→payoff (6 ป้าย) จาก §1 |
| `mechanism_detail` | str | ลำดับการกดสกิลจริง (Gameplay Interaction) |
| `condition` | `[Condition]` | reuse จาก macro/plays |
| `unconditional` | bool | ต้องประกาศชัด ไม่ใช่ปล่อยว่างแล้วถือว่าใช่ |
| `expected_result` | str | ได้อะไรเมื่อกลไกทำงาน |
| `weakness` | str | จุดอ่อน/ตัวแก้ทาง |
| `confidence` | `Confidence` | HIGH/MEDIUM/LOW |
| `source` | `Source` | reuse — บังคับมี (STEP 5) |
| `objective_scope` | `pick`/`ban`/`both` | |
| `unresolved` | `[str]` | entity ที่ยังยืนยัน id ไม่ได้ (STEP 6) |
| `data_check` | `DataCheck?` | ฝั่ง association |

### 2.1 `status` มาจากหลักฐาน ไม่ได้ตั้งเอง

```
unresolved ไม่ว่าง        → unknown   (มาก่อนเสมอ — ไม่รู้ด้วยซ้ำว่าเป็นตัวไหน)
data_check = agrees        → verified
อื่น ๆ                     → inferred
```

`usable = status != "unknown"` — record ที่ unknown **ถูกกรองทิ้งใน `find_matches`** จึงไม่มีวัน match/score

### 2.2 validator ที่บังคับความซื่อสัตย์ (ยกจาก counter + เพิ่มของ synergy)

1. `assumption` → confidence HIGH ไม่ได้
2. `data_check = disagrees` → confidence HIGH ไม่ได้ (**KNOWLEDGE ≠ OUTCOME** แต่ก็ไม่ให้โม้)
3. synergy กับตัวเองไม่ได้ (`a != b`)
4. `unresolved` ต้องเป็นชื่อใน `{a, b}` เท่านั้น
5. **`unresolved` → confidence HIGH ไม่ได้** (ใหม่ · STEP 6)

---

## 3. vocabulary — ทุกป้ายมี source (STEP 5)

`SynergyType` = §6 Synergy Tag System: `global_warp` `gold_boost` `aoe_pull_burst`
`double_ult` `poke_siege` `front_to_back` `tag_farm`

`SynergyMechanism` = §1 Gameplay Interaction: `recall_warp` `gold_accel` `stat_buff`
`ult_reset` `engage_followup` `cleanse_cover`

> ⚠️ บาง pair `synergy_type` (§6 tag) กับ `mechanism` (§1 กลไก) **ไม่ตรงกันในต้นทาง**
> เช่น Ming+Capheny tag = `gold_boost` แต่กลไกเป็น `stat_buff` — เก็บทั้งสองตามที่ source เขียน
> **ไม่รวบให้ตรงกันเอง** (CLAUDE.md rule 3 · Chaugnar+Hayate ก็เป็นแบบเดียวกัน)

---

## 4. DataCheck — วัดเทียบ expected ไม่ใช่ prior (STEP 4)

`measure_association()` → `data_check_from_association()` :

```
raw            = shrink(g, w, 0.5)              ← association ถ่วงตัวอย่าง
expected       = expected_synergy(stats, a, b)  ← เรียกของเดิมใน stats.py ไม่เขียนซ้ำ
adjusted_score = (shrink(g,w,exp) − exp) × 100 × conf(g)   ← สัญญาณ synergy จริง

verdict:  games < 8            → insufficient
          adjusted_score > 0.05 → agrees
          adjusted_score < -0.05→ disagrees
          อื่น ๆ                → mixed
```

**ต่างจาก counter ตรงตัวเทียบ** — counter เทียบ `prior 0.5` แต่ synergy เทียบ `expected_synergy`
เพราะคู่ที่ต่างคนต่างเก่งจะดูดีทั้งที่อาจไม่เข้ากันเลย นี่คือบทเรียนหลักของ docs/32

> **DataCheck ไม่ตัดสิน mechanistic truth** — มันตอบว่า "ผลแพ้ชนะทั้งเกมยืนยันไหม"
> ซึ่งเป็นคนละมิติ: ตัวเลขนับทุกเกม ไม่กรองเงื่อนไข ไม่หักความแข็งทีม และตัวอย่างถูกคัดด้วยการแบน
> **ห้าม overwrite knowledge ด้วย match data** — ทำได้แค่ลด confidence และแสดงทั้งคู่

---

## 5. matching — undirected, direct-only (STEP 3 ต่อ)

`find_matches(book, candidate, ctx)` : สำหรับ ally แต่ละตัวใน `ctx.allies`
หา evidence ที่ `pair == {candidate, ally}` · ข้าม `not usable` · ข้าม scope ไม่ตรง

- **ไม่มีทิศทาง** — ถาม `rouie` โดยมี ally `marja` หรือถาม `marja` โดยมี ally `rouie` ได้ผลเดียวกัน
- **ไม่มีเส้น mechanism-inference** — counter เดิน `threat → answer → capability` แต่ synergy
  ไม่มี threat จึงจับคู่ตรง ๆ เท่านั้น (docs/33 §2) · ไม่เดาข้ามคู่โดยไม่มีกราฟที่มี source
- `condition_state`: cue ภาษาคน → `unchecked` (นับ แต่ติดป้ายว่ายังไม่ได้ตรวจ) · ไม่แกล้งทำเป็น met

---

## 6. alias normalization — Doria (STEP 6)

ฐานข้อมูลมี `dolia` ไม่มี `doria` · `HERO_ALIASES` ไม่มี mapping (docs/33 §5)

Pair 4 (Doria & Tachi) จึง:
- `entity_a: doria` · `unresolved: [doria]` → `status = unknown` → **ไม่ถูก match/score**
- `confidence: LOW` (validator บังคับว่าห้าม HIGH)
- `data_check: insufficient` — "51 เกมภายใต้สมมติฐาน doria=dolia ซึ่งยังไม่ยืนยัน วัดคู่ที่อาจไม่ตรงกับข้ออ้าง"
- ความรู้ (ult reset) **ไม่ถูกลบ** — เก็บไว้ แต่ปิดการใช้งาน

**เมื่อยืนยันได้** ว่า doria = dolia: เพิ่ม `"doria": "dolia"` ใน `HERO_ALIASES` แล้วแก้ record เป็น
`entity_a: dolia` ลบ `unresolved` — record จะ active ทันที (ตอนนั้นค่อยตั้ง confidence/verdict ใหม่)

---

## 7. STEP 7 — marja counter representation

docs/31 §4.2: marja เป็น target ใน counter.md แต่ไม่มี threat tag → mechanism matching ใช้ไม่ได้

เติมจาก source ที่มีอยู่แล้ว — **ไม่หาแหล่งใหม่** · แต่ละ field ชี้ source ที่รองรับจริง:
- ThreatTag ใหม่ `split_push` (ออฟเลนสายสเกล ดันเลนข้าง)
- `threats: [split_push]` ให้ marja · **source = synergy.md §1 Pair 7 "Dual Side Push" + §3**
  (⚠️ **ไม่ใช่** CTR-004 — CTR-004 เป็น poke/lane counter ไม่ได้พูดถึง split push)
- MechanismAnswer `split_push → [lane_trade]` · **source = counter.md CTR-004** (lane/poke กด Marja
  ก่อนได้ดาบ Z) · confidence MEDIUM · threat ที่มันตอบนิยามจาก marja HeroThreat (synergy.md)
- ใส่ `threat: split_push` ให้ evidence CTR-004 (murad/ryoma/hayate) — `threat` เป็น cross-reference
  ไปยัง marja HeroThreat (แบบเดียวกับ `recall_warp` ที่ CTR-001 อ้าง rouie threat) · `source` ของ
  evidence ยังเป็น CTR-004 ที่บันทึกตัว counter · **ไม่มี field ไหนถูก source เดียวครอบเกินที่มันกล่าวถึง**

ผล: `find_matches(counter_book, "mina", enemies=["marja"])` เดินเส้น mechanism ถึง marja ได้แล้ว
(น้ำหนัก `counter_evidence` ยัง 0 → อันดับไม่ขยับ)

---

## 8. STEP 8 — ห้ามเปลี่ยนคะแนน · เชื่อมโดยไม่ขยับอันดับ

- `EXTRA_WEIGHTS["synergy_evidence"] = 0.0` (เพิ่มใหม่) · `synergy_adj` ยัง 0 · `synergy` ยังเท่าเดิม
- component `synergy_evidence` เกิดเฉพาะเมื่อส่ง `synergy_book` และมี usable match — ไม่งั้น **ไม่มี** component (ไม่ใช่ 0)
- ผลต่ออันดับ: `base = Σ w_all.get(k,0) × scaled` · น้ำหนัก 0 → total ไม่ขยับแม้แต่ทศนิยมที่ 12
- output `explain()`/`report()`: ชนิด · กลไก · เงื่อนไข · ผลที่คาด · จุดอ่อน · ที่มา · ความมั่นใจ · ข้อมูลเรา
  · pick/ban ได้คนละประโยค

### เทสต์ที่ล็อกคุณสมบัติ ([test_synergy_knowledge.py](../tests/unit/test_synergy_knowledge.py) · 46 ข้อ)
- `test_passing_the_book_never_changes_the_ranking` — ★★ ทุกตา totals เท่าเดิม
- `test_opening_the_weight_changes_the_ranking` — พิสูจน์ว่าไม่ใช่ dead code
- `test_an_unresolved_record_never_matches` — doria ไม่มีวันโผล่
- `test_the_data_check_in_the_file_matches_a_live_recompute` — ตัวเลขในไฟล์ = คำนวณสด

---

## 9. ⛔ สิ่งที่สเปคนี้ **ไม่** ทำ

| ไม่ทำ | เหตุผล |
|---|---|
| เปิดน้ำหนัก synergy ตัวใด | หน้าต่างสะอาด > 2026-09-06 = 0 เกม ([[rov-eval-windows-consumed]]) |
| แก้ตัวเทียบของ `synergy` (prior→expected) | เปลี่ยนพฤติกรรมโดยไม่มีหน้าต่างพิสูจน์ = เดา |
| แก้ `expected_synergy()` ให้หักความแข็งทีม | ต้องมี team-strength model + จะกลายเป็น fit บนข้อมูลที่ดูแล้ว |
| เดา synergy ข้ามคู่ (mechanism route) | ยังไม่มีกราฟ enabler→payoff ที่มี source |
| ถือว่า doria = dolia | ยังไม่มีหลักฐาน (STEP 6) |
