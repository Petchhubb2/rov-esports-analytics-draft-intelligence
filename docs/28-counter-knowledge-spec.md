# 28 — Counter Knowledge Spec

PHASE M1 · STEP 2–7 · **เขียนก่อน implementation**

อ่าน [27 — audit](27-counter-knowledge-audit.md) ก่อน · spec นี้ตั้งอยู่บนผลของ audit

---

## 1. หลักที่ไม่ยอมแลก

| หลัก | ผลต่อการออกแบบ |
|---|---|
| **ห้ามยุบเป็น score เดียว** | `CounterEvidence` เป็น record ไม่ใช่ float · score เป็นผลพลอยได้ท้ายสุด |
| **UNKNOWN ต้องเป็น UNKNOWN** | ไม่มีข้อมูล = ไม่มี component ไม่ใช่ component ที่ค่า 0 |
| **ห้ามเดา game fact** | ทุก mechanism/threat ต้องมีบรรทัดใน `counter.md` รองรับ |
| **ห้ามเปิดน้ำหนัก** | component ใหม่ทั้งหมดเริ่มที่ `0.0` · อันดับต้องไม่ขยับ |
| **ban ≠ pick** | ทุก evidence ต้องประกาศ `objective_scope` · ตีความคนละทาง |

---

## 2. Data Contract

### 2.1 `CounterEvidence`

```python
class CounterEvidence(BaseModel):
    evidence_id: str                    # CTR-001 · ใช้อ้างกลับไปที่ counter.md
    target: str                         # hero id ที่เป็นภัย
    counter: str                        # hero id ที่แก้ภัยนั้น
    counter_type: CounterType           # ชนะทางด้วยวิธีไหน
    threat: ThreatTag | None            # target ทำอะไรถึงเป็นปัญหา
    mechanism: MechanismTag             # counter ใช้กลไกอะไร
    mechanism_detail: str               # ประโยคจาก source ไม่ใช่คำสรุปของเรา
    condition: list[Condition]          # ต้องเกิดอะไรก่อนถึงใช้ได้
    risk: str                           # ใช้แล้วเสียอะไร
    confidence: Confidence
    source: Source
    objective_scope: ObjectiveScope      # pick | ban | both
    status: EvidenceStatus              # verified | inferred | unknown
    data_check: DataCheck | None        # ข้อมูล 861 เกมของเราว่าอย่างไร
```

### 2.2 field ที่เพิ่มจากที่คำสั่งระบุ — และเหตุผล

คำสั่งบอก "ห้ามสร้าง field ที่ไม่มี semantic ชัดเจน" เพิ่มมา 4 field เท่านั้น

| field | ทำไมต้องมี |
|---|---|
| `evidence_id` | ต้องอ้างกลับไปยัง `CTR-00x` ใน counter.md ได้ ไม่งั้นตรวจย้อนไม่ได้ |
| `threat` | **STEP 3 บังคับ** — mechanism matching ต้องมีขา "Enemy Threat" |
| `mechanism_detail` | `mechanism` เป็น enum ที่หยาบ · detail คือประโยคจริงจาก source ที่เอาไปแสดงได้ |
| `data_check` | **audit §3 บังคับ** — ข้อมูลเราค้าน 8/15 ข้อ ถ้าไม่เก็บไว้จะกลายเป็นการปิดบัง |

### 2.3 `status` — ผูกกับหลักฐาน ไม่ได้ตั้งเอง

```
verified   ความรู้ยืนยัน + ข้อมูล 861 เกมของเราเห็นด้วย
inferred   ความรู้ยืนยัน แต่ข้อมูลเรายังไม่พอ หรือค้านอยู่
           → ยังใช้ได้ แต่ต้องแสดง data_check ควบเสมอ
unknown    ไม่มีความรู้เรื่องคู่นี้เลย  ← สถานะเริ่มต้นของฮีโร่ 114/119 ตัว
```

> `unknown` ไม่ใช่ค่าที่เขียนลงไฟล์ — มันคือ**สิ่งที่ได้เมื่อค้นแล้วไม่เจอ**
> ระบบต้องคืน `None` ไม่ใช่ `CounterEvidence(status=unknown, ...)` ที่มี field ว่าง

### 2.4 validator ที่บังคับ (ลอกรูปแบบจาก `MacroRule`)

