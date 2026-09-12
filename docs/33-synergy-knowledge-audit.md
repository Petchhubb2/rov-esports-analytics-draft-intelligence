# 33 — Synergy Knowledge Audit

PHASE M2A · STEP 1 · 2026-09-12 · **audit ก่อนสร้าง representation — ยังไม่เปิดน้ำหนัก ไม่แตะอันดับ**

ต่อจาก [docs/32](32-synergy-audit.md) (M1.5) ซึ่งพิสูจน์ว่า co-occurrence ≠ synergy
เอกสารนี้ลงลึกถึงระดับโค้ดและเทสต์ เพื่อล็อกว่า M2A จะสร้างอะไรและ **จะไม่แตะอะไร**

> **M2A ทำแค่ representation** — ถอด `synergy.md` เป็นข้อมูลที่ trace ได้ พร้อม DataCheck
> **ไม่ใช่** การเพิ่มคะแนนหรือปรับน้ำหนัก · หน้าต่างสะอาด > 2026-09-06 = **0 เกม** ([docs/32](32-synergy-audit.md) · [[rov-eval-windows-consumed]])

---

## 1. synergy ในโค้ดตอนนี้ — สองเส้นทาง หนึ่งเปิดหนึ่งปิด

| # | ที่อยู่ | component | น้ำหนัก | ตัวเทียบ | สถานะ |
|---|---|---|---|---|---|
| 1 | [`recommend.py:768` `_synergy_with()`](../packages/core/rov/draft/recommend.py) | `synergy` | **0.05 → 0.28** (dynamic) | `prior` (0.5) | ✅ มีน้ำหนักจริง |
| 2 | [`recommend.py:665` `_synergy_adjusted()`](../packages/core/rov/draft/recommend.py) | `synergy_adj` | **0.0** | `expected_synergy()` | ✅ ทำงาน · ปิดตั้งแต่ PHASE B |

ทั้งคู่ใช้สูตร `stats.counter_score` เดียวกัน ต่างที่ **ตัวเทียบ** เท่านั้น (ยืนยันซ้ำจาก docs/32 §1)

```
synergy      (shrink(g,w,0.5)  − 0.5)           × 100 × conf(g)     ← ปนความแข็งรายตัว
synergy_adj  (shrink(g,w,exp)  − exp)           × 100 × conf(g)     ← หัก expected แล้ว
             exp = expected_synergy(stats, a, b)   [stats.py:288]
```

`weights_for()` ([recommend.py:116](../packages/core/rov/draft/recommend.py)) ดัน `synergy` จาก 0.05 ขึ้นไปได้ถึง ~0.28
ตามจำนวนตัวที่ทีมเราเปิด — **นี่คือน้ำหนักดิบที่ M1.5 เตือนว่า 15.9% ของคู่อาจชี้ผิดทาง**
M2A **ไม่แตะ** เส้นนี้ (แตะคือเปลี่ยนพฤติกรรมโดยไม่มีหน้าต่างพิสูจน์)

### 1.1 `compute_synergies()` — ที่มาของ association

[`stats.py:265`](../packages/core/rov/draft/stats.py) นับคู่ที่อยู่**ทีมเดียวกัน** เก็บทิศทางเดียว (เรียงชื่อ)
เป็น `MatchupStat` (games, wins) docstring เตือนเองว่า *"ปนเปื้อนด้วยทีมเก่งเล่นคู่นี้บ่อย"*

> **ข้อสรุปข้อ 1:** ตัวเลข co-occurrence นี้คือ **association** ไม่ใช่ mechanism
> M2A ต้องไม่ให้มันถูกเรียกว่า "synergy" โดยอัตโนมัติ (STEP 3)

---

## 2. data model ที่มี — และช่องที่ยังว่าง

| ของที่มี | ที่อยู่ | synergy มีเทียบเท่าไหม |
|---|---|---|
| `CounterEvidence` (pydantic) | [`counterknowledge.py:140`](../packages/core/rov/draft/counterknowledge.py) | ⛔ **ยังไม่มี `SynergyEvidence`** |
| `CounterBook.load()` glob YAML | `counterknowledge.py:224` | ⛔ ยังไม่มี `SynergyBook` |
| `Source · DataCheck · Condition` | [`macro/plays.py:51,62,84`](../packages/core/rov/macro/plays.py) | ✅ reuse ได้ตรง ๆ |
| `Confidence` enum | [`enums.py:232`](../packages/core/rov/domain/enums.py) | ✅ |
| `expected_synergy()` | `stats.py:288` | ✅ เป็นตัวเทียบที่ถูกต้องของ DataCheck |
| validator 4 ตัว | `counterknowledge.py:173-211` | ✅ ยกโครงได้ |

