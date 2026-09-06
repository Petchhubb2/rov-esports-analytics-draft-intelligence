# 11 — Macro Planner และ Macro Knowledge Base

ครอบคลุมโมดูล 27–32 ของ Blueprint ซึ่งเป็นส่วนที่ใหญ่ที่สุดที่แผนเดิมไม่มีเลย

---

## 1. ความต่างที่ต้องเข้าใจก่อน

```
MACRO ANALYZER   ตอบว่า "เกิดอะไรขึ้น"      ← มาจากวิดีโอ
MACRO PLANNER    ตอบว่า "ควรทำอะไร"        ← มาจาก draft + กติกา
```

สองอย่างนี้ใช้ข้อมูลคนละชุดและมีความเสี่ยงคนละแบบ

| | Analyzer | Planner |
|---|---|---|
| ที่มาของข้อมูล | สังเกตจริงจากวิดีโอ | อนุมานจาก rule + สถิติ |
| ผิดแล้วเป็นอย่างไร | รายงานสิ่งที่ไม่เกิดขึ้น | แนะนำสิ่งที่ทำให้แพ้ |
| ตรวจสอบอย่างไร | เทียบ ground truth | เทียบผลจริงย้อนหลัง |

**ความเสี่ยงหลักของ Planner คือการแต่งความรู้ขึ้นเอง**
Blueprint §36 เขียนว่า "Never fabricate strategic knowledge"
ทุก rule จึงต้องมี `source` และห้ามมี rule ที่เขียนจากความรู้สึก

---

## 2. Macro Knowledge Base

### สคีมาของ rule

```yaml
# knowledge/macro/objective/dragon_setup_mid_priority.yaml
rule_id: OBJ_DRAGON_MID_PRIORITY
name: เซ็ตอัพ Dragon เมื่อมี Mid Priority
phase: EARLY            # OPENING | EARLY | MID | LATE
priority: 70            # 0-100 ใช้จัดลำดับเมื่อ rule ชนกัน

conditions:
  - { fact: seconds_to_dragon_spawn, op: lte, value: 45 }
  - { fact: mid_wave_pushed,          op: eq,  value: true }
  - { fact: our_jungler_alive,        op: eq,  value: true }
  - { fact: enemy_jungler_last_seen_side, op: ne, value: DRAGON }

action:
  shape: 3-2
  assignments:
    - { role: mid,     goto: RIVER_BOTTOM }
    - { role: jungle,  goto: DRAGON_PIT_APPROACH }
    - { role: support, goto: RIVER_BOTTOM }
    - { role: dragon,  goto: DRAGON_LANE, note: ฟาร์มต่อ }
    - { role: ds,      goto: DS_LANE, note: ถือเลนกดดัน }

patch: "1.63"
confidence: MEDIUM      # HIGH | MEDIUM | LOW
source:
  type: derived_from_data      # derived_from_data | coach_input | literature | assumption
  ref: "RPL 2026 Summer, 291 เกม"
  detail: "ทีมที่มี 3 คนใน DRAGON_PIT_APPROACH ก่อนเกิด 30 วินาที ได้ dragon 71%"
notes: |
  ยังไม่ได้แยกตามความแข็งของ composition
  ต้องทบทวนเมื่อมีข้อมูลเกิน 500 เกม
```

### ประเภทของ source และวิธีใช้

| type | ความหมาย | แสดงบน UI อย่างไร |
|------|----------|-------------------|
| `derived_from_data` | คำนวณจากแมตช์จริง มีตัวเลขกำกับ | แสดงตัวเลขและจำนวนเกม |
| `coach_input` | โค้ชหรือผู้เล่นระดับสูงให้มา | แสดงชื่อผู้ให้และวันที่ |
| `literature` | จากบทวิเคราะห์ที่อ้างอิงได้ | แสดงลิงก์ |
| `assumption` | สมมติฐานที่ยังไม่ได้ตรวจ | **ต้องติดป้ายเตือนชัดเจน** |

กฎ: rule ที่เป็น `assumption` ห้ามมี `confidence: HIGH`
และต้องมีคำสั่ง `rov macro audit` ที่ลิสต์ rule ประเภทนี้ออกมาทั้งหมด

### โครงไดเรกทอรี

```
knowledge/macro/
├── opening/       0:00-1:00 การแบ่งตัวเปิดเกม
├── wave/          การจัดการเวฟมินเนี่ยน
├── roaming/       การโรมของ support และ mid
├── jungle/        เส้นทางป่าและการแย่งป่า
├── objective/     dragon slayer sentinel
├── teamfight/     การเลือกจังหวะปะทะ
├── split_push/    การแยกกดดัน
└── lane_swap/     การสลับเลน
```

