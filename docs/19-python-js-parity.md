# 19 — Python / JavaScript Parity

ตรวจเมื่อ 2026-09-11

---

## 1. ทำไมถึงมีของซ้ำสองชุด

กระดาน Draft Room เป็น **ไฟล์ HTML เดียวที่เปิดออฟไลน์ได้** และคิดคะแนนสด
ระหว่างดราฟต์ ซึ่งเรียก Python ไม่ได้ สูตรบางส่วนจึงต้องเขียนซ้ำเป็น JavaScript

เหตุผลที่เลือกแบบนี้ (จาก [docs/14-deployment.md](14-deployment.md) และการตัดสินใจ 2026-09-11)

1. ห้องซ้อม/หลังเวทีเน็ตไม่นิ่ง ไฟล์เดียวไม่มีวันล่มกลางดราฟต์
2. ดราฟต์มีเวลาจำกัดต่อตา latency เป็นศูนย์สำคัญกว่าฟีเจอร์
3. ลิขสิทธิ์ภาพฮีโร่ยังไม่เคลียร์ให้ deploy public ได้อยู่แล้ว

**ผลที่ตามมาซึ่งต้องยอมรับ:** ทุกสูตรที่หน้าเว็บใช้ มีโอกาสเพี้ยนจากฝั่ง Python
เอกสารนี้คือรายการทุกจุดที่ต้อง sync และสถานะว่ามีอะไรคอยจับหรือยัง

---

## 2. กติกาที่ใช้อยู่

1. **Python เป็น source of truth เสมอ** — แก้ Python ก่อน แล้วตามไปแก้ JS
2. ค่าคงที่ที่ส่งผ่าน `draft_data.json` ได้ **ให้ส่งผ่าน data อย่าเขียนซ้ำ**
   (เช่น `shrinkage_k`, `baseline_wr`, `min_pair_games` ทำแบบนี้อยู่แล้ว — ปลอดภัยที่สุด)
3. ค่าที่เขียนซ้ำจริง ๆ ต้องมีเทสต์ใน `tests/unit/test_web_board.py` ที่แกะจาก
   ทั้งสองฝั่งมาเทียบกัน ไม่ใช่แค่เช็คว่า "มีตัวแปรอยู่"

---

## 3. ตารางจุดที่ต้อง sync ทั้งหมด

### 3.1 ส่งผ่านข้อมูล (ปลอดภัย — ไม่นับเป็นของซ้ำ)

| ค่า | Python | ส่งผ่าน | JS |
|---|---|---|---|
| `SHRINKAGE_K = 30` | `stats.py:20` | `draft_data.shrinkage_k` | `K` (`:1145`) |
| `baseline_win_rate` | `stats.py` | `draft_data.baseline_wr` | `PRIOR` (`:1145`) |
| `MIN_PAIR_GAMES = 8` | `recommend.py:41` | `draft_data.min_pair_games` | `MINPAIR` (`:1145`) |
| `MIN_GAMES_RELIABLE = 15` | `stats.py:23` | `draft_data.min_games_reliable` | ใช้ผ่าน `D.` |
| `MIN_LANE_PAIR_GAMES` | `lanes.py` | `draft_data.min_lane_pair_games` | `MINLANE` (`:1182`) |

**วิธีนี้ควรเป็นค่าเริ่มต้นของทุกค่าคงที่ใหม่** — ถ้าส่งผ่าน data ได้ อย่าเขียนซ้ำ

### 3.2 เขียนซ้ำ + มีเทสต์คุม ✅

