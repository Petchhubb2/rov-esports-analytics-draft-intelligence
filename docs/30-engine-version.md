# 30 — Engine Version + Clean Evaluation Window

PHASE M1.5 · GOAL 1 + GOAL 2 · 2026-09-11

> **หมายเหตุเลขเอกสาร** คำสั่งขอ `docs/29-engine-version.md` แต่เลข 29 ถูกใช้
> ไปแล้วกับ [29-counter-knowledge-report.md](29-counter-knowledge-report.md) ในวันเดียวกัน
> ชุด M1.5 จึงเลื่อนเป็น **30 (version+window) · 31 (hero coverage) · 32 (synergy audit)**

---

## 1. ทำไมต้องล็อกเวอร์ชัน

ผลการวัดเทียบกันได้ก็ต่อเมื่อรู้ว่าวัดจาก engine ตัวไหน ระบบมีสามชั้นที่เปลี่ยนได้
อิสระจากกัน และเปลี่ยนชั้นไหนตัวเลขก็ขยับได้ทั้งนั้น

```
โค้ด      recommend.py · stats.py · lanes.py · composition.py
          counterknowledge.py · winconditions.py
น้ำหนัก    weights_for · ban_weights_for · EXTRA_WEIGHTS · ROLE_FLOOR
          MIN_PAIR_GAMES · SHRINKAGE_K
ความรู้    heroes.yaml · hero_assessment.yaml · format.yaml
          knowledge/counter/ · knowledge/macro/
```

จด commit อย่างเดียวจะพลาดกรณีไฟล์ความรู้ถูกแก้โดยไม่ commit
จดไฟล์ความรู้อย่างเดียวจะพลาดกรณีโค้ดเปลี่ยนสูตร

[`rov/eval/version.py`](../packages/core/rov/eval/version.py) จึง **คำนวณลายนิ้วมือสด
จากไฟล์จริงทุกครั้ง** ไม่ใช่ค่าคงที่ที่คนต้องจำไปอัปเดตเอง — ค่าคงที่แบบนั้น
คือค่าที่จะค้างอยู่กับอดีตแล้วหลอกคนอ่าน

---

## 2. เวอร์ชันปัจจุบัน

```
fingerprint   8686ec1315db
commit        e1ed66b        (M1 CounterKnowledge)

code          7241108b92d4
  recommend.py          28c9d0fc6190
  stats.py              b49e9e1779fe
  lanes.py              cb3c640a0b87
  composition.py        3f2d2265d761
  counterknowledge.py   f5e32887ee38
  winconditions.py      500d1fc4b779

knowledge     7cc2bc71fdef
  configs/draft/heroes.yaml            1b1d8dcfc895
  configs/draft/hero_assessment.yaml   9193ea0c1999
  configs/draft/format.yaml            7b4fa4b8b438
  knowledge/counter                    c1bd8dfe6040
  knowledge/macro                      e6b22632de8e

weights       89ff8b569ff8
```

> ⚠️ `fingerprint` ข้างบนคำนวณ ณ commit `e1ed66b` **ก่อน** เพิ่มไฟล์ของ M1.5
> ค่าปัจจุบันดูได้จาก `python scripts/run_m15_status.py` เสมอ เอกสารนี้ไม่ใช่แหล่งความจริง
> ของลายนิ้วมือ — โค้ดเป็น

### 2.1 ปริมาณความรู้ ณ จุดนี้

| คลัง | จำนวน |
|---|---|
| ฮีโร่ทั้งหมด | 119 |
| ฮีโร่ที่ประเมิน attribute แล้ว | **30** |
| counter evidence | **15** |
| counter threats | 8 |
| counter capabilities | 19 |
| macro rules | 42 |
| เกมที่มีข้อมูล | 861 |

### 2.2 น้ำหนัก

```
pick(0,0)     meta 0.3915 · winrate 0.4785 · counter 0.0800 · synergy 0.0500
pick_meta_share  0.45          ban_meta_share  0.75
role_floor       0.35          min_pair_games  8
shrinkage_k      30            min_games_reliable  15

extra (5 ตัว)    composition 0.0 · lane_counter 0.0 · synergy_adj 0.0
                 trait_counter 0.0 · counter_evidence 0.0
                 → เปิดอยู่: ไม่มีเลย
```

### 2.3 `comparable` — เทียบผลได้หรือยัง

`EngineVersion.comparable` เป็น `False` เมื่อ working tree ยังมีของที่ไม่ commit
เพราะไม่มีใครย้อนกลับมาดูได้ว่าตอนนั้นโค้ดหน้าตาอย่างไร
**ผลการวัดที่บันทึกไว้ตอน tree สกปรก ใช้อ้างอิงไม่ได้**

---

## 3. หน้าต่างข้อมูลสะอาด

### 3.1 ⛔ ตอนนี้ว่างเปล่า — 0 เกม

```
cutoff        หลัง 2026-09-06
สถานะ         ยังว่าง · มี 84 นัดรอแข่ง
เกมที่ใช้วัดได้  0
นัดที่รออยู่    84 · 2026-09-10 ถึง 2026-10-31
```

**นี่คือสถานะที่ถูกต้อง ไม่ใช่บั๊ก** ข้อมูลล่าสุดที่มีคือ 2026-09-06 ซึ่งเป็นวันเดียวกับ
cutoff พอดี จึงยังไม่มีเกมไหนอยู่หลังเส้นนี้

