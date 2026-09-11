# 29 — Counter Knowledge Report

PHASE M1 · STEP 9 · 2026-09-11

อ่านคู่กับ [27 audit](27-counter-knowledge-audit.md) และ [28 spec](28-counter-knowledge-spec.md)

---

## 1. สรุปหนึ่งย่อหน้า

Counter เปลี่ยนจาก **ตัวเลขล้วน** เป็น **หลักฐานที่อธิบายตัวเองได้**
ระบบตอบได้แล้วว่า counter ใคร · เพราะกลไกอะไร · ต้องเกิดเงื่อนไขอะไร · เสี่ยงอะไร ·
มั่นใจแค่ไหน · ใครบอก · ใช้กับ pick หรือ ban

**แต่ครอบคลุมแค่ 6.6% ของตาจริง** เพราะความรู้ที่มีพูดถึงฮีโร่ 24 จาก 119 ตัว
ตัวเลขนี้รายงานตรง ๆ ไม่ได้ขยายด้วยการเดา

**ยังไม่เปิดน้ำหนักอะไรเลย** — 3,587/3,587 ตา คะแนนเหมือนเดิมเป๊ะ

---

## 2. สิ่งที่ reuse ได้ — ไม่ได้เขียนใหม่

audit §5 ชี้ไว้ว่าโครงสร้าง provenance มีครบแล้ว ผลคือ **ไม่ต้องประดิษฐ์อะไรใหม่**

| ของเดิม | ใช้ยังไง |
|---|---|
| `Source` · `SourceType` · `SOURCE_LABEL` | ใช้ตรง ๆ ทั้งชุด · counter.md เป็น `coach_input` |
| `Confidence` | ใช้ตรง ๆ |
| `Condition(cue, fact, op, value)` | ใช้ตรง ๆ เป็น field `condition` |
| `DataCheck(verdict, detail, n)` | ใช้ตรง ๆ — **หัวใจของ M1** |
| `_assumption_cannot_be_high` | ลอกมาเป็น validator ของ `CounterEvidence` |
| `_contradicted_claims_cannot_be_high` | ลอกมา และ**มันจับได้จริง 6 ข้อ** |
| `MacroBook.load()` (YAML dir + กัน id ซ้ำ) | ลอกรูปแบบมาเป็น `CounterBook.load()` |
| `EXTRA_WEIGHTS` ที่ 0.0 | ใช้กลไกเดิมของ PHASE B ไม่ได้คิดวิธีใหม่ |
| `Component` | ใช้ตรง ๆ เป็นที่แสดงผล |
| `Suggestion.objective` (M0.75) | ทำให้ STEP 7 เกือบฟรี |
| `stats.counter_score()` | ใช้คำนวณ `data_check` ทุกข้อ |

**ไม่ได้แตะ:** `weights_for` · `ban_weights_for` · `_counter_against` ·
`_lane_counter_against` · `role_fit` · candidate pool

---

## 3. สิ่งที่เพิ่ม

| ไฟล์ | บรรทัด | หน้าที่ |
|---|---|---|
| `rov/draft/counterknowledge.py` | ~420 | schema · loader · mechanism matching · explanation |
| `knowledge/counter/direct_hero.yaml` | ~560 | ความรู้ถอดจาก counter.md พร้อม data_check |
| `recommend.py` | ~55 | component `counter_evidence` ที่น้ำหนัก 0 + รายงาน |
| `tests/unit/test_counter_knowledge.py` | ~380 | 41 เทสต์ |
| `scripts/run_counter_coverage.py` | ~160 | วัด coverage ตาม STEP 9 |

### 3.1 โครงสร้าง `CounterEvidence`

ตรงตาม contract ใน STEP 2 ทุก field บวกอีก 4 ที่มีเหตุผลกำกับ ([28 §2.2](28-counter-knowledge-spec.md))

```
evidence_id · target · counter · counter_type · threat · mechanism
mechanism_detail · condition · unconditional · risk · confidence
source · objective_scope · lane · data_check   →  status (คำนวณ ไม่ได้ตั้งเอง)
```

### 3.2 Mechanism matching เดินสามขาจริง

