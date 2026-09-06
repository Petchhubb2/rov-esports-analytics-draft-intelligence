# 05 — Macro Event Detection

Layer 3 แปลง `observations.parquet` เป็น `events.parquet`
เอกสารนี้กำหนดกติกาของแต่ละ event ให้ชัดพอที่จะเขียนโค้ดและทดสอบได้

---

## 1. หลักการร่วม

**R1 · Detector ทุกตัวมี interface เดียวกัน**

```python
class EventDetector(Protocol):
    name: str
    version: str
    def detect(self, obs: ObservationFrame, params: dict) -> list[Event]: ...
```

ทำให้เปิด/ปิด detector รายตัวได้ และประเมินแยกได้

**R2 · Event ทุกตัวต้องแนบ `evidence` และ `coverage`**
ห้ามมี event ที่อธิบายที่มาไม่ได้ ตรงตามเจตนาของ §41

**R3 · Event ที่คำนวณจากช่วงเวลาที่ coverage ต่ำ ต้องถูกลดระดับ**

```
coverage ≥ 0.8  → รายงานตามปกติ
coverage 0.5–0.8 → รายงานพร้อมธง LOW_COVERAGE
coverage < 0.5   → ไม่รายงาน
```

**R4 · พารามิเตอร์ทุกตัวอยู่ใน `configs/params/events.yaml`**
ห้ามมีตัวเลขวิเศษในโค้ด

**R5 · Detector ทำงานบนแกน `game_clock` เท่านั้น** ไม่ใช่ `video_time`

---

## 2. Primitive ที่ใช้ร่วมกัน

เขียนครั้งเดียวใน `rov/events/base.py` แล้วทุก detector เรียกใช้

| Primitive | นิยาม |
|-----------|-------|
| `zone_transitions(slot)` | ลำดับ `(zone, enter_clock, exit_clock)` หลัง hysteresis |
| `pairwise_dist(t)` | เมทริกซ์ระยะ 10×10 ณ เวลา t |
| `cluster(team, t, eps)` | กลุ่มผู้เล่นที่อยู่ใกล้กันด้วย DBSCAN บน `eps` |
| `speed(slot, t)` | ขนาดของเวกเตอร์ความเร็ว |
| `nearest_enemy(slot, t)` | ระยะถึงศัตรูที่ใกล้ที่สุดที่ observed |
| `objective_timer(t)` | วินาทีถึงการเกิดของ dragon / slayer ครั้งถัดไป |
| `coverage(slots, t0, t1)` | สัดส่วน (slot × sample) ที่ source == DETECTION |

`objective_timer` มีสองแหล่ง ใช้ร่วมกันได้

**แหล่งที่ 1 · ตารางเวลาเกิด** (ยืนยันแล้ว ดู [08-game-reference.md](08-game-reference.md) §3)

| Objective | เกิดครั้งแรก | เกิดใหม่ทุก |
|-----------|-------------|-------------|
| Abyssal Dragon | 2:00 | 2:00 |
| Enraged Abyssal Dragon | 10:00 | 5:00 |
| Dark Slayer | 8:00 | 5:00 |
| Spirit Sentinel | 1:50 | 2:00 |

⚠️ ตัวเลขมาจากแหล่งก่อนแพตช์ 26 มิ.ย. 2026 ซึ่งมี "major jungle system changes"
ต้องวัดซ้ำจากคลิปจริง เก็บไว้ใน `configs/params/objectives.yaml` ไม่ใช่ในโค้ด

**แหล่งที่ 2 · สีของ mark บน minimap** (แม่นกว่า)

mark ของ Dragon เป็นสีเหลืองเมื่อมีชีวิต และสีเทาเมื่อเพิ่งถูกฆ่า
อ่านได้จาก ROI คงที่จุดเดียว ทำใน Phase 2

ใช้ร่วมกัน: ตารางบอกว่า *ควร* เกิดเมื่อไร สีบอกว่า *เกิดจริง* หรือยัง
ความต่างระหว่างสองค่านี้เองก็เป็นข้อมูล เพราะบอกว่า objective ถูกปล่อยทิ้งไว้นานแค่ไหน

---

## 3. Event ทีละตัว

### 3.1 RECALL / RETURN_BASE