| กฎ | เหตุผล |
|---|---|
| `source.type == "assumption"` → ห้าม `confidence HIGH` | กฎเดิมของโปรเจกต์ |
| `data_check.verdict == "disagrees"` → ห้าม `confidence HIGH` | **audit §3** |
| `status == "verified"` → ต้องมี `data_check.verdict == "agrees"` | ห้ามประกาศ verified ลอย ๆ |
| `target` และ `counter` ต้องมีใน `heroes.yaml` | กัน typo กลายเป็นความรู้ผี |
| `target != counter` | ฮีโร่ counter ตัวเองไม่ได้ |

---

## 3. Vocabulary — มาจาก counter.md §6 ทั้งหมด

ไม่มีป้ายไหนที่ผมคิดขึ้นเอง ทุกป้ายมีบรรทัดรองรับ

### ThreatTag — ศัตรูตัวนี้ทำอะไรถึงเป็นปัญหา

| tag | ความหมาย | ตัวอย่างจาก source |
|---|---|---|
| `recall_warp` | ดึงทีมกลับบ้าน/เติมไฟต์ด้วยวงวาร์ป | rouie |
| `heavy_cc` | สเปม CC ล็อกจนจ่ายดาเมจไม่ได้ | ybneth |
| `tank_frontline` | ค้ำไฟต์จนยิงไม่เข้า | ybneth · skud · toro |
| `immobile_backline` | แผงหลังขาตาย เสี่ยงโดนล้วง | iggy · yue · violet · capheny |
| `poke_siege` | ตอดเลือดระยะไกล บีบไม่ให้เข้าใกล้ | iggy · yue · violet |

### MechanismTag — counter ใช้อะไรแก้

| tag | ความหมาย | ตัวอย่างจาก source |
|---|---|---|
| `burst` | ฆ่าเป้าหมายเดี่ยวในชุดเดียว | billow · aoi · zata |
| `displacement` | ผลัก/ปัดออกจากพื้นที่ | omen · skud · qi · tachi |
| `cleanse` | ล้างสถานะ CC ทั้งทีม | chaugnar |
| `tank_melt` | True damage / %HP ละลายแผงหน้า | hayate · florentino |
| `dive` | พุ่งข้ามแผงหน้าถึงแผงหลัง | liliana · krizzix · elandorr · billow |
| `lane_trade` | ได้เปรียบการเทรดในเลน 1v1 | mina · murad · ryoma |
| `peel` | ปกป้องแผงหลังจากตัวล้วง | y'bneth · toro |

### CounterType — ป้ายชนิดการชนะทาง (counter.md §6 ตรง ๆ)

`hard` · `displacement` · `cleanse` · `burst` · `poke` · `lane` · `flex`

---

## 4. Mechanism Matching (STEP 3)

**ห้ามตรวจแค่ `A counters B`** ต้องเดินสามขา

```
Enemy Threat  →  Counter Mechanism  →  Candidate Capability
```

### 4.1 สองเส้นทางที่ให้ evidence

**เส้นที่ 1 · Direct** — มี record ที่ `target == enemy` และ `counter == candidate`
ใช้ `confidence` ตาม record

**เส้นที่ 2 · Mechanism match** — ไม่มี record ตรงคู่ แต่

```
enemy มี threat T
  ∧ มี record บอกว่า mechanism M ตอบ T ได้
  ∧ candidate มี capability M
→ evidence แบบ inferred
```

**confidence ของเส้นที่ 2 ต้องลดลงหนึ่งขั้นเสมอ** (HIGH → MEDIUM → LOW)
เพราะเป็นการอนุมานข้ามคู่ ไม่ใช่คำกล่าวตรง ๆ ของ source

### 4.2 ตัวอย่างที่ spec ต้องรองรับ (จากคำสั่ง)

```
Enemy       rouie
Threat      recall_warp
Mechanism   displacement | burst
Candidate   omen · tachi · skud · qi  (displacement)
            billow · aoi · zata       (burst)
Condition   "ต้องกดเลือกหลังจากศัตรูเปิด Rouie แล้ว"
Risk        "ถ้าศัตรูแผงหน้าหนา อาจเข้าไม่ถึง Rouie ช่วงเลทเกม"
```

### 4.3 ข้อมูลไม่พอ → UNKNOWN