```
Enemy Threat  →  Counter Mechanism  →  Candidate Capability
```

สองเส้นทาง — `direct` (source พูดถึงคู่นี้ตรง ๆ) และ `mechanism` (อนุมานข้ามคู่)
**เส้น mechanism ถูกลดความมั่นใจหนึ่งขั้นเสมอ** และมีเทสต์คุม

---

## 4. Counter coverage — ตัวเลขจริง

### 4.1 คลังความรู้

| รายการ | ค่า |
|---|---|
| evidence ทั้งหมด | **15** |
| ฮีโร่ที่เป็น target | 5 |
| ฮีโร่ที่เป็น counter | 14 |
| รู้ threat | **8/119 = 6.7%** |
| รู้ mechanism | **19/119 = 16.0%** |
| **ยังไม่รู้อะไรเลย** | **95/119 = 79.8%** |

### 4.2 ความครบของแต่ละ record

| รายการ | ค่า |
|---|---|
| มีกลไก + ความเสี่ยง + ที่มา ครบ | **15/15 = 100%** |
| มีเงื่อนไข (หรือประกาศว่าไม่มี) | **15/15 = 100%** |
| มี `data_check` | **15/15 = 100%** |
| ประเมินเงื่อนไขอัตโนมัติได้ | **5/15 = 33%** (เฉพาะ lane counter) |

### 4.3 ไปถึงตาจริงกี่ตา (200 ดราฟต์ · 3,587 ตา)

| | ตาที่มีหลักฐาน |
|---|---|
| รวม | **237/3,587 = 6.6%** |
| ตาเลือก | 199/1,991 = **10.0%** |
| ตาแบน | 38/1,596 = **2.4%** |

หลักฐานที่ยิงออกมา **direct 57 · mechanism 330** — เส้นทางกลไกทำงานจริง
และขยายความรู้ 15 ข้อออกไปได้กว้างกว่าคู่ที่ source พูดถึงตรง ๆ ราว 6 เท่า

ความมั่นใจ **LOW 300 · HIGH 46 · MEDIUM 41** — LOW เยอะเพราะเส้น mechanism
ถูกลดขั้นตามกติกา ซึ่งเป็นพฤติกรรมที่ตั้งใจ

### 4.4 ทำไมฝั่ง ban ถึงต่ำกว่ามาก (2.4% vs 10.0%)

**ไม่ใช่บั๊ก** — ตาแบนถามว่า "ถ้าปล่อยตัวนี้ให้ศัตรู เขาจะกดอะไร**ของเรา**ได้"
ซึ่งต้องรู้ว่า**เรา**เปิดอะไรไปแล้ว ที่ตาแบนเฟส 1 ยังไม่มีใครเปิดอะไรเลย
evidence ฝั่ง ban จึงว่างเปล่าโดยโครงสร้าง ตรงกับที่ spec §6.1 คาดไว้ล่วงหน้า

---

## 5. UNKNOWN coverage — ส่วนที่ต้องพูดให้ดัง

**79.8% ของฮีโร่ (95/119) ระบบไม่รู้อะไรเกี่ยวกับ counter เลย**

และระบบ**ไม่แกล้งทำเป็นรู้** — ฮีโร่เหล่านั้นไม่มี component `counter_evidence`
ไม่ใช่มี component ที่ค่า 0 ซึ่งจะอ่านว่า "ตรวจแล้ว ไม่ได้เปรียบ"

| กรณี | ระบบทำอะไร |
|---|---|
| ไม่ส่ง `counter_book` มา | ไม่มี component |
| ไม่รู้กลไกของ candidate | ไม่มี component (ไม่เดาจาก `hero_class`) |
| ไม่รู้ threat ของศัตรู | ไม่มี component |
| กลไกไม่ตรงกับภัย | ไม่มี match (เช่น cleanse ไม่ตอบ recall_warp) |
| เงื่อนไขเลนไม่ผ่าน | มี match แต่ `counts = False` |
| เงื่อนไขเป็นภาษาคน | `unchecked` + ขึ้นป้าย **"ระบบยังตรวจให้ไม่ได้ ต้องดูเอง"** |

### 5.1 ความรู้ที่มีแต่ระบบยังใช้ไม่ได้