---

## 3. Rule Engine

### Fact ที่ rule ใช้อ้างอิงได้

ต้องกำหนดให้ครบและตายตัว มิฉะนั้นจะเขียน rule ที่ประเมินไม่ได้

**จาก draft (มีตั้งแต่ก่อนเกมเริ่ม)**

```
our_composition_tags      รายการ MacroTag ของทีมเรา
enemy_composition_tags
our_power_curve           {early, mid, late}
enemy_power_curve
role_matchup_delta        ความได้เปรียบเสียเปรียบต่อเลน
we_have_engage            bool
we_have_peel              bool
we_outscale               bool
```

**จากสถานะเกม (ต้องมี vision pipeline)**

```
game_clock
seconds_to_dragon_spawn
seconds_to_slayer_spawn
dragon_state              ALIVE | DEAD | UNKNOWN
our_jungler_alive
enemy_jungler_last_seen_side
enemy_jungler_last_seen_age    วินาทีนับจากครั้งสุดท้ายที่เห็น
mid_wave_pushed
our_players_in_zone(zone)
gold_diff
tower_diff
```

**สำคัญ:** fact ที่ขึ้นต้นด้วย `enemy_*_last_seen` ต้องมาพร้อมอายุเสมอ
เพราะ "ศัตรูอยู่ฝั่งบน" ที่ข้อมูลเก่า 40 วินาที ไม่ใช่ข้อเท็จจริงอีกต่อไป
Rule ที่ใช้ fact เหล่านี้ต้องระบุ `max_age` ของตัวเอง

### การประเมิน

```python
def evaluate(rules, facts, phase):
    matched = [r for r in rules
               if r.phase == phase and all(c.holds(facts) for c in r.conditions)]
    matched.sort(key=lambda r: r.priority, reverse=True)
    return matched
```

เมื่อ rule ชนกัน ใช้ `priority` ตัดสิน แต่ต้อง**บันทึกว่ามี rule อื่นที่แข่งอยู่**
เพื่อให้ผู้ใช้เห็นทางเลือกที่ระบบไม่ได้เลือก และเป็นที่มาของ Secondary Plan

---

## 4. Win Condition Engine

ตอบคำถาม "ทีมนี้ควรชนะด้วยอะไร" จาก composition ล้วน ไม่ต้องรอ vision

```python
def win_conditions(our_comp, enemy_comp) -> list[WinCondition]:
    """คืนรายการเรียงตามน้ำหนัก พร้อมเหตุผลเชิงตัวเลข"""
```

รูปแบบที่รองรับตอนแรก

| Win Condition | เงื่อนไขที่ทำให้ถูกเลือก |
|---------------|--------------------------|
| Early Objective Tempo | early power สูงกว่า และมี FAST_CLEAR + EARLY_GANK |
| Scaling / Late Teamfight | late power สูงกว่าชัดเจน และมี PEEL |
| Split Push | มี SPLIT_PUSH และ waveclear ดี แต่ teamfight สู้ไม่ได้ |
| Poke and Siege | มี POKE หลายตัว และ objective damage สูง |
| Pick-off | มี DIVE + hard CC และศัตรูมี mobility ต่ำ |

ทุกอันต้องคืน `evidence` เป็นตัวเลข ไม่ใช่แค่ชื่อ

---

## 5. Macro Plan

```json
{
  "plan_id": "...",
  "draft_id": "...",
  "generated_at": "...",
  "rule_versions": ["OBJ_DRAGON_MID_PRIORITY@3", "OPEN_INVADE_CHECK@1"],
  "win_conditions": [
    { "id": "EARLY_OBJECTIVE_TEMPO", "weight": 0.62,
      "evidence": { "early_power_delta": 11.4, "tags": ["FAST_CLEAR","EARLY_GANK"] } }
  ],
  "tiers": {
    "PRIMARY":   { "shape": "3-2", "steps": [...], "trigger": "ค่าเริ่มต้น" },
    "SECONDARY": { "shape": "4-1", "steps": [...], "trigger": "เสีย mid priority" },
    "EMERGENCY": { "shape": "1-3-1", "steps": [...], "trigger": "jungler ตายก่อน objective" }
  }
}
```

`rule_versions` ทำให้ตรวจย้อนกลับได้ว่าแผนนี้มาจาก rule เวอร์ชันใด
ตามกฎข้อ 11–12 ของ Blueprint §70

---

## 6. Actual vs Recommended

```
Macro Plan (ก่อนเกม)
        +
Observation + Event (จากวิดีโอ)
        ↓
   จับคู่ตามช่วงเวลา
        ↓
   PLAN DEVIATION
```

