# 20 — Draft Intelligence Spec

ออกแบบเมื่อ 2026-09-11 · **ยังไม่ได้ลงมือเขียนโค้ด**

เอกสารนี้เป็น conceptual model ตาม STEP 2 และเป็นสัญญาว่าอะไรจะถูกสร้าง
ก่อนจะสร้างจริง · อ่าน [docs/17-intelligence-audit.md](17-intelligence-audit.md) ก่อน

---

## 1. หลักการที่ต้องไม่ละเมิด

รับมาจากโปรเจคเดิม ห้ามลดมาตรฐาน

1. ระบบไม่เดาค่าเชิงคุณภาพ — `UNKNOWN` เป็นสถานะที่ถูกต้อง
2. ทุก rule ต้องมี `source`
3. `assumption` ห้าม confidence HIGH
4. win rate ทุกตัวผ่าน shrinkage
5. ทุกคะแนนต้องอธิบายได้ว่ามาจากอะไร
6. เมื่อเอกสารขัดกัน `docs/09-build-log.md` มีน้ำหนักสูงสุด

เพิ่มใหม่จาก kit

7. **แยก 5 ระดับความจริง** — `FACT` / `OBSERVATION` / `INFERENCE` / `OPINION` / `UNKNOWN`
   ห้ามเลื่อน `INFERENCE` ขึ้นเป็น `FACT` โดยไม่มีหลักฐานใหม่
8. **ห้ามรวมข้ออ้างที่ขัดกันเงียบ ๆ** — เก็บทั้งสองด้านเหมือนที่ `data_check` ทำ
9. **ตัวเลขน้ำหนักทุกตัวต้องเป็น config** ไม่ฝังใน business logic

---

## 2. Conceptual Model

```
                          ┌──────────────────┐
                          │   Draft State    │  มีแล้ว: state.py
                          └────────┬─────────┘
                                   ▼
                          ┌──────────────────┐
                          │ Context Extract  │  ใหม่: ใครเปิดอะไร เลนไหนว่าง
                          └────────┬─────────┘  เฟสไหน ใครได้ last pick
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
          ┌──────────────────┐          ┌──────────────────┐
          │ Team Composition │          │  Enemy Threat    │  ใหม่
          │    Analysis      │          │    Analysis      │
          │ มีแล้ว: 10 มิติ   │          │ threat tags      │
          │ ต้องเพิ่ม 6 มิติ  │          │ + problems       │
          └────────┬─────────┘          └────────┬─────────┘
                   └──────────────┬──────────────┘
                                  ▼
                       ┌──────────────────────┐
                       │ Candidate Generation │  มีแล้ว: legal_moves
                       └──────────┬───────────┘
                                  ▼
                       ┌──────────────────────┐
                       │ Candidate Evaluation │  ขยาย: 4 → 11 factor
                       └──────────┬───────────┘
                                  ▼
                       ┌──────────────────────┐
                       │ Enemy Response Sim   │  ใหม่: 1 ply
                       └──────────┬───────────┘
                                  ▼
                       ┌──────────────────────┐
                       │ Final Composition    │  ใหม่
                       └──────────┬───────────┘
                                  ▼
                       ┌──────────────────────┐
                       │   Win Condition      │  ใหม่
                       └──────────┬───────────┘
                                  ▼
                       ┌──────────────────────┐
                       │ Macro Requirements   │  มี 42 rule รอเชื่อม
                       └──────────┬───────────┘
                                  ▼
                       ┌──────────────────────┐
                       │ Recommendation +     │  ใหม่
                       │    Explanation       │
                       └──────────────────────┘
```

---

## 3. การแยกห้าชั้นที่ห้ามปนกัน

STEP 2 กำหนดให้แยก A–E ตารางนี้คือนิยามที่จะใช้ในโค้ด

