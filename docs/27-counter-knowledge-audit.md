# 27 — Counter Knowledge Audit

PHASE M1 · STEP 1 · 2026-09-11 · **ยังไม่แตะโค้ด**

> **หมายเหตุเลขเอกสาร** คำสั่งขอ `docs/26-counter-knowledge-audit.md` แต่เลข 26
> ถูกใช้ไปแล้วกับ [26-team-comp-page.md](26-team-comp-page.md) เมื่อวันเดียวกัน
> ชุด M1 จึงเลื่อนเป็น **27 (audit) · 28 (spec) · 29 (report)**

---

## 1. Counter score ตอนนี้มาจากไหน

มีสามชั้น อยู่ใน [`recommend.py`](../packages/core/rov/draft/recommend.py) ทั้งหมด

| component | น้ำหนักตอนนี้ | แหล่งข้อมูล | สถานะ |
|---|---|---|---|
| `counter` | **0.08 → 0.44** (ไต่ตามตัวที่ศัตรูเปิด) | matchup context=TEAM | ✅ ทำงาน |
| `lane_counter` | **0.0** | matchup context=LANE | ✅ ทำงาน · ปิดอยู่ |
| `trait_counter` | **0.0** | `strong_against_traits` | ⛔ **ตายสนิท** |

### ชั้นที่ 1 — `counter` (ตัวเดียวที่มีน้ำหนักจริง)

```
_counter_against()  →  stats.counter_score(games, wins, prior)
                    =  (shrink(g, w, prior) − prior) × 100 × confidence(g)
```

- นับคู่ที่ **อยู่คนละทีมในเกมเดียวกัน** (`MIN_PAIR_GAMES = 8`)
- เฉลี่ยต่อ **จำนวนศัตรูที่เปิดมา** ไม่ใช่ต่อคู่ที่มีข้อมูล — คู่ที่ไม่รู้จึงถ่วงลงหาศูนย์เอง
- มี 1,818 คู่ในชุดข้อมูล

### ชั้นที่ 2 — `lane_counter`

สูตรเดียวกันเป๊ะ (`ScoredPair.counter_score`) ต่างแค่บริบท — นับเฉพาะคู่ที่ยืนเลนเดียวกัน
`MIN_LANE_PAIR = 3` · 680 คู่ · เปิดอยู่ที่น้ำหนัก 0 ตั้งแต่ PHASE B

### ชั้นที่ 3 — `trait_counter` ⛔

```python
if not (hero.strong_against_traits or hero.weak_against_traits):
    return None      # ← ทุกฮีโร่ ทั้ง 119 ตัว เข้าทางนี้
```

กลไกเขียนเสร็จแล้วและมีเทสต์พิสูจน์ว่าใช้ได้
(`test_trait_counter_works_once_traits_exist`) **แต่ไม่มีข้อมูลป้อนเลยสักตัว**

นี่คือ **ช่องเสียบที่ M1 ต้องมาเสียบ** ไม่ใช่โค้ดที่ต้องเขียนใหม่

---

## 2. ตอบคำถาม audit ทีละข้อ

| คำถาม | คำตอบ |
|---|---|
| ใช้ context ระดับไหน | **คู่ฮีโร่** แล้วเฉลี่ยข้ามศัตรู — ไม่มีระดับ threat ไม่มีระดับ composition |
| hero-vs-hero หรือ team-level | **hero-vs-hero ล้วน** `analyze()` มีระดับทีมแต่ไม่ได้ต่อเข้ากับ counter |
| มี mechanism ไหม | **ไม่มีเลย** ตัวเลขบอกว่า "คู่นี้ชนะมากกว่า" ไม่บอกว่า **เพราะอะไร** |
| มี condition ไหม | **ไม่มีเลย** เข้าเงื่อนไขเดียวคือ `games >= 8` แล้วใช้ตลอด ไม่ว่าเฟสไหน เลนไหน |
| provenance อยู่ตรงไหน | **counter ไม่มี provenance** — เป็น `derived_from_data` โดยพฤตินัยแต่ไม่เคยติดป้าย |
| แยก pick/ban ไหม | **ไม่แยก** M0.75 แยกที่ *น้ำหนัก* แล้ว แต่ counter evidence ยังตีความเดียว |