**สิ่งที่ synergy ไม่มีและ counter มี:** ทิศทาง. counter เดิน `target ← counter` มีหัวมีหาง
synergy เป็น `A + B → ผลรวม` **ไม่มีทิศทาง** — `find_matches()` จึงต้องจับคู่แบบ undirected
และ **ไม่มี** เส้น mechanism-inference (threat→answer) เพราะ synergy ไม่มี threat (docs/32 §6.1)

---

## 3. `synergy.md` — 8 pair ชั้น 1 ครบทุกช่อง

[`external_knowledge/.../synergy.md`](../external_knowledge/rov-claude-kit/knowledge/synergy.md) §1 มี 8 pair
แต่ละ pair มี Synergy Type · Reason · Gameplay Interaction · Condition · Expected Result · Weakness · Source ครบ

ช่องที่ต้องแยกตาม STEP 3 → map เข้าฟิลด์:

| STEP 3 | มาจาก synergy.md | เก็บที่ไหนใน M2A |
|---|---|---|
| **association** | (ไม่มีในไฟล์ — เป็นตัวเลข) | **วัดจาก `compute_synergies()` ไม่ใช่ฟิลด์ในความรู้** |
| mechanism | `Synergy Type` + `Gameplay Interaction` | `synergy_type` + `mechanism` + `mechanism_detail` |
| condition | `Condition` | `condition: [Condition]` |
| expected result | `Expected Result` | `expected_result` |
| (weakness) | `Weakness` | `weakness` |

> **association ไม่อยู่ในความรู้** ตรงกับ field list ของ STEP 2 ที่ **ไม่มี** ช่อง association
> มันถูกวัด ไม่ได้ถูกประกาศ — DataCheck คือสะพานที่เอาสองฝั่งมายืนคู่กันโดยไม่ทับกัน

---

## 4. DataCheck — คำนวณใหม่จาก 861 เกม ด้วยสูตรที่ shipping จริง

วัดด้วย `_synergy_adjusted` per-pair term จริง: `(shrink(g,w,exp) − exp) × 100 × conf(g)`
(ต่างจาก docs/32 §4 ที่ใช้ค่าประมาณรอบแรก — **verdict เท่ากันทุกข้อ** ต่างแค่ magnitude)

| pair | เกม | raw(assoc) | exp | adjE | score | verdict |
|---|---|---|---|---|---|---|
| rouie + capheny | 29 | 0.492 | 0.516 | 0.500 | −0.81 | **disagree** |
| teemee + capheny | 37 | 0.448 | 0.470 | 0.434 | −1.96 | **disagree** |
| ming + capheny | 4 | — | — | — | — | insufficient (< 8) |
| **dolia + tachi** ⚠️ | 51 | 0.469 | 0.473 | 0.459 | −0.88 | **unresolved** (§5) |
| krizzix + liliana | 10 | 0.475 | 0.502 | 0.476 | −0.64 | **disagree** |
| krizzix + zuka | 2 | — | — | — | — | insufficient (< 8) |
| rouie + marja | 34 | 0.562 | 0.557 | 0.589 | +1.71 | **agree** |
| chaugnar + hayate | 3 | — | — | — | — | insufficient (< 8) |

- **สมมติ doria = dolia:** agree 1 · disagree 4 · insufficient 3 → ตรงกับ docs/32 และโจทย์ M2A เป๊ะ
- **เมื่อ dolia+tachi เป็น unresolved (§5):** agree 1 · disagree 3 · insufficient 3 · **unknown 1**

> DataCheck **ไม่ตัดสิน mechanistic truth** (STEP 4) — `disagree` แปลว่า "ผลแพ้ชนะทั้งเกม
> ไม่ยืนยัน" ซึ่งเป็น**คนละมิติ**กับ "กลไกทำงานไหม" ทีมเก่ง ฟอร์มวันนั้น อีก 4 ตัวในคอมพ์
> และการที่ตัวอย่างถูกคัดด้วยการแบน ล้วนแทรกอยู่ในตัวเลขนั้น · **ห้าม overwrite knowledge**

---

## 5. ⚠️ `Doria` ยังยืนยันไม่ได้ว่าคือ `dolia` — ตรวจแล้วในฐานข้อมูลจริง

```
configs/draft/heroes.yaml : มี  dolia (id: dolia, name_en: Dolia)  · ไม่มี doria เลย
HERO_ALIASES              : ไม่มี doria → dolia  (parser.py:143)
```

synergy.md Pair 4 เขียน **"Doria (ดอเรีย)"** — ยังแยกไม่ออกด้วยข้อมูลที่มีว่า

1. เป็น `dolia` คนละคำทับศัพท์ (ไทย "ดอเรีย" · Liquipedia "Dolia") — **น่าจะใช่ แต่ยังไม่มีหลักฐาน**
2. เป็นฮีโร่ที่ไม่เคยปรากฏในลีกที่เก็บมา