| ชั้น | นิยาม | ตัวอย่าง | เก็บที่ไหน | เปลี่ยนเมื่อไร |
|---|---|---|---|---|
| **A · Evidence** | สิ่งที่สังเกตได้ ตรวจย้อนได้ ไม่มีการตีความ | "Rouie ถูกแบน 565 จาก 861 เกม" · "สกิล 1 มีป้าย Knock Back" | `data/hero_traits.json`, `data/cache/liquipedia/` | เมื่อดึงข้อมูลใหม่ |
| **B · Rule** | ข้อความ IF/THEN/BECAUSE ที่มีคนพูดไว้และอ้างที่มาได้ | "IF ศัตรู pick Rouie THEN pick Billow BECAUSE burst ฆ่าก่อนวงวาร์ปทำงาน" | `knowledge/` (YAML) | เมื่อมีแหล่งใหม่ |
| **C · Derived Metric** | ตัวเลขที่คำนวณจาก A ด้วยสูตรที่เขียนไว้ | `adjusted_win_rate` · `counter_score` · `frontline = 69.1` | คำนวณสด ไม่เก็บ | เมื่อสูตรหรือข้อมูลเปลี่ยน |
| **D · Recommendation** | อันดับที่ระบบเสนอ | "อันดับ 1: Mganga" | คำนวณสด | ทุกตา |
| **E · Explanation** | คำอธิบายที่ประกอบจาก A+B+C ให้คนอ่าน | "เติม peel ที่ทีมขาด · ตัดภัยจาก dive · เสี่ยงแพ้ poke" | คำนวณสด | ทุกตา |

**กฎการไหล:** `A → C → D → E` และ `B → D → E`
**ห้าม** `E` ย้อนกลับไปแก้ `C` · **ห้าม** `D` เขียนทับ `A`

---

## 4. Provenance Model ที่ขยายแล้ว

ปัจจุบัน `Hero.filled_kind` มี 3 ค่า ซึ่งตอบ "ใครให้ค่า" แต่ไม่ตอบ "ค่านี้จริงแค่ไหน"

**เสนอให้แยกเป็นสองแกนอิสระ**

```python
class Provenance(BaseModel):
    # แกนที่ 1 — ใครเป็นคนให้ค่า (มีอยู่แล้ว ขยาย 1 ค่า)
    filled_kind: Literal["human", "coach_source", "assistant", "derived"]

    # แกนที่ 2 — ค่านี้เป็นความจริงระดับไหน (ใหม่ จาก kit)
    epistemic: Literal["FACT", "OBSERVATION", "INFERENCE", "OPINION", "UNKNOWN"]

    sources: list[str] = []        # ชื่อคลิป/หน้าเว็บ/rule_id ที่อ้างได้
    confidence: Confidence         # HIGH / MEDIUM / LOW (มีอยู่แล้วใน enums)
    note: str | None = None
```

`coach_source` เป็นค่าใหม่สำหรับข้อมูลที่มาจาก `external_knowledge/` —
**ไม่ใช่ `human`** เพราะไม่มีคนนั่งตรวจค่าของเราโดยตรง แต่**ดีกว่า `assistant`**
เพราะมีคลิปโค้ชอ้างอิงได้

### ตารางความน่าเชื่อถือ (เรียงจากมากไปน้อย)

| filled_kind | epistemic ที่อนุญาต | ตัวอย่าง |
|---|---|---|
| `derived` | `FACT`, `OBSERVATION` | pick/ban count จาก Liquipedia · ป้ายสกิลจากหน้าฮีโร่ |
| `human` | ทุกค่า | โค้ชกรอก engage = 85 |
| `coach_source` | `FACT`, `OBSERVATION`, `INFERENCE`, `OPINION` | CTR-001 จาก Draft 101 |
| `assistant` | `INFERENCE`, `OPINION`, `UNKNOWN` — **ห้าม `FACT`** | ค่า 30 ตัวที่กรอกไว้ตอนนี้ |

**validator ที่ต้องเขียน:** `assistant` + `FACT` → ValueError
เหตุผลเดียวกับที่ `assumption` + `HIGH` ถูกห้ามอยู่แล้ว

---

## 5. Composition Engine — 6 มิติที่จะเพิ่ม

**ไม่แทนที่ 10 มิติเดิม** เพิ่มแบบ modular และเริ่มที่น้ำหนัก 0 ใน recommendation