- ไม่รู้ threat ของศัตรู → ไม่สร้าง evidence
- ไม่รู้ capability ของ candidate → ไม่สร้าง evidence
- **ห้ามเดาจาก `hero_class`** เช่น "เป็น assassin เลยน่าจะ burst ได้"
  audit §5.3 พิสูจน์แล้วว่า Liquipedia tag หยาบเกินและครอบคลุมแค่ 30/119

---

## 5. Context (STEP 4)

evidence จะถูกนับก็ต่อเมื่อบริบทครบ

| บริบท | ใช้ทำอะไร |
|---|---|
| enemy heroes | หา target / threat |
| our picks | ตรวจว่า risk ชนกับคอมพ์เราไหม · ใช้กับ ban interpretation |
| draft phase | เฟส 1 ไม่มีใครเปิด → evidence ส่วนใหญ่ยังไม่เข้าเงื่อนไข |
| candidate role | กรอง lane_trade ที่ต้องประกบเลนเดียวกัน |
| lane (ถ้ารู้) | `lane` counter_type ต้องอยู่เลนเดียวกันจริง |
| objective scope | pick หรือ ban |

### 5.1 กติกา condition

```
condition ที่มี fact/op/value  →  ประเมินอัตโนมัติ
condition ที่มีแต่ cue          →  ยังประเมินไม่ได้ · แสดงให้คนอ่านตัดสิน
                                   และนับเป็น "condition ยังไม่ยืนยัน"
```

**`unconditional: true` เท่านั้น**ที่ข้ามการตรวจได้ ต้องระบุชัดในไฟล์

ตอนนี้ condition ของ counter.md เกือบทั้งหมดเป็น `cue` ภาษาคน
เช่น "ก่อน Marja ได้ดาบ Z" ซึ่งระบบยังไม่รู้เรื่องไอเทม
→ **ต้องบอกผู้ใช้ว่ายังไม่ได้ตรวจให้** ไม่ใช่แกล้งทำเป็นตรวจแล้ว

---

## 6. Pick vs Ban (STEP 7)

**ห้ามใช้การตีความเดียวกันกลับหัว**

| | ประโยค | ใช้ evidence อย่างไร |
|---|---|---|
| **Pick** | "ตัวนี้ช่วยเราแก้ threat ที่ศัตรูมีอยู่" | candidate = `counter` · enemy = `target` |
| **Ban** | "ถ้าปล่อยตัวนี้ให้ศัตรู เขาจะใช้กลไกนี้กดเรา" | candidate = `counter` · **เรา** ถือ `target` |

### 6.1 ทำไมถึงไม่ใช่เรื่องเดียวกัน

Pick ถามว่า *เรามีปัญหา แล้วตัวนี้แก้ได้ไหม* — ต้องรู้ว่าศัตรูเปิดอะไรมาแล้ว

Ban ถามว่า *ถ้าเขาได้ตัวนี้ เขาจะแก้ทางเราได้ไหม* — ต้องรู้ว่า**เรา**เปิดอะไรไปแล้ว
และที่ตาแบนเฟส 1 ยังไม่มีใครเปิดอะไรเลย **evidence ฝั่ง ban จึงว่างเปล่าเกือบทั้งหมด**
ซึ่งเป็นผลลัพธ์ที่ถูกต้อง ไม่ใช่บั๊ก

### 6.2 `objective_scope` ต่อ record

| scope | ใช้เมื่อ |
|---|---|
| `pick` | evidence ที่พูดถึงการ "เอามาแก้" เท่านั้น เช่น Problem-Based |
| `ban` | evidence ที่ target เป็นตัวเรา และ counter เป็นตัวศัตรูจะหยิบ |
| `both` | Direct Hero Counter ส่วนใหญ่ — ใช้ได้ทั้งสองทางแต่**คนละประโยค** |

---

## 7. Score Separation (STEP 6)

### 7.1 component ใหม่ — ทุกตัวน้ำหนัก 0.0

```python
EXTRA_WEIGHTS = {
    "composition":     0.0,   # PHASE B
    "lane_counter":    0.0,   # PHASE B
    "synergy_adj":     0.0,   # PHASE B
    "trait_counter":   0.0,   # PHASE B
    "counter_evidence": 0.0,  # M1 ← ใหม่
}
```