### ตัวอย่างของปัญหา

ตอนนี้ระบบพูดได้แค่

```
COUNTER  +2.9   จาก 3/5 คู่ที่มีข้อมูล · เด่นเมื่อเจอ ybneth (+2.9)
```

แต่ตอบไม่ได้ว่า **ทำไม** · ต้องเกิดอะไรก่อน · เสี่ยงอะไร · ใครบอก

---

## 3. ⚠️ ผลตรวจที่สำคัญที่สุด — ข้อมูลเราค้าน counter.md เป็นส่วนใหญ่

เอาข้ออ้าง Direct Hero Counter ทั้ง 15 คู่จาก
[`counter.md`](../external_knowledge/rov-claude-kit/knowledge/counter.md)
มาเทียบกับ matchup จริง 861 เกม

| rule | counter | vs target | เกม | adj | score | ข้อมูลเราว่า |
|---|---|---|---|---|---|---|
| CTR-001 | billow | rouie | 43 | 0.507 | **+0.40** | ✅ เห็นด้วย |
| CTR-001 | tachi | rouie | 25 | 0.491 | −0.41 | ❌ ไม่เห็นด้วย |
| CTR-001 | skud | rouie | 22 | 0.442 | **−2.44** | ❌ ไม่เห็นด้วย |
| CTR-001 | qi | rouie | 29 | 0.458 | −2.08 | ❌ ไม่เห็นด้วย |
| CTR-001 | omen · aoi · zata | rouie | 0 · 4 · 6 | — | — | ⚪ ข้อมูลไม่พอ |
| CTR-002 | mina | omen · marja | 0 · 6 | — | — | ⚪ ข้อมูลไม่พอ |
| CTR-003 | chaugnar | ybneth | 14 | 0.591 | **+2.89** | ✅ เห็นด้วย |
| CTR-004 | murad | marja | 16 | 0.500 | +0.00 | ❌ ไม่เห็นด้วย |
| CTR-004 | ryoma | marja | 75 | 0.467 | −2.38 | ❌ ไม่เห็นด้วย |
| CTR-004 | hayate | marja | 51 | 0.420 | **−5.05** | ❌ ไม่เห็นด้วย |
| CTR-005 | liliana | iggy | 26 | 0.464 | −1.66 | ❌ ไม่เห็นด้วย |
| CTR-005 | sinestrea | iggy | 18 | 0.500 | +0.00 | ❌ ไม่เห็นด้วย |

**เห็นด้วย 2 · ไม่เห็นด้วย 8 · ข้อมูลไม่พอ 5**

### นี่ไม่ได้แปลว่าใครผิด — และห้ามสรุปว่าใครผิด

โปรเจกต์นี้เคยเจอสถานการณ์เดียวกันแล้วกับ macro rule และตัดสินใจไว้แล้วว่า
([`plays.py` · `DataCheck`](../packages/core/rov/macro/plays.py))

> ความรู้จากโค้ชเป็น**ความรู้เชิงกลไก** ส่วนข้อมูลของเราวัด**ผลแพ้ชนะของทั้งเกม**
> สองอย่างนี้ไม่เท่ากันและขัดกันได้โดยไม่มีใครผิด เก็บทั้งคู่ไว้ให้เห็นพร้อมกัน
> ดีกว่าเลือกเชื่อข้างเดียวเงียบ ๆ

เหตุผลเชิงโครงสร้างที่ทั้งสองฝั่งขัดกันได้โดยไม่มีใครโกหก

1. **คนละคำถาม** — "Tachi ผลัก Rouie ออกจากวงวาร์ปได้ไหม" (จริง/เท็จเกี่ยวกับตัวเกม)
   ไม่ใช่คำถามเดียวกับ "เกมที่ Tachi อยู่ตรงข้าม Rouie ฝ่าย Tachi ชนะกี่ %"