| มิติใหม่ | คำนวณจาก | สถานะข้อมูล | ถ้าไม่มีข้อมูล |
|---|---|---|---|
| `flexibility` | `lane_usage` — entropy ของการกระจายเลน ถ่วงด้วยจำนวน pick | ✅ มีครบ 120 ตัว | `UNKNOWN` |
| `burst` vs `sustained` | `damage.profile` + `utility.poke` | ✅ มี 30 ตัว | `UNKNOWN` |
| `poke` | `utility.poke` (กรอกแล้วแต่ไม่มีใครอ่าน) | ✅ มี 30 ตัว | `UNKNOWN` |
| `backline_access` | `utility.mobility` + `range` + `utility.engage` | ✅ มี 30 ตัว | `UNKNOWN` |
| `backline_protection` | `utility.peel` + `utility.disengage` + `frontline` ของทีม | ✅ มี 30 ตัว | `UNKNOWN` |
| `lane_safety` | `lane_matchups` 680 คู่ (คำนวณแล้วไม่ได้ใช้) | ✅ มีแล้ว | `UNKNOWN` |
| `macro_dependency` | `required_conditions` จาก kit | ⚠️ มี 13 ตัวใน kit | `UNKNOWN` |
| `team_fight_pattern` | จำแนกเป็น 4 แบบตาม kit | ⚠️ ต้องเขียนกฎจำแนก | `UNKNOWN` |

**หลักสำคัญ:** `CompositionReport.dimensions[key].value` ต้องรองรับ `None`
และ report ต้องพิมพ์ `UNKNOWN` ไม่ใช่ `0.0` — ตอนนี้ `Dimension.value` เป็น
`float` บังคับ ซึ่งทำให้แยกไม่ออกระหว่าง "ศูนย์จริง" กับ "ไม่รู้"

### `CompositionProfile` — สัญญาที่ macro engine จะเรียกใช้

ตาม `specs/MACRO_ENGINE_SPEC.md` ที่ขอ

```python
@dataclass
class CompositionProfile:
    """สรุปคอมพ์แบบกระชับ สำหรับให้ macro engine อ่าน"""
    early: float | None
    mid: float | None
    late: float | None
    engage: float | None
    disengage: float | None
    peel: float | None
    objective: float | None
    waveclear: float | None
    mobility: float | None
    win_condition: WinCondition | None
    pattern: TeamFightPattern | None
    unknown_fields: list[str]        # ★ บอกตรง ๆ ว่าอะไรยังไม่รู้
```

---

## 6. Recommendation — 11 factor

ขยายจาก 4 → 11 · **ทุกตัวใหม่เริ่มที่น้ำหนัก 0** แล้วเปิดทีละตัวพร้อมวัดผล

| factor | มีแล้ว? | ที่มา | ชั้น |
|---|---|---|---|
| `meta` | ✅ | `presence_rate` | C |
| `winrate` | ✅ | `adjusted_win_rate` | C |
| `counter_value` | ✅ | `counter_score` — จะเสริมด้วย rule | C+B |
| `synergy_value` | ✅ | `counter_score` — จะเปลี่ยนไปใช้ `expected_synergy()` | C+B |
| `role_fit` | ✅ (เป็นตัวคูณ) | `lane_usage` | C |
| **`composition_fit`** | ❌ | ต่างของ composition ก่อน/หลัง pick | C |
| **`enemy_threat_fit`** | ❌ | threat tag ของศัตรู × ความสามารถของ candidate | B |
| **`flex_value`** | ❌ | entropy ของ `lane_usage` | C |
| **`power_curve_fit`** | ❌ | tempo ของทีมเทียบศัตรู | C |
| **`objective_fit`** | ❌ | `utility.objective` เทียบกับช่วงเกม | C |
| **`macro_fit`** | ❌ | rule ใน `knowledge/macro/` ที่ตรงกับคอมพ์ | B |
| **`risk`** | ❌ | ผลลบ — `creates_gaps` + counter ที่ศัตรูยังเปิดได้ | C+B |
| **`data_confidence`** | ❌ | ไม่ใช่ factor ที่บวก แต่เป็นตัวคูณ/ป้าย | C |

### Output contract

**ตรงกับที่ [docs/06-draft-engine.md §7](06-draft-engine.md) ออกแบบไว้ตั้งแต่แรก**
เพิ่มเฉพาะ `expected_enemy_response` และ `sources` ตาม kit

```python
@dataclass
class Suggestion:
    hero_id: str
    rank: int
    total: float
    components: dict[str, Component]     # มีแล้ว — เพิ่ม confidence ต่อ component
    role_fit: float                      # มีแล้ว
    games: int                           # มีแล้ว

    # ── ใหม่ทั้งหมด ────────────────────────────────
    fills_gaps: list[Gap]                # แก้ปัญหาอะไร        → PRIMARY GOAL ข้อ 2, 3
    creates_gaps: list[Gap]              # สร้างจุดอ่อนอะไร     → ข้อ 4
    expected_enemy_response: list[EnemyResponse]   # ข้อ 5
    our_counter_response: list[str]      # ข้อ 6
    remaining_risks: list[Risk]
    reasons: list[Reason]                # เปลี่ยนจาก list[str] เป็น structured
    sources: list[str]                   # rule_id / ชื่อคลิป  → ข้อ 9
    confidence: Confidence               # ข้อ 10
    data_basis: DataBasis                # จาก docs/06 §7
```