`counter_evidence` แยกเป็น sub-signal ที่อธิบายได้ ไม่ยุบเป็นเลขเดียวตั้งแต่ต้น

| sub-signal | ความหมาย |
|---|---|
| `direct` | มี record ตรงคู่กี่ข้อ |
| `mechanism` | match ผ่านกลไกกี่ข้อ |
| `condition_met` | เงื่อนไขที่ประเมินได้แล้วผ่านกี่ข้อ |
| `confidence` | ค่าสูงสุดของ evidence ที่เข้าเงื่อนไข |

### 7.2 ข้อรับประกัน

1. `counter_evidence` weight = 0 → **อันดับ recommendation ต้องไม่ขยับแม้แต่ตาเดียว**
   วัดด้วย regression fixture เดิม 216 ตา
2. **ไม่แตะ** `counter` · `lane_counter` · `weights_for` · `ban_weights_for`
3. ถ้าจะเปิดน้ำหนัก — **ไม่ใช่ใน M1** และต้องมีหน้าต่าง evaluation ใหม่
   ([rov-eval-windows-consumed](27-counter-knowledge-audit.md): validation กับ holdout ถูกดูไปแล้วทั้งคู่)

### 7.3 ของเดิม map เข้า structure ใหม่ได้ไหม

| ของเดิม | map เป็น |
|---|---|
| `counter` (context=TEAM) | `DataCheck` ของ evidence — **ไม่ใช่** evidence เอง |
| `lane_counter` (context=LANE) | `DataCheck` ของ evidence ที่ `counter_type == "lane"` |
| `trait_counter` | ยังว่าง · M1 จะเติม `strong_against_traits` จาก mechanism ที่มี source |

> ตัวเลขเดิมกลายเป็น **หลักฐานฝ่ายข้อมูล** ที่ยืนคู่กับความรู้ ไม่ใช่คู่แข่งกัน
> ตรงกับรูปแบบที่ macro rule ใช้อยู่แล้ว

---

## 8. Explanation (STEP 5)

ทุก suggestion ที่มี evidence ต้องสร้างข้อความนี้ได้

```
Counter:     Chaugnar
Against:     Y'bneth
Why:         อัลติล้างสถานะ CC ทั้งทีม ทำให้คอมพ์เปิด CC เสียจังหวะไฟต์
Condition:   เลือกในตำแหน่ง Support เมื่อฝั่งตรงข้าม pick Y'bneth   [ยังไม่ได้ตรวจให้]
Risk:        ขาด hard CC เปิดไฟต์เอง ต้องพึ่งดาเมจหลักจากเพื่อน
Evidence:    มาเจาะพี่หมูกับปราสาทสายฟ้า — BAC vs BRU RPL winter 2026
Confidence:  HIGH
Our data:    ข้อมูลเราเห็นด้วย (14 เกม · +2.89)
```

**บรรทัด `Our data:` บังคับ** — ถ้าข้อมูลเราค้าน ต้องขึ้นว่าค้าน

---

## 9. Success Criteria

| # | เกณฑ์ | วัดอย่างไร |
|---|---|---|
| 1 | weight = 0 แล้วอันดับไม่ขยับ | regression fixture 216 ตา · identical |
| 2 | ทุก evidence มี source | validator + test |
| 3 | ข้อที่ข้อมูลค้าน ห้าม HIGH | validator + test |
| 4 | UNKNOWN คืน None ไม่ใช่ค่า 0 | test |
| 5 | condition ยังไม่ผ่าน → ไม่นับ | test |
| 6 | pick กับ ban ได้ประโยคคนละแบบ | test |
| 7 | รายงาน coverage ตรงไปตรงมา | docs/29 |
| 8 | pytest + ruff ผ่าน | CI |

---

## 10. สิ่งที่ M1 จะ **ไม่** ทำ

- ไม่เปิดน้ำหนักใด ๆ
- ไม่แตะ `weights_for` / `ban_weights_for` / `counter` / `lane_counter`
- ไม่สร้าง Ban Engine ใหม่ — ใช้ `objective` ที่ M0.75 ทำไว้
- ไม่เติม counter record ที่ไม่มีบรรทัดใน counter.md รองรับ
- ไม่ derive mechanism จาก Liquipedia tag (audit §5.3)
- ไม่ใช้ holdout เดิมตัดสินอะไร