2. **ตัวอย่างถูกคัดมาแล้ว** — `rouie` ถูกแบน **565 ครั้ง** จาก 861 เกม
   เกมที่ Rouie ได้ลงจริงคือเกมที่อีกฝั่ง**เลือกจะไม่แบน** ซึ่งไม่ใช่ตัวอย่างสุ่ม
3. **ผลรวมทั้งเกมกลบกลไกเฉพาะจุด** — counter ในเลนช่วงต้นเกมสำเร็จ
   แต่แพ้เกมเพราะเรื่องอื่น ตัวเลขจะบันทึกว่า "ไม่เห็นด้วย"
4. **`hayate vs marja` 51 เกม −5.05** ชัดเจนพอที่จะบอกว่า **เงื่อนไขสำคัญ** —
   counter.md ระบุไว้เองว่าใช้เฉพาะ "เลน 1v1 ก่อน Marja ได้ดาบ Z"
   แต่ตัวเลขของเรานับ**ทุกเกม**ที่สองตัวนี้อยู่คนละฝั่ง รวมเกมที่ Marja ไป Carry ด้วย

**ข้อ 4 คือหัวใจของ M1** — ความขัดแย้งส่วนหนึ่งไม่ใช่ความขัดแย้งจริง
แต่เป็นเพราะ**ตัวเลขไม่รู้จัก condition** ที่ความรู้ระบุไว้แล้ว

### สิ่งที่ผลนี้บังคับให้ spec ต้องทำ

- ห้ามยุบ mechanism knowledge ลงเป็นตัวเลขเดียวกับ matchup
- ต้องมี `DataCheck` ต่อ CounterEvidence ทุกข้อ
- ข้อที่ข้อมูลเราค้าน **ห้ามมี confidence HIGH** ในมุมมองที่รวมแล้ว
  (validator แบบเดียวกับ `_contradicted_claims_cannot_be_high`)
- 5 ข้อที่ข้อมูลไม่พอต้องเป็น **UNKNOWN** ไม่ใช่ 0 และไม่ใช่ "เชื่อความรู้ไปก่อน"

---

## 4. Counter Knowledge ที่มีอยู่ — นับของจริง

[`counter.md`](../external_knowledge/rov-claude-kit/knowledge/counter.md) · 22,827 ตัวอักษร

| ชั้น | จำนวน | มี mechanism | มี condition | มี risk | มี source |
|---|---|---|---|---|---|
| 1 · Direct Hero Counter | **5 rule** (CTR-001…005) | ✅ ทุกข้อ | ✅ ทุกข้อ | ✅ ทุกข้อ | ✅ ทุกข้อ |
| 2 · Role Counter | 3 (assassin · tank/CC · poke) | ✅ | ⚪ โดยนัย | ⛔ | ✅ |
| 3 · Composition Counter | 2 (heavy CC · rouie warp) | ✅ | ⚪ โดยนัย | ⛔ | ✅ |
| 4 · Problem-Based | 4 คำถาม | ✅ | ⛔ | ⛔ | ✅ |
| 5 · Counter Rules | 4 (IF/THEN/BECAUSE) | ✅ | ✅ | ⛔ | ✅ |
| 6 · Tag System | 7 counter tag · 5 threat tag · 5 gate | — | — | — | — |

**ครอบคลุมฮีโร่ 25 ตัว ทุกตัวมีอยู่ใน `heroes.yaml` แล้ว** และเป็นตัวกลางเมต้าจริง

```
rouie 88.3%  ·  sinestrea 81.8%  ·  marja 72.2%  ·  elandorr 72.5%
florentino 58.0%  ·  toro 58.4%  ·  billow 52.7%  ·  hayate 47.2%
```