```python
@dataclass
class Reason:
    type: Literal["role_gap", "damage_mix", "trait_counter", "empirical_counter",
                  "synergy", "meta", "macro", "flex", "risk"]
    detail: str
    source: str | None       # rule_id ถ้ามาจาก B · ชื่อ metric ถ้ามาจาก C
    epistemic: str           # FACT / OBSERVATION / INFERENCE / ...
```

**กฎ:** `Reason.source` เป็น `None` ได้เฉพาะเมื่อ `type` มาจาก derived metric
ถ้าอ้าง rule แล้วไม่มี `source` → ValueError

---

## 7. Counter Engine — 5 ชั้น

```
CounterEngine.analyze(enemy_picks, our_picks, candidate)
  │
  ├─ ชั้น 1 · Hero Counter
  │    empirical: pooled.matchups / lane_matchups          [C]
  │    rule:      CTR-001..005 จาก knowledge/counter.md     [B]
  │    → ถ้าทั้งสองตรงกัน confidence สูงขึ้น
  │    → ถ้าขัดกัน แสดงทั้งคู่ ห้ามเลือกข้างเงียบ ๆ
  │
  ├─ ชั้น 2 · Role Counter
  │    enemy role tags → required response
  │    3 กลุ่มจาก kit: Assassin / Tank-CC / Poke-Siege
  │
  ├─ ชั้น 3 · Composition Counter
  │    enemy composition → threat tags → team problem → response
  │
  ├─ ชั้น 4 · Problem-Based Counter
  │    "ทีมเรามีปัญหาอะไร" → "คุณสมบัติอะไรแก้ได้" → "ใครมีคุณสมบัตินั้น"
  │    4 คำถามจาก kit + ที่ derive จาก composition gaps
  │
  └─ ชั้น 5 · Win-Condition Counter
       enemy win condition → วิธีขัด
```

### Schema ของ rule (YAML — ต่อยอดจาก `MacroRule` ที่มีอยู่)

```yaml
rule_id: CTR-001
kind: hero_counter
target: [rouie]
counter: [billow, omen, tachi, skud, qi, aoi, zata]
counter_type: [hard_counter, displacement_counter, burst_counter]
reason: "Rouie เด่นเรื่องวงวาร์ป แต่ตัวบางต้นเกมและแพ้ตัวโถม/กระแทกออกจากวง"
mechanism:
  - "Burst: ฆ่าเป้าหมายก่อนวงวาร์ปทำงานสำเร็จ"
  - "Displacement: ผลักศัตรูออกจากพื้นที่วงวาร์ป"
condition: "ต้องเลือกหลังศัตรูเปิด Rouie หรือดักทางในเฟสสุดท้าย"
risk: "ถ้าศัตรูมีแผงหน้าหนา อาจเข้าไม่ถึง Rouie ในเลทเกม"
epistemic: FACT
confidence: HIGH
source:
  type: coach_input
  ref: "Rov เบสิคมาโครรูอี้ ฉบับเข้าใจง่ายๆ · Draft 101"
  detail: "external_knowledge/rov-claude-kit/knowledge/counter.md CTR-001"
data_check:              # ★ ต้องคำนวณจากข้อมูลเราเอง ห้ามคัดลอกมา
  verdict: null          # เติมโดยสคริปต์ ไม่ใช่คนเขียน
```

**`data_check` ต้องให้เครื่องคำนวณ** จาก `pooled.matchups` แล้วเติมเอง
เพื่อให้เห็นทันทีว่าคลิปกับข้อมูล 861 เกมเห็นตรงกันหรือไม่ —
นี่คือกลไกเดียวกับที่ `knowledge/macro/` ใช้อยู่แล้วและได้ผลดี

---

## 8. Synergy Engine — 7 ชนิด

Schema เดียวกับ counter แต่เพิ่มช่องจาก `specs/SYNERGY_ENGINE_SPEC.md`