- **`peel` ไม่มีกฎตอบภัยไหนเลย** — counter.md §2 อธิบายภัยจาก assassin ไว้
  แต่ §6 (Threat Tag System) ไม่มี tag สำหรับมัน การเพิ่ม tag เองจะเป็นการแต่งความรู้
  จึงปล่อยเป็นช่องว่างที่มองเห็นได้
- **เงื่อนไข 10/15 ข้อประเมินอัตโนมัติไม่ได้** เช่น "ก่อน Marja ได้ดาบ Z"
  ระบบยังไม่รู้เรื่องไอเทมและเวลาในเกม

---

## 6. ⚠️ ข้อมูลของเราค้านความรู้ 6 ใน 15 ข้อ

นี่คือผลที่สำคัญที่สุดของเฟสนี้ และมันถูกเก็บไว้ในระบบ ไม่ได้ปัดทิ้ง

| verdict | จำนวน |
|---|---|
| `agrees` — ข้อมูลเราเห็นด้วย | **2** |
| `disagrees` — ข้อมูลเราค้าน | **6** |
| `mixed` — เห็นด้วยบางส่วน | 2 |
| `insufficient` — ข้อมูลไม่พอ | 5 |

**status ที่ได้: verified 2 · inferred 13**

ทั้ง 6 ข้อที่ข้อมูลค้าน **ถูก validator บังคับให้ลด confidence เป็น MEDIUM**
ไม่ได้ลบทิ้ง เพราะความรู้เชิงกลไกกับผลแพ้ชนะทั้งเกมตอบคนละคำถาม —
เหตุผลเต็มใน [audit §3](27-counter-knowledge-audit.md)

ตัวอย่างที่หนักที่สุด `hayate` counter `marja` — counter.md บอก HIGH
แต่ข้อมูลเราได้ `-5.05` จาก 51 เกม **ข้อสังเกตที่บันทึกไว้ในไฟล์:**
Hayate เล่นเลน Dragon เป็นหลัก จึงอาจไม่เคยประกบ Marja ในเลนจริงตามเงื่อนไขที่ระบุ
— ตัวเลขไม่รู้จัก condition แต่ความรู้รู้

หน้าจอแสดงทั้งสองฝั่งพร้อมกันเสมอ

```
  ความมั่นใจ: MEDIUM
  ข้อมูลเรา:  ข้อมูลเราไม่เห็นด้วย · 51 เกม — counter_score -5.05 ...
```

---

## 7. เทสต์ที่เพิ่ม — 41 ตัว

`tests/unit/test_counter_knowledge.py`

| กลุ่ม | จำนวน | ตัวที่สำคัญที่สุด |
|---|---|---|
| ที่มาครบ | 5 | ทุก evidence ต้องมี source · กลไก · ความเสี่ยง |
| validator | 7 | **ข้อที่ข้อมูลค้านห้าม HIGH** · counter ตัวเองไม่ได้ · id ซ้ำไม่ได้ |
| direct counter | 2 | เจอคู่ตรง · ความมั่นใจไม่ถูกลด |
| mechanism match | 5 | **เดิน threat→mechanism→capability** · ลดขั้นความมั่นใจ · **กลไกผิดประเภทต้องไม่หลุด** |
| condition | 4 | เลนไม่ตรง = `unmet` · เลนตรง = `met` · ภาษาคน = `unchecked` |
| confidence / source | 5 | ไหลถึงคำอธิบาย · **บรรทัด "ข้อมูลเรา" บังคับ** |
| pick vs ban | 2 | ได้คนละประโยค · scope กรองได้ |
| ต่อกับ engine | 5 | **★★ ส่ง book เข้าไปแล้วอันดับไม่ขยับ** · ไม่ส่ง = ไม่มี component |
| coverage | 2 | รายงาน unknown ตรง ๆ |

**เทสต์ที่เป็นแกน**