| # | ตรรกะ | Python | JS | เทสต์ |
|---|---|---|---|---|
| 1 | ลำดับ ban/pick | `configs/draft/format.yaml` `sequence` | `SEQ` (`:1148`) | `test_js_sequence_matches_format_yaml` |
| 2 | จำนวน ban/pick | `format.yaml` `bans_per_team`/`picks_per_team` | `BANS`, `PICKS` (`:1155`) | `test_js_bans_and_picks_match_format_yaml` |
| 3 | Global Ban-Pick | `format.yaml` `global_ban_pick` | `GBP` (`:1234`) | `test_js_global_ban_pick_matches_format_yaml` |
| 4 | เวลาต่อตา | `format.yaml` `turn_clock` | `CLOCK` (`:1159`) | `test_js_turn_clock_matches_format_yaml` + `test_unverified_clock_must_say_so_on_screen` |
| 5 | สูตรน้ำหนัก | `weights_for()` `recommend.py:95` | `weightsFor()` (`:1327`) | `test_js_weight_formula_matches_python` — ทดสอบ 30 combination |
| 6 | สเกล counter/synergy (-3, +3) | `_scale()` `recommend.py:150` | `scale()` (`:1192`) | `test_js_component_scale_matches_python` |
| 7 | `ROLE_FLOOR = 0.35` | `recommend.py:45` | `:1313` | `test_js_role_fit_matches_python` |
| 8 | `LANE_OWN_SHARE = 0.5` | `recommend.py:50` | `:1281` | `test_js_role_fit_matches_python` |
| 9 | Composition — `CC_SCALE`, `WC_MIN_W`, `GAP_AT`, `STRONG_AT` | `composition.py` | `:1951-1953` | `test_js_composition_constants_match_python` |
| 10 | Composition — ชื่อมิติ | `composition.py analyze()` | `COMP_DIMS` (`:1965`) | `test_js_composition_dimensions_match_python_labels` |
| 11 | Composition — ตัวเลขจริง | `analyze()` | `compDims()` | `test_js_and_python_agree_on_a_real_composition` — เทียบถึงทศนิยม |

### 3.3 เขียนซ้ำ + **ไม่มีเทสต์คุม** ⚠️

| # | ตรรกะ | Python | JS | ความเสี่ยง |
|---|---|---|---|---|
| **12** | **`counter_score`** — `(adjusted - prior) * 100 * confidence` | `stats.py:194` และ `lanes.py:86` (**สองที่ใน Python เอง!**) | `cscore()` (`:1191`) | 🔴 **สูง** — เป็นแกนของ counter/synergy ทั้งระบบ ถ้าเพี้ยนอันดับจะสลับโดยไม่มีใครรู้ |
| **13** | **`main_lane` / flex detection** | `lanes.py:123` | `mainLaneOf()` (`:1806`) | 🟡 กลาง — กระทบ `role_fit` และป้าย "เฟลก" บนหน้าจอ |
| **14** | `_top_weighted` / `_saturating_sum` | `composition.py:94`, `:103` | `topW`, `satSum` (`:1955`, `:1959`) | 🟢 ต่ำ — ข้อ 11 เทียบผลลัพธ์อยู่แล้ว แต่ไม่ได้เทียบตัวฟังก์ชันตรง ๆ |

### 3.4 **มีเฉพาะฝั่ง JS — ไม่มีของฝั่ง Python เลย** 🔴

| # | ตรรกะ | JS | ปัญหา |
|---|---|---|---|
| **15** | **`winCondition()`** — ตัดสินว่าคอมพ์เป็นสายต้นเกม/ท้ายเกม/กลาง ๆ ด้วยเกณฑ์ `tempo.avg <= -0.12` และ `>= +0.12` | `:1928` | **ไม่มีอะไรเทียบได้เพราะฝั่ง Python ไม่มีแนวคิดนี้เลย** · CLI กับเว็บให้ข้อสรุปคนละแบบ · เกณฑ์ ±0.12 ไม่มีที่มาเขียนไว้ |
| **16** | `compTempo()` — เฉลี่ย tempo ของ 5 ตัว | `:1908` | เช่นเดียวกัน |
| **17** | `compThreats()` — หาตัวศัตรูที่กดคอมพ์เราหนักสุด | `:1917` | เป็น logic ที่มีค่า แต่ติดอยู่บนเว็บ CLI ใช้ไม่ได้ |
| **18** | `renderComp()` เกณฑ์ gaps/strengths | `:2000` | ใช้ `GAP_AT`/`STRONG_AT` ที่มีเทสต์แล้ว แต่การจัดกลุ่มเป็นข้อความอยู่แค่ JS |

**ข้อ 15 คือช่องว่างที่อันตรายที่สุดในเอกสารนี้** — เป็นการตัดสินใจเชิงกลยุทธ์
("คอมพ์นี้ต้องรีบจบ") ที่ผู้ใช้เห็นและเชื่อ แต่มีอยู่ที่เดียวและไม่มีใครตรวจ

---

## 4. ปัญหาที่ค้นพบเพิ่ม: Python ซ้ำกันเอง

`counter_score()` ถูกเขียน **สองครั้งในฝั่ง Python เอง**