```yaml
rule_id: SYN-001
kind: hero_pair
heroes: [rouie, capheny]
synergy_type: global_warp_synergy
gameplay_interaction: "Rouie วางวงวาร์ปให้ Capheny รีเซตเลือดกลับมาไฟต์ต่อ"
condition: "ต้องมีเลนข้างที่ประคองตัวเองได้เพราะ Rouie ต้นเกมอ่อน"   # ★ สำคัญ
expected_result: "ยืดไฟต์และดันสองทางพร้อมกัน"
weakness: "ถ้าโดน burst/displacement ระหว่างวาร์ป แผนพัง"
epistemic: FACT
confidence: HIGH
source: {...}
data_check: {verdict: null}
```

**`condition` และ `weakness` คือสิ่งที่ระบบเดิมเก็บไม่ได้เลย** —
เดิมมีแค่ "คู่นี้ชนะ X% จาก n เกม"

**การรวมคะแนน:** empirical (`expected_synergy()`) + rule bonus
โดย rule bonus เป็น config เริ่มต้นจาก kit แต่**ต้อง fit ก่อนเปิดใช้**

---

## 9. Lookahead — 1 ply เท่านั้น

```
our_candidate
  → predict_enemy_response(candidate, enemy_state)
      • ศัตรูยังขาดเลนไหน            (deterministic)
      • rule ไหนที่ trigger จาก candidate นี้   (B)
      • empirical: ตัวไหนที่ทีมอาชีพมักหยิบตอบ   (C — จาก 861 เกม)
  → our_best_response(projected_state)
  → projected_final_composition
```

**ข้อจำกัดที่ต้องประกาศทุกครั้ง**

1. **1 ply เท่านั้น** — ไม่ทำ minimax ลึก เพราะ branching factor ~119 และ
   ไม่มีทางประเมินความน่าจะเป็นของศัตรูได้แม่นพอ
2. **คืน "ตัวเลือกที่เป็นไปได้ + confidence" ไม่ใช่ "ศัตรูจะทำแบบนี้"**
3. **ไม่ใช้ ML** — `specs/` และ IMPORTANT RULE ข้อ 9 ห้ามไว้ตรงกัน
4. ถ้าข้อมูลไม่พอ คืน `UNKNOWN` แทนการเดา

---

## 10. Win Condition

จำแนกคอมพ์เป็น 4 แบบตาม `knowledge/synergy.md §3`

| pattern | ลายเซ็น | macro ที่ต้องใช้ |
|---|---|---|
| `FRONT_TO_BACK` | frontline สูง + engage สูง + carry scaling | ตั้งไฟต์หน้าตรง คุม objective |
| `DIVE` | mobility สูง + backline_access สูง + burst | หาจังหวะล้วง เลี่ยงไฟต์ยาว |
| `POKE_SIEGE` | poke สูง + waveclear สูง + frontline ต่ำ | ตอดแล้วดันป้อม ห้ามโดนเปิด |
| `SPLIT_PUSH` | splitpush สูง + global mobility | 1-3-1 บีบสองทาง |

**ต้องคืน `UNKNOWN` ได้** เมื่อคอมพ์ไม่เข้าลายเซ็นไหนชัด หรือข้อมูลไม่ครบ
ห้ามบังคับให้เข้าแบบใดแบบหนึ่งเสมอ

จากนั้นผูกกับ `knowledge/macro/` ผ่าน `tags` ที่ `MacroRule` มีอยู่แล้ว

---

## 11. Benchmark Plan

**ห้ามอ้างว่า "ฉลาดขึ้น" โดยไม่มีตัวเลข** (STEP 14)

### การแบ่งข้อมูล

```
861 เกม · 305 ซีรีส์ · เรียงตามวันที่
├── train/analysis : 2025-08-23 ถึง 2026-05-08   (~70%)
└── evaluation     : 2026-05-09 ถึง 2026-09-06   (~30%)
```

**แบ่งตามเวลา ไม่ใช่สุ่ม** — เพราะเมตาเปลี่ยนตามเวลา การสุ่มจะทำให้
โมเดลเห็นอนาคตของเมตาเดียวกัน ซึ่งเป็น leakage ที่ตรวจไม่เจอ

**กฎเหล็ก:** `recommend()` ตอนประเมิน ห้ามเห็นข้อมูลหลัง cutoff แม้แต่เกมเดียว
รวมถึง `presence_rate` และ `matchups` ที่ต้องคำนวณจาก train เท่านั้น