แต่ก็มีตัวที่แทบไม่มีใครใช้ — `chaugnar` 4.1% · `aoi` 6.6% · `krizzix` 10.7%
ซึ่งจะทำให้ `DataCheck` ของ rule ที่พึ่งตัวพวกนี้เป็น `insufficient` เกือบแน่นอน

### แต่ละ record มีครบตาม data contract ที่คำสั่งขอหรือยัง

| field ที่ต้องการ | counter.md มีไหม |
|---|---|
| target · counter · counter_type | ✅ ครบทั้ง 5 |
| mechanism | ✅ ครบ และแยกย่อยได้ (Burst / Displacement) |
| condition | ✅ ครบ |
| risk | ✅ ครบ |
| confidence | ✅ ครบ (HIGH ทั้ง 5) |
| source | ✅ ครบ พร้อมชื่อคลิปและเลขอ้างอิง |
| **objective_scope** | ⛔ **ไม่มี** ต้องตัดสินใจเองใน spec |
| **status** | ⛔ **ไม่มี** ต้องมาจาก DataCheck |

---

## 5. สิ่งที่ reuse ได้ — ไม่ต้องเขียนใหม่

นี่คือส่วนที่สำคัญที่สุดของ audit เพราะคำสั่งห้ามรื้อของเดิม

### 5.1 ระบบ provenance ครบชุดอยู่แล้ว ✅

[`rov/macro/plays.py`](../packages/core/rov/macro/plays.py) มีครบและผ่านการใช้งานจริงกับ 42 macro rule

| ของเดิม | ใช้กับ CounterEvidence ได้ทันที |
|---|---|
| `SourceType` 5 ชนิด + `SOURCE_LABEL` ไทย | ✅ counter.md เป็น `literature` / `coach_input` |
| `Source(type, ref, detail, url)` | ✅ |
| `Confidence` enum | ✅ |
| `Condition(cue, fact, op, value)` | ✅ ตรงกับ field `condition` ที่ spec ขอ |
| `DataCheck(verdict, detail, n)` | ✅ **ตรงกับปัญหา §3 พอดี** |
| `_assumption_cannot_be_high` validator | ✅ ลอกรูปแบบมาใช้ |
| `_contradicted_claims_cannot_be_high` | ✅ **ต้องมี** ตาม §3 |
| `MacroBook.load()` อ่าน YAML ทั้ง dir + กัน id ซ้ำ | ✅ ลอกรูปแบบ |

> **ข้อสรุป:** ไม่ต้องประดิษฐ์ provenance ใหม่เลย มีของที่ผ่านการใช้งานแล้ว

### 5.2 ช่องเสียบใน engine มีอยู่แล้ว ✅

- `trait_counter()` + `derive_traits()` — กลไกพร้อม รอข้อมูล
- `strong_against_traits` / `weak_against_traits` ใน `Hero` — ช่องมีอยู่แล้ว ว่างอยู่
- `EXTRA_WEIGHTS = {... : 0.0}` — วิธีเพิ่ม factor ที่น้ำหนัก 0 พิสูจน์แล้วใน PHASE B
- `Component(key, label, raw, scaled, detail)` — ที่สำหรับคำอธิบาย มีอยู่แล้ว
- `Suggestion.objective` ∈ {pick, ban} — **M0.75 เพิ่งทำให้ STEP 7 ทำได้ง่าย**

### 5.3 vocabulary ของกลไก — มีบางส่วน ⚪

`herotraits.py` มี `HARD_CC` / `SOFT_CC` / `MOBILITY_TAGS` / `SHIELD_TAGS`

**แต่ใช้ derive mechanism ไม่ได้จริง** — ตรวจ `data/hero_traits.json` แล้วพบว่า

```
billow   all_effects: ["Control", "Heal", "Movement"]   hard_cc: []
capheny  all_effects: ["Area DMG", "Damage Boost", "Movement", ...]
```

Liquipedia ใช้ป้าย**หยาบ** (`Control`, `Movement`) ไม่ใช่ `Knock Back` ตามที่โค้ดคาด
ผลคือ `hard_cc` ว่างแม้กับตัวที่มี CC จริง และไฟล์ครอบคลุมแค่ **30/119 ตัว**