### วิธีจับคู่

สำหรับแต่ละ step ของแผนที่มีช่วงเวลากำกับ ให้ดูว่าผู้เล่นที่ระบุ
อยู่ใน zone ที่แผนบอกหรือไม่ ภายในหน้าต่างเวลาที่ยอมรับได้

```
match_rate = จำนวน step ที่ทำตาม / จำนวน step ทั้งหมดที่ประเมินได้
```

### กฎที่ต้องยึด

Blueprint §50 เขียนไว้ชัดว่า **deviation ไม่เท่ากับเล่นผิด**

ทุก deviation ต้องรายงานพร้อมสามอย่าง

1. **บริบท** — ตอนนั้นเกิดอะไรขึ้น (เช่น jungler ตายไปก่อน 8 วินาที)
2. **ผลลัพธ์** — ทำแล้วได้หรือเสีย objective/kill
3. **coverage** — ช่วงนั้นมีข้อมูล observed กี่เปอร์เซ็นต์

ถ้า coverage ต่ำกว่า 0.5 **ห้ามรายงาน deviation เลย**
เพราะไม่รู้จริง ๆ ว่าผู้เล่นอยู่ไหน

### สิ่งที่ระบบต้องพูดได้

```
Step: MID + JUNGLE + SUPPORT → DRAGON_PIT_APPROACH ที่ 3:15

ทำตาม: บางส่วน (2 จาก 3 คน)
  ✓ jungle เข้าพื้นที่ที่ 3:12
  ✓ support เข้าพื้นที่ที่ 3:19
  ✗ mid อยู่ DS_LANE ตลอดช่วง

บริบท: mid เพิ่งเคลียร์เวฟที่ 3:05 และเวฟถัดไปมาถึงที่ 3:21
ผลลัพธ์: เสีย dragon · เสีย 1 kill
coverage: 0.94
```

---

## 7. ลำดับการพัฒนา

ต้องทำตามลำดับนี้ เพราะแต่ละขั้นพึ่งขั้นก่อนหน้า

| ขั้น | งาน | ต้องมีอะไรก่อน |
|-----|-----|----------------|
| P1 | Hero macro characteristics (Blueprint §38) + MacroTag | ไม่ต้องมีอะไร |
| P2 | Win Condition Engine | P1 |
| P3 | สคีมา rule + loader + `rov macro audit` | ไม่ต้องมีอะไร |
| P4 | เขียน rule ชุดแรกจากข้อมูล draft ที่ดึงมาแล้ว | P3 + ข้อมูล draft |
| P5 | Rule Engine + Plan generator | P2, P4 |
| P6 | Primary/Secondary/Emergency + Decision Tree | P5 |
| P7 | Actual vs Recommended | P6 + **vision pipeline ครบถึง event** |

**P1–P6 ทำได้โดยไม่ต้องรอ vision เลย** เพราะใช้แค่ draft และ hero attribute
มีเพียง P7 ที่ต้องรอ ซึ่งตรงกับที่ Blueprint §68 วางไว้ว่า M7 (Draft → Macro Plan)
มาก่อน M8 (Actual vs Recommended)

---

## 8. สิ่งที่ต้องระวังที่สุด

| ความเสี่ยง | ทำไมอันตราย | ป้องกันอย่างไร |
|-----------|-------------|----------------|
| แต่ง rule จากความรู้สึก | ระบบจะดูฉลาดแต่แนะนำผิด และตรวจไม่ได้ว่าผิดตรงไหน | บังคับให้ทุก rule มี `source` และมีคำสั่ง audit |
| Rule ตายตัวเกินไป | Blueprint §42 เตือนเรื่องนี้โดยเฉพาะ เช่น "roam ต้องไปมิดเสมอ" | ทุก rule ต้องมี conditions อย่างน้อย 2 ข้อ ที่ไม่ใช่แค่เวลา |
| ใช้ fact ที่ข้อมูลเก่า | "ศัตรูอยู่ฝั่งบน" เมื่อ 40 วินาทีที่แล้ว ไม่ใช่ความจริงตอนนี้ | fact ทุกตัวมี `max_age` และ rule ต้องประกาศว่ารับได้แค่ไหน |
| สรุปว่า deviation = ผิด | ทำให้โค้ชไม่เชื่อระบบตั้งแต่ครั้งแรกที่ใช้ | บังคับรายงานบริบทและผลลัพธ์ควบคู่เสมอ |
| ให้ LLM เขียน rule | ขัดกฎข้อ 3 ของ Blueprint §70 โดยตรง | LLM ใช้ได้เฉพาะเรียบเรียงคำอธิบายจาก rule ที่มีอยู่แล้ว |