### ตัววัด

| # | ตัววัด | นิยาม | ตอนนี้ | เป้า |
|---|---|---|---|---|
| B1 | **Top-5 hit rate** | ตัวที่ทีมอาชีพเลือกจริง ติด 5 อันดับแรกของระบบกี่ % | ยังไม่วัด | วัดก่อน แล้วห้ามถอย |
| B2 | **Recommendation stability** | เปลี่ยน min_games ±3 แล้วอันดับ 1 เปลี่ยนกี่ % | ยังไม่วัด | ต่ำลง = ดีขึ้น |
| B3 | **Counter accuracy** | เมื่อระบบบอก "ตัวนี้กดตัวนั้น" ผลจริงใน eval set เป็นยังไง | ยังไม่วัด | > baseline |
| B4 | **Role fit accuracy** | ตัวที่แนะนำลงเลนที่ระบบคิดไว้จริงกี่ % | ยังไม่วัด | > 80% |
| B5 | **Composition coherence** | คอมพ์ที่ชนะจริง ได้คะแนน composition สูงกว่าที่แพ้ไหม | ยังไม่วัด | ต่างอย่างมีนัย |
| B6 | **Explanation completeness** | คำแนะนำกี่ % ที่มีครบ fills_gaps + risk + source + confidence | 0% | 100% |
| B7 | **Unknown handling** | ระบบบอก UNKNOWN เมื่อข้อมูลไม่พอกี่ % (ควรสูง ไม่ใช่ต่ำ) | ยังไม่วัด | สูง = ซื่อสัตย์ |
| B8 | **Provenance completeness** | ค่าที่ใช้คิดคะแนนกี่ % ที่ trace กลับไปหา source ได้ | ยังไม่วัด | 100% |

**B1 เป็นตัวหลัก** แต่ต้องอ่านด้วยความระวัง — ทีมอาชีพอาจเลือกผิด และ
การเลียนแบบ 100% ไม่ใช่เป้าหมาย เป้าหมายคือ **ไม่ถอยหลัง** เวลาเพิ่ม factor

**B6, B7, B8 สำคัญไม่แพ้กัน** เพราะวัดความซื่อสัตย์ ไม่ใช่ความแม่น
และเป็นตัวที่ระบบนี้ควรได้คะแนนสูงที่สุด

---

## 12. Test Plan

เทสต์ใหม่ที่จะเพิ่ม (เทสต์เดิม 282 ตัวห้ามเสียแม้แต่ตัวเดียว)

| ไฟล์ | เทสต์ | จำนวนประมาณ |
|---|---|---|
| `test_counter_knowledge.py` | schema validation · rule จาก kit โหลดได้ · `data_check` คำนวณถูก · rule ที่ขัดกับข้อมูลต้องไม่ได้ HIGH | ~15 |
| `test_synergy_knowledge.py` | เช่นเดียวกัน + `condition`/`weakness` ต้องมี | ~12 |
| `test_composition_v2.py` | 6 มิติใหม่ · `UNKNOWN` เมื่อข้อมูลไม่ครบ · `CompositionProfile` · ไม่ทำให้ 10 มิติเดิมเปลี่ยนค่า | ~20 |
| `test_recommend_context.py` | factor ใหม่ที่น้ำหนัก 0 ต้องไม่เปลี่ยนอันดับ ★ · `fills_gaps`/`creates_gaps` · `confidence` | ~18 |
| `test_lookahead.py` | 1 ply · คืน UNKNOWN เมื่อข้อมูลไม่พอ · ไม่ crash เมื่อ pool หมด | ~10 |
| `test_explanation.py` | ทุก reason มี source หรือเป็น derived · ห้ามมีคะแนนที่อธิบายไม่ได้ | ~12 |
| `test_provenance_v2.py` | `assistant` + `FACT` ต้อง ValueError · epistemic label ครบ | ~10 |
| `test_benchmark.py` | train/eval ไม่ทับกัน · ไม่มี leakage · ตัววัดคำนวณได้ | ~8 |
| `test_web_board.py` (เพิ่ม) | parity ของ factor ใหม่ทุกตัว | ~10 |

★ **เทสต์ที่สำคัญที่สุด** — พิสูจน์ว่าการเพิ่ม factor ไม่เปลี่ยนพฤติกรรมเดิม
จนกว่าจะตั้งใจเปิดน้ำหนัก นี่คือเครื่องมือที่ทำให้เพิ่มของได้โดยไม่พังของเดิม