| รายการ | เกมที่มีข้อมูล | นัดที่ยังไม่มีข้อมูล | ช่วง |
|---|---|---|---|
| RPL 2026 Summer (ไทย) | 291 | 0 | — |
| **RPL 2026 Winter (ไทย)** | 93 | **50** | 2026-09-10 → 2026-10-25 |
| RPL 2025 Winter (ไทย) | 232 | 0 | — |
| GCS 2026 Spring (ไต้หวัน) | 196 | 0 | — |
| **GCS 2026 Summer (ไต้หวัน)** | 49 | **34** | 2026-09-11 → 2026-10-31 |

84 นัดกำลังจะแข่งในอีก 7 สัปดาห์ข้างหน้า เริ่มพรุ่งนี้ (2026-09-10 ผ่านไปแล้ว
วันนี้ 2026-09-11 คือวันแรกของ GCS Summer)

### 3.2 ทำไมตัดที่ 2026-09-06

เพราะเป็นวันสุดท้ายที่มีข้อมูลตอนปิด M1 เกมทุกเกมก่อนหน้านั้นถูกใช้ไปแล้ว
ไม่ทางใดก็ทางหนึ่ง

| ใช้ไปอย่างไร | ที่ไหน |
|---|---|
| เป็น train ของ benchmark | docs/22 · docs/25 |
| เป็น eval ที่ **ดูผลไปแล้ว** | validation window · holdout window |
| เป็นตัวคำนวณ `data_check` | counter evidence ทั้ง 15 ข้อ |
| เป็นฐานของ presence/matchup | ทุกคำแนะนำที่ระบบให้ |

### 3.3 กติกา — บังคับด้วยโค้ด ไม่ใช่แค่เขียนไว้

[`rov/eval/cleanwindow.py`](../packages/core/rov/eval/cleanwindow.py)

```python
ALLOWED_PURPOSES = frozenset({"measurement", "report"})

def assert_measurement_only(purpose: str) -> None:
    if purpose not in ALLOWED_PURPOSES:
        raise CleanWindowMisuse(...)
```

`clean_series()` เรียก `assert_measurement_only()` เสมอ จะดึงข้อมูลออกมาต้อง
เขียนวัตถุประสงค์ลงไปเป็นตัวอักษร

| วัตถุประสงค์ | ผล |
|---|---|
| `measurement` · `report` | ✅ ผ่าน |
| `weight_tuning` · `threshold_tuning` · `rule_selection` · `fit` · `training` | ⛔ `CleanWindowMisuse` |

มันหยุดคนที่ตั้งใจโกงไม่ได้ แต่ทำให้การโกงต้อง**เกิดขึ้นอย่างจงใจและเห็นได้ในโค้ด**
แทนที่จะเกิดขึ้นเงียบ ๆ ด้วยความเคยชิน

### 3.4 การจัดการวันที่อ่านไม่ออก

ซีรีส์ที่ `parse_date` อ่านไม่ออก **ถูกจัดเข้าฝั่ง "เคยดูแล้ว" เสมอ**
เพราะการเดาว่ามันอยู่หลัง cutoff จะทำให้หน้าต่างสะอาดปนเปื้อน
ซึ่งแพงกว่าการเสียตัวอย่างไปไม่กี่ชิ้นมาก

มีเทสต์คุมทิศทางนี้ไว้ (`test_an_unreadable_date_goes_to_the_seen_side_not_the_clean_side`)

---

## 4. ⛔ สิ่งที่ห้ามทำจนกว่าหน้าต่างจะมีข้อมูล

| ห้าม | เหตุผล |
|---|---|
| optimize `counter_evidence` | ไม่มีหลักฐานอิสระให้พิสูจน์ |
| optimize `synergy_adj` · `composition` · `trait_counter` | เหมือนกัน |
| แตะ ban weights หรือ pick weights | หน้าต่างเดิมถูกดูหมดแล้ว |
| **ถอยไปใช้หน้าต่าง validation/holdout เดิม** | มันเลิกเป็นหลักฐานอิสระตั้งแต่ M0.75 |
| ลด cutoff ลงเพื่อให้มีข้อมูล | เท่ากับยกเลิกหน้าต่างสะอาดทิ้ง |

**ข้อที่ยากที่สุดคือข้อ 4** — เวลาอยากรู้ผล ความอยากจะพาไปหาหน้าต่างที่มีข้อมูล
เอกสารนี้และโค้ดจึงเขียนไว้ชัดว่าทำไมถึงทำไม่ได้

---

## 5. เมื่อไรถึงกลับมาทำต่อได้

```
เงื่อนไข        มีเกมในหน้าต่างสะอาดอย่างน้อย ~150-200 เกม
                (เท่ากับ holdout เดิมที่มี 142 ดราฟต์ · 476 ตานับคะแนน)
คาดว่า          ปลายเดือนตุลาคม 2026 เมื่อ RPL Winter และ GCS Summer เดินไปได้ครึ่งทาง
วิธีตรวจ        python scripts/run_m15_status.py
```

เมื่อถึงตอนนั้น **รันได้ครั้งเดียว** ต่อการตัดสินใจหนึ่งครั้ง
กติกาเดียวกับ holdout ใน [docs/24 §7](24-ban-intelligence-spec.md)