ทำก่อนตัวอื่นเพราะเป็น primitive ที่ตัวอื่นต้องใช้กรอง

| หัวข้อ | รายละเอียด |
|--------|-----------|
| Input | zone transitions, alive |
| กติกา | ตำแหน่งกระโดดเข้า `BASE_*` ของฝ่ายตัวเอง โดย `alive == true` ตลอด และระยะกระโดด > `max_speed × Δt` |
| แยกจาก | ตายแล้วเกิดใหม่ (`alive` เป็น false ระหว่างทาง) |
| Output | `RECALL` ที่ start = เวลาที่หายจากตำแหน่งเดิม |
| Confidence | สูงเมื่อมีเฟรมยืนยันติดกัน ≥ 2 เฟรม |

**ความสำคัญ:** ถ้าไม่ตรวจ recall การเดินทางกลับฐานจะถูกนับเป็น rotation ปลอม
ที่มีระยะทางมหาศาล และจะทำให้ metric "movement distance" ผิดทั้งหมด

---

### 3.2 ROTATION

| หัวข้อ | รายละเอียด |
|--------|-----------|
| Input | zone transitions ต่อ slot |
| กติกา | เปลี่ยนจาก zone A → zone B โดยที่ A และ B อยู่คนละ macro-region และเวลาเดินทาง ≤ `rotation_max_sec` (แนะนำ 25) และไม่ใช่ RECALL และ `alive == true` |
| macro-region | จับกลุ่ม zone เป็น TOP_SIDE / MID / BOT_SIDE / BASE เพื่อไม่ให้การเดินภายในป่าตัวเองนับเป็น rotation |
| Output | `zone_from`, `zone_to`, `duration`, `path_length` |
| Confidence | ลดลงตามสัดส่วนเวลาที่ track เป็น COASTING |
| Failure mode | zone กระพริบที่ขอบ → แก้ด้วย hysteresis · การเดินผ่าน zone กลางทางถูกนับซ้ำ → รวม transition ที่ต่อเนื่องกันภายใน `merge_window_sec` |

ตัวอย่าง evidence

```json
{ "path": ["MID","RIVER_BOTTOM","DRAGON_LANE"],
  "duration": 13.0, "path_length": 0.34,
  "coasting_fraction": 0.08 }
```

---

### 3.3 GROUPING

| หัวข้อ | รายละเอียด |
|--------|-----------|
| Input | ตำแหน่งของทีมเดียวกัน ณ เวลา t |
| กติกา | DBSCAN ด้วย `eps = group_radius` (แนะนำ 0.08 normalized) ได้ cluster ขนาด ≥ 3 และคงอยู่ต่อเนื่อง ≥ `group_min_sec` (แนะนำ 3) |
| Output | `player_ids`, `size`, `centroid`, `zone`, `duration` |
| Confidence | จาก coverage ของสมาชิกทุกคนในช่วงนั้น |
| Failure mode | ระหว่าง teamfight ทุกคนอยู่ใกล้กันหมดจนได้ grouping ที่ไม่มีความหมาย → ตัด grouping ที่ทับกับ TEAMFIGHT ออกตอนสรุป |

`group_radius` ต้องปรับตามขนาดแมพจริง วัดจาก ground truth ว่าระยะเท่าไร
ที่มนุษย์เรียกว่า "รวมตัวกัน" แล้วใช้ค่านั้น อย่าเดา

---

### 3.4 OBJECTIVE_SETUP

Event ที่มีคุณค่าเชิงวิเคราะห์สูงสุดตัวหนึ่ง และตรงกับตัวอย่าง end-to-end ใน §80

| หัวข้อ | รายละเอียด |
|--------|-----------|
| Input | grouping, zone, objective_timer |
| กติกา | มีผู้เล่นทีมเดียวกัน ≥ 3 คนอยู่ใน `<OBJ>_PIT` หรือ `<OBJ>_PIT_APPROACH` ต่อเนื่อง ≥ `setup_min_sec` (แนะนำ 5) และ `objective_timer` ≤ `setup_lead_sec` |
| `setup_lead_sec` | **Dragon 45 วินาที** เพราะรอบเกิดคือ 120 วินาที · **Slayer 60 วินาที** เพราะรอบเกิดคือ 300 วินาที และเป็น objective ที่วางแผนล่วงหน้ามากกว่า |
| Output | `objective`, `team`, `players`, `arrival_order`, `seconds_before_spawn`, `duration` |
| Confidence | สูงขึ้นเมื่อ: จำนวนคนมากขึ้น, เข้าใกล้เวลาเกิด, coverage สูง |
| Failure mode | ทีมเดินผ่านหลุมระหว่างทางไปที่อื่น → แก้ด้วย `setup_min_sec` และเช็คว่าความเร็วเฉลี่ยต่ำ (ยืนรอ ไม่ใช่เดินผ่าน) |