> **กติกา M2A (STEP 6):** record นี้ต้อง `status = unknown` · `unresolved: [doria]`
> · **ห้ามใช้ใน matching / scoring / benchmark** จนกว่าจะยืนยัน แล้วเพิ่มเข้า `HERO_ALIASES`
> · ห้ามลบความรู้ทิ้ง — กลไก "ult reset → double ult" เป็นข้อเท็จจริงของตัวเกม เก็บไว้แต่ปิดการใช้งาน

เป็นบทเรียนเดียวกับ `flw_mm` / `bolt_baron` ([docs/09](09-build-log.md))

---

## 6. Marja — มีความรู้ counter แต่ระบบเอื้อมไม่ถึง (STEP 7)

[docs/31 §4.2](31-hero-knowledge-coverage.md): `marja` presence **72%** เป็น **target** ใน counter.md
ถึงสองที่ (CTR-002 · CTR-004) **แต่ยังไม่มี threat tag** → mechanism matching ใช้กับ marja ไม่ได้เลย

- ปัจจุบัน [`knowledge/counter/direct_hero.yaml`](../knowledge/counter/direct_hero.yaml): marja โผล่เป็น target ของ `mina/murad/ryoma/hayate` (`lane_trade`) เท่านั้น — **ไม่มี `threats:` ไม่มี `capabilities:`**
- STEP 7 = เติม representation 4 มิติ (threat · capability · mechanism · condition) ให้ marja **เท่าที่มี source**
- source แยกตาม field (สำคัญ — อย่าใช้ source เดียวครอบ): **threat `split_push` ← synergy.md Pair 7 §3 "Dual Side Push"**
  · **mechanism `lane_trade` (วิธีแก้ในเลนก่อนดาบ Z) ← counter.md CTR-004** ซึ่งเป็น poke/lane counter **ไม่ได้ระบุ split push**
  — ทั้งสองแหล่งมีอยู่แล้ว (docs/31 §6 ข้อ 1 ยืนยันว่าทำได้ทันที)
- ห้ามเติม fact ที่ไม่มี source (เช่น immortal ult เป็น capability ในบริบท synergy เท่านั้น ยังไม่มี counter.md บรรทัดรองรับให้เป็น mechanism → คง UNKNOWN)

---

## 7. เทสต์ที่มีอยู่ — อะไรคุ้ม synergy บ้าง

| เทสต์ | คุ้มอะไร | M2A ต้องไม่ทำให้ fail |
|---|---|---|
| [`test_recommend_regression.py`](../tests/unit/test_recommend_regression.py) | 216 ตา snapshot เป๊ะ | ✅ เส้นที่ไม่ส่ง book ต้องไม่ขยับ |
| `test_recommend_factors.py::test_synergy_adj_*` | `synergy_adj` น้ำหนัก 0 / เปิดแล้วขยับ | ✅ ต้องคง 0 |
| `test_counter_knowledge.py` | โครง `find_matches`/`explain`/UNKNOWN | ✅ template — mirror มาทำ synergy |
| `test_m15_guards.py` | หน้าต่างสะอาด · fingerprint · quality | ✅ เพิ่มความรู้ได้ fingerprint ขยับได้ |

**ยังไม่มี** เทสต์ที่แตะ `SynergyEvidence`/`SynergyBook` เลย (เพราะยังไม่มีของ) → M2A ต้องสร้าง

---

## 8. สิ่งที่ M2A จะสร้าง · จะไม่แตะ

### สร้าง (representation ล้วน)
1. `rov/draft/synergyknowledge.py` — `SynergyEvidence` · `SynergyBook` · `find_matches` (undirected) · `explain` · `coverage` · `quality_table` — mirror counter
2. `knowledge/synergy/hero_pairs.yaml` — 8 pair จาก synergy.md พร้อม `data_check` (§4) + วินัย alias (§5)
3. `SynergyAssociation` + `measure_association()` — วัด co-occurrence แยกจากความรู้ (STEP 3) โดย **เรียก `expected_synergy()` เดิม ไม่เขียนสูตรซ้ำ**
4. component `synergy_evidence` ใน recommend (**น้ำหนัก 0**) + `s.synergy_matches`
5. เติม marja threat/capability/answer ใน counter book จาก source ที่มี (STEP 7)
6. เทสต์ `test_synergy_knowledge.py` + regression "book ไม่เปลี่ยนอันดับ"

### ⛔ จะไม่แตะ (เปลี่ยนพฤติกรรม = ต้องมีหน้าต่างพิสูจน์ ซึ่งว่างเปล่า)
- น้ำหนัก `synergy` (0.05→0.28) · `synergy_adj` (0) · ตัวเทียบของ `synergy`
- `expected_synergy()` (แก้ = fit บนข้อมูลที่ดูแล้ว)
- อันดับ/คะแนนของทุกตาใน fixture — **ต้องเท่าเดิมหลักทศนิยมที่ 12**