```
packages/core/rov/draft/stats.py:194   MatchupStat.counter_score()
packages/core/rov/draft/lanes.py:86    LaneMatchup.counter_score()
```

ทั้งสองมีสูตรเดียวกัน แต่เป็นคนละคลาสและไม่มีเทสต์เทียบกัน
ถ้าวันหนึ่งแก้ที่เดียว `counter` แบบ TEAM กับแบบ LANE จะคิดคนละสเกล

**นับรวมแล้วสูตรเดียวนี้อยู่ใน 3 ที่: `stats.py`, `lanes.py`, `cscore()` ใน JS**

---

## 5. สิ่งที่ต้องทำ เรียงตามความเร่งด่วน

| ลำดับ | งาน | แรง | ปิดความเสี่ยงข้อ |
|---|---|---|---|
| 1 | เทสต์ parity ของ `counter_score` ↔ `cscore` | 30 นาที | 12 |
| 2 | รวม `counter_score` ใน Python ให้เหลือที่เดียว (mixin หรือฟังก์ชันร่วม) + เทสต์ | 1 ชม. | §4 |
| 3 | ย้าย `winCondition()` มาเป็น `composition.win_condition()` ใน Python + เทสต์ parity + เขียนที่มาของเกณฑ์ ±0.12 ลงใน docstring | 2 ชม. | 15, 16 |
| 4 | เทสต์ parity ของ `main_lane` ↔ `mainLaneOf` | 30 นาที | 13 |
| 5 | ย้าย `compThreats()` มา Python ให้ CLI ใช้ได้ด้วย | 2 ชม. | 17 |

รวม ≈ **6 ชั่วโมง** ปิดช่องว่าง parity ได้ทั้งหมด

---

## 6. ทางออกระยะยาว (L5 ใน audit)

ปัญหาที่ต้นเหตุคือ **สูตรถูกเขียนเป็นโค้ดสองภาษา** แทนที่จะเป็น **ข้อมูลที่ทั้งสองภาษาอ่าน**

แนวทางที่เสนอ — ไม่ต้องทำตอนนี้ แต่ควรเป็นเป้าเมื่อจำนวน factor เพิ่มขึ้น

```
composition_spec.json  ←  สร้างจาก Python (source of truth)
        │
        ├──> Python อ่านแล้ว execute
        └──> ฝังใน draft_data.json ให้ JS อ่านแล้ว execute
```

โดย spec เก็บเป็น `{dimension, source_field, aggregator, params}`
และ aggregator มีแค่ไม่กี่ตัว (`top_weighted`, `saturating_sum`, `weakest_mean`, `mean`)
ที่เขียน implementation ไว้ทั้งสองภาษา แล้วมีเทสต์เทียบเฉพาะ aggregator

**ข้อดี:** เพิ่มมิติใหม่ = เพิ่มบรรทัดใน spec ไม่ต้องแตะ JS เลย
**ข้อเสีย:** aggregator ยังต้องเขียนซ้ำอยู่ดี แต่มีแค่ 4 ตัวและนิ่งแล้ว

**เกณฑ์ว่าเมื่อไรควรทำ:** เมื่อมิติ composition เกิน 15 ตัว หรือเมื่อ
`recommend()` เพิ่ม factor เกิน 8 ตัว — ก่อนหน้านั้นการเขียนซ้ำ + เทสต์ยังคุ้มกว่า

---

## 7. กฎสำหรับงานต่อจากนี้

ทุก PHASE ที่เพิ่มตรรกะใหม่ ต้องตอบสามข้อนี้ก่อน merge

1. ตรรกะนี้ต้องอยู่บนหน้าเว็บด้วยไหม
   - ไม่ต้อง → เขียนใน Python อย่างเดียว **จบ**
   - ต้อง → ไปข้อ 2
2. ส่งผ่าน `draft_data.json` เป็นข้อมูลแทนได้ไหม
   - ได้ → ส่งผ่านข้อมูล **จบ** (ปลอดภัยที่สุด)
   - ไม่ได้ (ต้องคิดสดตอนดราฟต์) → ไปข้อ 3
3. เขียนซ้ำใน JS **พร้อมเทสต์ parity ในคอมมิตเดียวกัน**
   - เทสต์ต้องแกะค่าจากทั้งสองฝั่งมาเทียบ ไม่ใช่ hardcode ค่าที่คาดหวัง