`arrival_order` มีค่ามาก เพราะตอบคำถาม §2.2 ที่ว่า "ใครเข้า Zone ก่อน" โดยตรง
และเป็นวัตถุดิบของ player profile

---

### 3.5 GANK

ยากกว่าที่แผนเดิม §26 ประเมินไว้ ต้องระวังเรื่อง false positive มาก

| หัวข้อ | รายละเอียด |
|--------|-----------|
| Input | rotation, nearest_enemy, alive transitions, zone |
| กติกา (ทุกข้อต้องจริง) | 1. ผู้เล่น X เข้าสู่ lane ที่ตนไม่ได้อยู่ประจำ · 2. มีศัตรู observed อยู่ใน lane นั้น · 3. ระยะระหว่าง X กับศัตรูลดลงต่อเนื่อง ≥ 2 วินาที · 4. ระยะต่ำสุดถึงจุด ≤ `engage_radius` |
| ผลลัพธ์ | ถ้ามี `alive: true→false` ของฝ่ายใดฝ่ายหนึ่งภายใน `gank_window_sec` (แนะนำ 6) → `outcome: SUCCESS/FAILED` มิฉะนั้น `outcome: NO_ENGAGE` |
| Confidence | ต่ำโดยธรรมชาติ ตั้งเพดานไว้ที่ 0.85 จนกว่าจะมีข้อมูลจาก main view |
| Failure mode | การเดินผ่านเลนธรรมดาถูกนับเป็น gank · การ gank ที่ล้มเหลวเงียบ ๆ ตรวจไม่พบ |

**คำเตือน:** ถ้า minimap มี fog (G1) การ gank ส่วนใหญ่จะเกิดในจุดที่มองไม่เห็นศัตรู
ทำให้เงื่อนไขข้อ 2 เป็นเท็จเกือบตลอด ในกรณีนั้นให้ลดระดับเป็น
`GANK_ATTEMPT` ที่อาศัยเงื่อนไข 1 + การตายของศัตรูเท่านั้น และระบุไว้ชัดว่า recall ต่ำ

---

### 3.6 TEAMFIGHT

แผนเดิม §29 เสนอให้ใช้ main view ร่วมด้วย ซึ่งถูกต้องแต่แพง
ทำรุ่นที่ใช้เฉพาะ minimap + HUD ก่อน แล้ววัดว่าพอหรือไม่

| หัวข้อ | รายละเอียด |
|--------|-----------|
| Input | ตำแหน่งทุกคน, `alive` จาก HUD, `hp_frac` จาก HUD |
| กติกา v1 | มีผู้เล่น ≥ 4 คน (จากทั้งสองฝ่าย รวมกัน) อยู่ในรัศมี `fight_radius` (แนะนำ 0.10) และมีอย่างน้อย 1 ฝ่ายละ 2 คน และมีสัญญาณการปะทะ |
| สัญญาณการปะทะ | `hp_frac` ของอย่างน้อย 2 คนลดลงเร็วกว่า `hp_drop_rate` หรือมี `alive: true→false` |
| Output | `start`, `end`, `zone`, `blue_count`, `red_count`, `deaths_blue`, `deaths_red`, `winner` |
| การหาจุดจบ | จบเมื่อจำนวนคนในรัศมีลดต่ำกว่าเกณฑ์ต่อเนื่อง ≥ 3 วินาที |
| Confidence | สูงเมื่อมีทั้งการรวมตัวและการตาย · ต่ำเมื่อมีแค่การรวมตัว |

`hp_frac` จาก HUD คือกุญแจ มันเปลี่ยน teamfight detection จากการเดา
เป็นการสังเกตจริง และอ่านง่ายกว่าการวิเคราะห์ main view หลายเท่า
คุ้มค่าที่จะลงทุนทำ HUD reader ให้ดีตั้งแต่ Phase 2