```python
def test_passing_the_book_never_changes_the_ranking(ctx, book):
    """ความรู้ใหม่ทั้งก้อนเข้ามาแล้ว คะแนนต้องไม่ขยับแม้แต่หลักทศนิยมที่ 12"""

def test_a_capability_that_does_not_answer_the_threat_finds_nothing(book):
    """cleanse ไม่ได้ตอบ recall_warp — ต้องไม่มี match หลุดมา"""

def test_a_claim_our_data_contradicts_cannot_be_high_confidence():
    """docs/27 §3 — เกิดขึ้นจริง 6 ใน 15 ข้อ"""
```

**รวมทั้งโปรเจกต์ 582 ผ่าน · 11 skip · ruff ผ่าน** (จาก 541)

---

## 8. Regression result

| การวัด | ผล |
|---|---|
| 200 ดราฟต์ · 3,587 ตา · ส่ง book เข้าไป | **3,587/3,587 คะแนนเหมือนเดิมเป๊ะ** |
| regression fixture เดิม 216 ตา | ผ่าน ไม่แตะ |
| leakage tests 8 ตัว | ผ่าน |
| ban intelligence 29 ตัว | ผ่าน |
| ตาที่เปลี่ยน | **0** |

---

## 9. ยังไม่เปิดน้ำหนักอะไร

```python
EXTRA_WEIGHTS = {
    "composition":      0.0,
    "lane_counter":     0.0,
    "synergy_adj":      0.0,
    "trait_counter":    0.0,
    "counter_evidence": 0.0,   # M1 ← ใหม่ และเป็น 0
}
```

`counter` (0.08→0.44) กับ `ban_weights_for` **ไม่ถูกแตะเลย**

**ทำไมถึงยังเปิดไม่ได้แม้จะอยากเปิด:** หน้าต่าง evaluation ทั้งสองบาน
(validation และ holdout) ถูกดูไปแล้วใน M0.75 การ fit น้ำหนักบนนั้นคือ overfit
ที่มองไม่เห็น ต้องมีหน้าต่างใหม่ที่ยังไม่เคยสก็อร์ หรือเก็บเกมใหม่เพิ่ม

---

## 10. พร้อมสำหรับ M2 SynergyKnowledge หรือยัง

**พร้อม** โดยมีเงื่อนไข

### ที่พร้อม

- โครงสร้าง `CounterBook` / `CounterEvidence` ยกไปทำ `SynergyBook` ได้ตรง ๆ
- `DataCheck` pattern พิสูจน์แล้วว่าจับความขัดแย้งได้จริง (6/15)
- กติกา "weight = 0 แล้วต้องไม่ขยับ" มี benchmark คุมแล้ว
- `synergy.md` มีอยู่ใน external_knowledge แล้ว โครงเดียวกับ counter.md
- `synergy_adj` component เปิดรออยู่ที่น้ำหนัก 0 ตั้งแต่ PHASE B

### ที่ต้องระวังก่อนเริ่ม M2

1. **coverage จะต่ำแบบเดียวกัน** — อย่าตั้งเป้าว่า M2 จะครอบคลุมสูง
   ให้ตั้งเป้าว่าจะรายงานตัวเลขจริงได้ตรง ๆ
2. **synergy ปนเปื้อนหนักกว่า counter** — `_synergy_with()` เตือนไว้เองว่า
   ค่านี้ปน "ทีมเก่งเล่นคู่นี้บ่อย" ยังไม่ได้หักออก `DataCheck` ฝั่ง synergy
   จึงตีความยากกว่า ต้องใช้ `expected_synergy()` เป็นตัวเทียบ ไม่ใช่ prior เฉย ๆ
3. **ห้ามเปิดน้ำหนักใน M2 เช่นกัน** จนกว่าจะมีหน้าต่าง evaluation ใหม่
4. **`peel` ที่ค้างอยู่** ควรแก้ตอนที่มี threat vocabulary ใหม่ที่มี source รองรับ
   ไม่ใช่แต่งเพิ่มเอง

### สิ่งที่ควรทำก่อน M2 ถ้าเลือกได้

เก็บเกมใหม่หลัง 2026-09-06 เพื่อให้มีหน้าต่างสะอาดไว้ตัดสินน้ำหนัก
ตอนนี้ M1 สร้างความรู้ไว้แล้วแต่**ยังพิสูจน์ไม่ได้ว่ามันช่วย** ซึ่งเป็นหนี้ที่สะสมอยู่