> **สรุป: mechanism capability ต้องมาจาก `counter.md` ซึ่งระบุไว้ตรง ๆ พร้อม source**
> ("Omen, Skud, Qi และ Tachi มีสกิลผลัก") **ห้าม derive จาก Liquipedia tag**
> เพราะจะได้ผลผิดแบบเงียบ ๆ

### 5.4 สิ่งที่ต้องเพิ่มจริง ๆ

| ต้องเพิ่ม | เหตุผล |
|---|---|
| `CounterEvidence` schema + loader | ไม่มีของเดิมที่ทำหน้าที่นี้ |
| ไฟล์ YAML ถอดจาก counter.md | ความรู้ยังเป็น markdown อ่านด้วยเครื่องไม่ได้ |
| Threat / Mechanism vocabulary | มีใน counter.md §6 แต่ยังไม่เป็นโค้ด |
| `objective_scope` ต่อ record | counter.md ไม่มี ต้องตัดสินใจใน spec |
| component ใหม่ที่น้ำหนัก 0 | ตาม STEP 6 |

---

## 6. ความเสี่ยงที่ audit เห็น — ต้องระวังใน spec

1. **ล่อให้ยุบเป็นคะแนนเดียว** — counter.md §6 เสนอ `Direct_Counter_Score +30%` มาให้เลย
   ถ้าทำตามทันทีจะได้ระบบที่เดิมพันบนตัวเลขที่ข้อมูลเราค้าน 8/15 ข้อ
   **STEP 6 สั่งไว้ถูกแล้วว่าเริ่มที่ representation ไม่ใช่ score**
2. **ตัวอย่างน้อยจนวัดไม่ได้** — 5/15 คู่มีข้อมูลไม่พอ และตัวอย่าง `chaugnar` (4.1% presence)
   จะไม่มีวันมีข้อมูลพอในชุดนี้ ต้องยอมรับ UNKNOWN ถาวร
3. **condition ที่เขียนเป็นภาษาคน** — "ก่อน Marja ได้ดาบ Z" ระบบยังไม่รู้เรื่องไอเทม
   ต้องยอมให้ condition เป็น `cue` ข้อความที่ยังประเมินอัตโนมัติไม่ได้
   แบบเดียวกับที่ macro rule ทำ และ**ต้องบอกผู้ใช้ว่ายังไม่ได้ตรวจให้**
4. **ban กับ pick ตีความกลับทาง** — "Mina counter Omen" ตอน pick แปลว่า
   "เอา Mina มาแก้ Omen" แต่ตอน ban ต้องกลายเป็น "อย่าปล่อย Mina ให้ศัตรู
   ถ้าเรามี Omen/Marja" ซึ่ง**ไม่ใช่ประโยคเดียวกันกลับหัว**
5. **จำนวน rule น้อยมากเทียบกับ 119 ฮีโร่** — 5 direct rule ครอบคลุม 5 target
   coverage จะต่ำมากและ**ต้องรายงานตัวเลขนั้นตรง ๆ** ไม่ใช่ขยายด้วยการเดา

---

## 7. พร้อมไป STEP 2 หรือยัง

**พร้อม** — และ audit นี้เปลี่ยนสองอย่างในแผนเดิม

1. `status` ใน data contract **ต้องผูกกับ `DataCheck`** ไม่ใช่ตั้งเองลอย ๆ
   เพราะ §3 พิสูจน์แล้วว่าความรู้กับข้อมูลขัดกันบ่อยกว่าที่คาด
2. `mechanism` **ต้องมาจาก counter.md ไม่ใช่ derive จาก Liquipedia tag**
   เพราะ §5.3 พิสูจน์แล้วว่าป้ายที่ดึงมาหยาบเกินและครอบคลุมแค่ 30/119

**ยังไม่ได้แตะโค้ดแม้แต่บรรทัดเดียว** ตามคำสั่ง STEP 1