---

### 3.6b OBJECTIVE_TAKEN 🟢 เพิ่มใหม่หลังค้นข้อมูล

Event ที่ตรวจง่ายและมีค่าสูง เป็นไปได้เพราะ minimap แสดงสถานะ objective ด้วยสี

| หัวข้อ | รายละเอียด |
|--------|-----------|
| Input | `objective_state` จาก minimap (เหลือง = มีชีวิต, เทา = เพิ่งถูกฆ่า) |
| กติกา | สีเปลี่ยนจาก ALIVE เป็น DEAD ยืนยันด้วย ≥ 2 เฟรมติดกัน |
| ทีมที่ได้ | ทีมที่มีคนอยู่ในหลุมมากกว่า ณ วินาทีที่เปลี่ยนสถานะ |
| Output | `objective`, `team`, `clock`, `players_present`, `contested` |
| `contested` | จริงเมื่อมีทั้งสองทีมอยู่ในหลุมภายใน 5 วินาทีก่อนหน้า |
| Confidence | สูงมาก เพราะมาจากการสังเกตสถานะโดยตรง |

Event นี้ปิดวงจรของ OBJECTIVE_SETUP ทำให้ตอบได้ว่า
"ทีมเซ็ตอัพแล้วได้ objective จริงกี่เปอร์เซ็นต์"
ซึ่งเป็น metric ที่โค้ชสนใจมากกว่าจำนวนครั้งที่เซ็ตอัพเฉย ๆ

---

### 3.7 DEATH / RESPAWN

| หัวข้อ | รายละเอียด |
|--------|-----------|
| Input | `alive` จาก HUD |
| กติกา | `alive` เปลี่ยน true→false ยืนยันด้วย ≥ 2 เฟรมติดกัน |
| Output | `slot`, `clock`, `zone_last_seen`, `respawn_clock` |
| Confidence | สูง เพราะมาจาก HUD โดยตรง |
| หมายเหตุ | `zone_last_seen` อาจเป็น null ถ้าตายในที่มืด ต้องยอมรับ ห้ามเดา |

---

### 3.8 SPLIT_PUSH และ LANE_SWAP

ทำทีหลัง มีคุณค่าน้อยกว่าและตรวจง่ายเมื่อมีของข้างบนแล้ว

- `SPLIT_PUSH`: ผู้เล่น 1 คนอยู่ใน lane ที่ห่างจาก centroid ของทีมเกิน `split_dist`
  ต่อเนื่อง ≥ 15 วินาที ขณะที่เพื่อน ≥ 3 คนรวมกันอยู่อีกฝั่ง
- `LANE_SWAP`: เปรียบเทียบ zone ที่ใช้เวลามากที่สุดของแต่ละ slot
  ในช่วง 0–3 นาที กับ role ที่ประกาศไว้ใน `match_players`

---

## 4. ลำดับการรัน Detector

มีลำดับพึ่งพากัน ต้องรันตามนี้

```
1. DEATH / RESPAWN      (จาก HUD ล้วน)
2. OBJECTIVE_TAKEN      (จากสี mark บน minimap ล้วน ไม่พึ่ง event อื่น)
3. RECALL               (ต้องรู้ death ก่อน เพื่อแยกออกจากการเกิดใหม่)
4. ROTATION             (ต้องรู้ recall ก่อน เพื่อไม่นับซ้ำ)
5. GROUPING
6. OBJECTIVE_SETUP      (ต้องมี grouping + objective_timer)
7. TEAMFIGHT            (ต้องมี death + hp)
8. GANK                 (ต้องมี rotation + death)
9. SPLIT_PUSH / LANE_SWAP
10. post-process: ตัด grouping ที่ทับ teamfight · รวม rotation ที่ต่อเนื่อง ·
    ผูก OBJECTIVE_SETUP เข้ากับ OBJECTIVE_TAKEN เพื่อคำนวณอัตราสำเร็จ
```

---

## 5. Layer 4 · จาก Event เป็น Profile

### 5.1 Metric ดิบก่อน แล้วค่อยตีความ