### Regression case จากดราฟต์จริง

สร้างจาก eval set — เลือกดราฟต์จริง 20 เกมแล้วเก็บผลปัจจุบันเป็น snapshot
ทุกครั้งที่แก้ engine ต้องบอกได้ว่าอันดับเปลี่ยนไปกี่ตำแหน่งและเพราะอะไร

---

## 13. ไฟล์ที่จะเปลี่ยน

| ไฟล์ | การเปลี่ยนแปลง | ความเสี่ยง |
|---|---|---|
| `rov/draft/heroes.py` | เพิ่ม `Provenance` · `epistemic` · `sources[]` | 🟡 แตะ model ที่ 119 ตัวใช้อยู่ — ต้องมี default ที่ backward compatible |
| `rov/draft/composition.py` | เพิ่ม 6 มิติ · `Dimension.value` รองรับ `None` · `CompositionProfile` | 🟡 แตะของที่ทำงานอยู่ — เทสต์เดิม 12 ตัวต้องผ่านหมด |
| `rov/draft/recommend.py` | เพิ่ม 7 factor (น้ำหนัก 0) · `Suggestion` ขยาย | 🟡 แกนของระบบ — ต้องมี snapshot test ก่อนแตะ |
| `rov/draft/counters.py` | **ไฟล์ใหม่** — CounterEngine 5 ชั้น | 🟢 ของใหม่ |
| `rov/draft/synergies.py` | **ไฟล์ใหม่** — SynergyEngine 7 ชนิด | 🟢 |
| `rov/draft/lookahead.py` | **ไฟล์ใหม่** — 1 ply | 🟢 |
| `rov/draft/explain.py` | **ไฟล์ใหม่** — Explanation Engine | 🟢 |
| `rov/draft/winconditions.py` | **ไฟล์ใหม่** + ย้าย `winCondition()` จาก JS | 🟢 |
| `rov/eval/benchmark.py` | **ไฟล์ใหม่** | 🟢 |
| `knowledge/counter/*.yaml` | **ใหม่** — 5 direct + 3 role + 2 comp + 4 problem | 🟢 |
| `knowledge/synergy/*.yaml` | **ใหม่** — 8 pair + 5 role + 7 tag | 🟢 |
| `configs/draft/weights.yaml` | **ใหม่** — น้ำหนักทุกตัวออกจากโค้ด | 🟡 ต้องให้ค่าเริ่มต้นตรงกับที่ hardcode อยู่เป๊ะ ๆ |
| `configs/draft/hero_assessment.yaml` | เพิ่ม 3 ตัวจาก kit + ตรวจ 10 ตัว | 🟢 |
| `apps/web/draft_board.tpl.html` | PHASE J เท่านั้น | 🟡 |

---

## 14. สิ่งที่ยังไม่ตัดสิน — ต้องถามหรือทดลองก่อน

1. **น้ำหนักของ factor ใหม่** — ยังไม่มีวิธีตัดสินจนกว่าจะมี benchmark (B1–B5)
   → ทุกตัวเริ่มที่ 0 แล้วเปิดทีละตัวพร้อมวัดผล
2. **`coach_source` ควรอยู่ตรงไหนในลำดับความน่าเชื่อถือ** — สูงกว่า `assistant` แน่นอน
   แต่เทียบกับ `derived` ยังไม่ชัด (คลิปโค้ชอธิบายกลไก ส่วนข้อมูลวัดผลลัพธ์
   สองอย่างนี้ตอบคนละคำถาม)
3. **Chaugnar และตัวที่คลิปให้ค่าสูงแต่ข้อมูลไม่ยืนยัน** — จะให้ระบบเสนอหรือไม่
   → เสนอแต่ติดป้าย `insufficient` ตามที่ [docs/18 §3](18-hero-data-coverage.md) สรุป
4. **ลำดับสลับ ban/pick และเวลาต่อตา** — ยังต้องดูคลิปแข่ง
5. **จะรองรับ `scope: both_teams` ของ Global Ban-Pick ไหม** — ตอนนี้ JS รองรับแค่
   `own_team_only` และมีเทสต์ล็อกไว้ ถ้ารายการอื่นใช้กติกาต่างต้องแก้ทั้งสองฝั่ง