แผนเดิม §32 และ §81 แสดง profile ที่มีค่า "Style: Aggression 78"
ตัวเลขเหล่านี้ต้องมีที่มาชัดเจน ไม่ใช่คะแนนที่ตั้งขึ้น

ลำดับที่ถูก

```
1. metric ดิบ ที่นับได้ตรงไปตรงมา
2. normalize เทียบกับ peer group (role เดียวกัน patch เดียวกัน)
3. รวมเป็น style score พร้อมเปิดเผยสูตร
```

### 5.2 Metric ดิบต่อผู้เล่น

| Metric | นิยามที่คำนวณได้ |
|--------|------------------|
| First rotation target | zone ปลายทางของ ROTATION แรกหลังนาทีที่ 1 |
| Opening route | ลำดับ zone ใน 90 วินาทีแรก |
| Objective participation | สัดส่วนของ OBJECTIVE_SETUP ของทีมที่ผู้เล่นนี้อยู่ด้วย |
| Objective first-arrival rate | สัดส่วนที่เป็นคนแรกใน arrival_order |
| Teamfight participation | สัดส่วนของ TEAMFIGHT ที่อยู่ในรัศมี |
| Time in enemy half | วินาทีที่อยู่ในครึ่งแมพศัตรู หารด้วยเวลาเกม |
| Grouping frequency | จำนวน GROUPING ต่อ 10 นาที |
| Movement distance | ผลรวมระยะทางจาก OBSERVED เท่านั้น |
| Gank attempts | จำนวน GANK ต่อ 10 นาที |
| Deaths in enemy jungle | ตัวชี้วัดความเสี่ยง |

ทุกตัวต้องมาพร้อม `n_matches` และ `coverage_mean`

### 5.3 Style Score

```
aggression = z(time_in_enemy_half) · 0.4
           + z(gank_attempts)      · 0.3
           + z(deaths_in_enemy_jungle) · 0.3

objective  = z(objective_participation)    · 0.5
           + z(objective_first_arrival)    · 0.3
           + z(dragon_setup_rate)          · 0.2
```

โดย `z()` คือ z-score เทียบกับผู้เล่น role เดียวกันใน patch เดียวกัน
แล้วแปลงเป็นสเกล 0–100 ด้วย percentile

**สิ่งที่ต้องแสดงคู่กับคะแนนเสมอ**

```
Objective   88   (n=42 matches, coverage 0.91, percentile ในกลุ่ม jungler)
```

ตัวเลข 88 เพียงลำพังไม่มีความหมาย ถ้าไม่รู้ว่าเทียบกับใครและจากกี่แมตช์

### 5.4 เกณฑ์ขั้นต่ำก่อนแสดง Profile

```
n_matches ≥ 5      จึงจะแสดง profile
n_matches ≥ 15     จึงจะแสดง style score
coverage_mean ≥ 0.8 จึงจะแสดงโดยไม่มีคำเตือน
```

ต่ำกว่านี้ให้แสดงเฉพาะ metric ดิบพร้อม sample size

---

## 6. การประเมิน Event Detector

ต่อ event type ต้องรายงาน

```
                Precision  Recall   F1    n_gt   n_pred
ROTATION           0.91     0.88   0.89     47      45
GROUPING           0.86     0.90   0.88     22      23
OBJECTIVE_SETUP    0.94     0.79   0.86     14      12
GANK               0.62     0.55   0.58     11      10
TEAMFIGHT          0.88     0.92   0.90     13      14
```

เกณฑ์จับคู่: temporal IoU ≥ 0.5 และ type ตรงกัน (ดู 03-data-contracts.md §5)

**เกณฑ์ผ่าน Milestone 4**

| Event | F1 ขั้นต่ำ |
|-------|-----------|
| ROTATION | 0.85 |
| GROUPING | 0.85 |
| OBJECTIVE_SETUP | 0.80 |
| TEAMFIGHT | 0.80 |
| GANK | 0.60 — และต้องระบุบน UI ว่าเป็นค่าประมาณ |

GANK ตั้งเกณฑ์ต่ำโดยตั้งใจ เพราะข้อมูลที่มีไม่พอจะทำให้ดีกว่านี้
ถ้าทำได้ต่ำกว่า 0.6 ให้เอาออกจาก UI แทนที่จะแสดงข้อมูลที่ผิดครึ่งหนึ่ง
