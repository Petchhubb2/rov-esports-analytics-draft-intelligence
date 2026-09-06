# 04 — Vision Pipeline

เอกสารนี้ครอบคลุม Phase 0–3 ซึ่งเป็นส่วนที่ตัดสินว่าโครงการทั้งหมดจะสำเร็จหรือไม่

---

## 1. Phase 0 · Calibration

### 1.1 ขั้นตอน

```
1. ดึงเฟรมนิ่ง 20 เฟรม จากช่วงกลางเกม (หลีกเลี่ยง intro และ replay)
2. หา minimap ROI
3. ยืนยันว่า ROI คงที่ตลอดคลิป
4. หา transform pixel → normalized map
5. วัดขนาด icon
6. หา ROI ของ HUD และนาฬิกา
7. เขียน configs/layouts/<id>.yaml
8. รัน rov layout-check เพื่อดูภาพยืนยันด้วยตา
```

### 1.2 วิธีหา minimap ROI แบบกึ่งอัตโนมัติ

minimap มีขอบกรอบชัดเจนและเนื้อหาภายในนิ่ง จึงหาได้จาก "ความแปรปรวนต่ำ"

```
1. สุ่ม 200 เฟรมจากทั้งคลิป
2. คำนวณ per-pixel standard deviation ข้ามเฟรม
3. บริเวณ main view จะมี SD สูงมาก (กล้องเคลื่อน)
   บริเวณ minimap จะมี SD ต่ำ (พื้นหลังนิ่ง มีแค่ icon ขยับ)
   บริเวณ HUD คงที่จะมี SD ต่ำสุด
4. threshold + morphology → หาสี่เหลี่ยม SD ต่ำที่มีขนาดใกล้เคียงจัตุรัส
   ในควอดแรนต์ที่คาดหวัง
5. เสนอ ROI ให้คนยืนยัน/ลากปรับด้วยมือ
```

ขั้นตอนที่ 5 สำคัญ อย่าทำอัตโนมัติเต็มรูปแบบ ทำครั้งเดียวต่อรายการแข่ง
การให้คนยืนยันใช้เวลา 30 วินาที และตัดความเสี่ยงทั้งชุดออกไป

### 1.3 Transform

รองรับสองแบบ เลือกจากคำตอบข้อ 5 ใน Phase 0 checklist

**แบบ A · Affine** (ถ้า minimap เป็นสี่เหลี่ยมตรง)

```
x_norm = (px - roi.x) / roi.w
y_norm = (py - roi.y) / roi.h
```

**แบบ B · Homography** (ถ้า minimap ถูกบิดมุมหรือเป็นสี่เหลี่ยมข้าวหลามตัด)

ระบุจุดอ้างอิง 4 จุดที่รู้พิกัดจริงบนแมพ เช่น ฐานสองฝั่งและหลุม objective สองหลุม
แล้วคำนวณ `cv2.getPerspectiveTransform`

เก็บ transform ไว้ใน config ไม่คำนวณใหม่ทุกครั้ง

### 1.4 ตัวอย่างไฟล์ layout

```yaml
# configs/layouts/rov_pro_league_720p.yaml
id: rov_pro_league_720p
source_resolution: [1280, 720]
verified_on: "2026-09-06"
verified_by: cm

minimap:
  roi: { x: 18, y: 16, w: 186, h: 186 }
  transform: affine          # หรือ homography
  fog_of_war: null           # ← G1 ต้องตอบก่อนเริ่ม Phase 1
  color_semantics: null      # side | ally_enemy  ← ต้องตอบเช่นกัน
  icon:
    diameter_px: [16, 24]
    ring_thickness_px: 2
  teams:
    blue: { hue: [95, 125], sat_min: 90, val_min: 70 }
    red:  { hue: [0, 12],   sat_min: 90, val_min: 70 }
  # ตำแหน่งคงที่ของ mark objective — เหลือง = มีชีวิต, เทา = เพิ่งถูกฆ่า
  objective_marks:
    dragon: { x: 0, y: 0, w: 0, h: 0 }   # ← วัดจากคลิปจริง
    slayer: { x: 0, y: 0, w: 0, h: 0 }
    sat_alive_min: 80
  # ตำแหน่งป้อมทั้งหมด ใช้เป็น static mask กัน false positive
  tower_positions: []                     # ← วัดจากคลิปจริง

clock:
  roi: { x: 596, y: 8, w: 88, h: 26 }
  format: "MM:SS"

hud:
  left:  { x: 0,    y: 120, w: 74, h: 400, slots: 5 }
  right: { x: 1206, y: 120, w: 74, h: 400, slots: 5 }
  portrait_size_px: 48
  dead_indicator: grayscale     # grayscale | countdown | both

scoreboard:
  roi: { x: 420, y: 4, w: 440, h: 36 }

replay:
  banner_roi: { x: 0, y: 0, w: 1280, h: 60 }
  detect_by: [clock_regression, minimap_missing, banner_template]
```

**Acceptance ของ Phase 0:** `rov layout-check` วาดกรอบทุก ROI ทับเฟรมสุ่ม 10 เฟรม
และทุกกรอบอยู่ตรงตำแหน่งจริงทั้ง 10 เฟรม

---

## 2. Frame Sampling

### กฎเวลา

ห้ามคำนวณเวลาจาก `frame_index / fps` เพราะ

- คลิปที่ตัดต่อมาอาจเป็น variable frame rate
- ffmpeg บางเวอร์ชันรายงาน fps เฉลี่ยไม่ตรงกับความจริง

ใช้ PTS จาก PyAV ตรง ๆ

```python
for packet in container.demux(video_stream):
    for frame in packet.decode():
        pts_sec = float(frame.pts * video_stream.time_base)
```

### อัตราสุ่มแบบปรับตัว

```
ค่าเริ่มต้น            2 fps
ช่วงที่ตรวจพบ combat   5–10 fps
ช่วงก่อน objective spawn ±30 วินาที   5 fps
```

ทำเป็นสองรอบ: รอบแรกสุ่ม 1 fps ทั้งเกมเพื่อหาช่วงน่าสนใจ
รอบสองสุ่มถี่เฉพาะช่วงนั้น วิธีนี้ประหยัดเวลา decode ราว 60%

---

## 3. Frame State Classifier (G3)

จำเป็นก่อน detection ไม่ใช่หลัง

| สัญญาณ | วิธีตรวจ | บ่งชี้ |
|--------|----------|--------|
| นาฬิกาถอยหลัง | เทียบ game_clock กับเฟรมก่อน | REPLAY |
| นาฬิกาไม่เดิน > 5 วินาที | game_clock คงที่ขณะ video_time เดิน | PAUSE |
| ไม่พบกรอบ minimap | edge density ใน ROI ต่ำผิดปกติ | REPLAY / NON_GAME |
| HUD หายไป | template match บริเวณ HUD ล้มเหลว | NON_GAME / DRAFT |
| พบ banner replay | template matching บริเวณด้านบน | REPLAY |
| หน้า draft | ตรวจ layout ของหน้าเลือกตัว | DRAFT |

รวมด้วยกฎง่าย ๆ ก่อน: ถ้าสัญญาณใดชี้ว่าไม่ใช่ LIVE ให้เป็น non-LIVE
แล้วทำ temporal smoothing (median filter หน้าต่าง 5 เฟรม) เพื่อกันการกระพริบ

**อย่าใช้ ML ที่นี่** กฎเหล่านี้ตรวจสอบได้ด้วยตาและแก้ง่ายเมื่อ broadcast เปลี่ยน layout

---

## 4. Minimap Detection

### 4.1 Background Model (G5)

```
1. เลือก 300 เฟรมที่ frame_state == LIVE กระจายทั้งเกม
2. crop minimap ทุกเฟรม → stack เป็น array (300, H, W, 3)
3. background = np.median(stack, axis=0)
4. เก็บเป็น background.png
```

median ทนต่อ outlier — icon ที่เคลื่อนที่จะถูกกรองออกโดยธรรมชาติ
เพราะไม่มี icon ตัวใดอยู่ที่พิกัดเดิมเกินครึ่งของ 300 เฟรม

### ⚠️ แก้จากข้อมูลที่ตรวจสอบแล้ว — ต้องใช้ rolling median

เอกสารรุ่นแรกเสนอ median ครั้งเดียวทั้งเกม **ใช้ไม่ได้**
เพราะยืนยันแล้วว่า icon ป้อมบน minimap "ค่อย ๆ จางสีลงตามความเสียหาย
และหายไปเมื่อถูกทำลาย" (ดู [08-game-reference.md](08-game-reference.md) §4)
พื้นหลังจึงเปลี่ยนอย่างต่อเนื่องตลอดเกม ไม่ใช่เปลี่ยนเป็นครั้งคราว

**⚠ ข้อสรุปนี้ถูกหักล้างด้วยการวัดจริงแล้ว** ดู [09-build-log.md](09-build-log.md) §5

วัดแล้วพบว่าหน้าต่างสั้น **แย่กว่า** หน้าต่างยาวชัดเจน

| หน้าต่าง | precision | recall (ไม่ทับ) |
|---------|-----------|-----------------|
| 75 วินาที | 0.919 | 0.926 |
| ทั้งคลิป | 0.972 | 0.969 |

เพราะฮีโร่ที่อยู่นิ่งนานจะครองเวลาเกินครึ่งของหน้าต่างสั้น แล้วกลายเป็นพื้นหลัง

ส่วนป้อม: เป็นสี่เหลี่ยมเล็กที่พื้นที่ต่ำกว่าเกณฑ์ขนาด icon ตัวกรองขนาดจัดการได้
และถ้ายังหลุด ให้ใส่ `tower_positions` ใน layout เพื่อ mask ทิ้ง เพราะป้อมอยู่ตำแหน่งคงที่

```
ค่าเริ่มต้นที่ใช้จริง  bg_window_sec = 600
```

คำนวณล่วงหน้าเป็นช่วง ๆ แล้ว cache ไม่ต้องคำนวณใหม่ทุกเฟรม
นอกจากนี้ health pack ที่หายไปเมื่อป้อมชั้นหนึ่งพัง ก็เป็นอีกสิ่งที่เปลี่ยนพื้นหลัง

### 4.2 ท่อ Detection

```
crop minimap
   │
   ├─▶ residual = |frame − background|          ← ของที่เคลื่อนไหว
   │
   ├─▶ hsv = cvtColor(frame, BGR2HSV)
   │      team_mask = inRange(hue_blue) | inRange(hue_red)   ← วงแหวนทีม
   │
   ▼
mask = (residual > τ_res) AND team_mask
   │
   ▼
morphology: open(3×3) → close(5×5)              ← ลบ noise, ปิดรู
   │
   ▼
connectedComponentsWithStats
   │
   ▼
กรองด้วย: area ∈ [a_min, a_max]
          circularity > 0.65
          radius ∈ layout.icon.diameter_px / 2
   │
   ▼
candidate detections
   │
   ▼
แยก blob ที่ติดกัน (icon ทับกัน)                ← ดู 4.4
   │
   ▼
ระบุทีมจากสีวงแหวนรอบนอก
   │
   ▼
detections.parquet
```

### 4.3 สิ่งที่ต้องกรองออก และวิธีกรอง

| สิ่งรบกวน | ลักษณะ | วิธีแยก |
|-----------|--------|---------|
| Minion | เล็กกว่า ไม่มีวงแหวน สีจาง · **เคลื่อนที่ จึงรอด background subtraction** | area + saturation + circularity และใส่ lane corridor mask เพื่อลดน้ำหนัก detection เล็กที่อยู่กลางเลนพอดี |
| ป้อม | อยู่กับที่ แต่ **สีจางลงเรื่อย ๆ ตามความเสียหาย** | rolling median จัดการให้ · เพิ่ม static mask ที่พิกัดป้อมเป็นชั้นกันพลาด |
| Ping / marker | วงแหวนขยาย มีอายุสั้น (1–2 วินาที) | ติดตามข้ามเฟรม ถ้ารัศมีโตขึ้นเรื่อย ๆ = ping |
| Objective icon | ตำแหน่งคงที่ที่หลุม | เพิ่ม static mask จาก layout config |
| เอฟเฟกต์เตือน | กระพริบเป็นจังหวะ | temporal filter |
| Ward / ตาลูก | เล็ก อยู่กับที่ | area + static ข้ามหลายเฟรม |

แนะนำให้เก็บ `reject_reason` ไว้ในโหมด debug จะช่วยจูน threshold ได้เร็วขึ้นมาก

### 4.4 กรณี Icon ทับกัน — ความเสี่ยงอันดับหนึ่ง (§77)

ลำดับความพยายาม จากถูกที่สุดไปแพงที่สุด

**ระดับ 1 · Distance transform + watershed**
blob ที่ติดกันมักมี "คอคอด" ใช้ `cv2.distanceTransform` หาแกนกลาง
แล้ว watershed แยกออก ได้ผลดีเมื่อทับกันไม่เกินราวครึ่งหนึ่ง

**ระดับ 2 · ใช้ prior จากจำนวนที่คาดหวัง**
ถ้ารู้ว่าทีมน้ำเงินต้องมี 5 ตัว แต่ตรวจได้ 3 blob และหนึ่งใน blob มีพื้นที่
ประมาณ 2.5 เท่าของ icon เดี่ยว → ใช้ k-means บน pixel ใน blob นั้นด้วย k=3

**ระดับ 3 · ยอมรับว่าไม่รู้**
ถ้าแยกไม่ได้ ให้บันทึกเป็น cluster เดียวที่มี `member_count_estimate`
และตั้ง track ของทุกคนในกลุ่มเป็น `COASTING` พร้อม confidence ต่ำ

**ห้ามทำ:** เดาว่าใครอยู่ตรงไหนในกลุ่มโดยไม่มีหลักฐาน
ระหว่าง teamfight ตำแหน่งต่างกัน 20 pixel ไม่มีผลต่อ macro analysis อยู่แล้ว
แต่ identity ที่สลับกันมีผลมหาศาล การยอมรับความไม่รู้จึงถูกกว่าการเดา

---

---

## 4.5 Objective State Reader — ของแถมที่คุ้มที่สุด 🟢

ค้นข้อมูลแล้วพบว่า minimap แสดงสถานะ objective ด้วยสีโดยตรง

```
Abyssal Dragon mark  สีเหลือง = มีชีวิต
                     สีเทา    = เพิ่งถูกฆ่า
```

(ที่มา: samurai-gamers · ดู [08-game-reference.md](08-game-reference.md) §4)

นี่เป็น ROI คงที่เพียงสองจุดบน minimap อ่านง่ายกว่า OCR หลายเท่า
และให้ข้อมูลที่มีค่าสูงมากต่อ macro analysis

```python
# rov/minimap/objective_state.py
def read_objective_state(minimap_crop, layout) -> dict:
    out = {}
    for obj in ("dragon", "slayer"):
        roi   = layout.minimap.objective_marks[obj]
        patch = crop(minimap_crop, roi)
        hue, sat = mean_hsv(patch)
        out[obj] = "ALIVE" if sat > layout.sat_alive_min else "DEAD"
    return out
```

**สิ่งที่ได้จากงานครึ่งวัน**

| ได้อะไร | เดิมต้องทำอย่างไร |
|---------|-------------------|
| `OBJECTIVE_TAKEN` event พร้อมเวลาที่แม่น | ต้องวิเคราะห์ main view ซึ่งยากมาก |
| `objective_timer` ที่ยืนยันด้วยการสังเกตจริง | ต้องคำนวณจากตารางเวลาอย่างเดียว ซึ่งผิดได้ถ้าไม่มีใครฆ่า |
| ตรวจสอบว่า `OBJECTIVE_SETUP` จบลงอย่างไร | เดาไม่ได้เลย |

⚠️ ต้องยืนยันสีที่แน่นอนจากคลิปจริง และเพิ่มพิกัด `objective_marks`
เข้าไฟล์ layout ตอน Phase 0

**ทำในเฟสไหน:** Phase 2 คู่กับ HUD reader ไม่ใช่ Phase 5
เพราะเป็น input ของ event detection ไม่ใช่ผลลัพธ์

---

## 5. Hero Identification และ Tracking

### 5.1 ที่มาของ Identity

```
match_players (slot → player_id, hero_id, team_id)
        │  กำหนดครั้งเดียวต่อเกม จาก draft หรือยืนยันด้วยมือ
        ▼
HUD slot order  ←── คงที่ตลอดเกม
        │
        ▼
tracker ทำงานกับ "slot" ไม่ใช่ "hero"
```

จุดสำคัญเชิงออกแบบ: **tracker ไม่จำเป็นต้องรู้ว่าฮีโร่ชื่ออะไร**
มันแค่ต้องรักษาความต่อเนื่องของ slot 10 ช่อง
การแปลง slot → hero เป็นงานของ lookup table ที่ตั้งครั้งเดียว
ทำให้ปัญหาง่ายลงมากและเลี่ยง classification ทั้งหมดได้

### 5.2 Appearance Feature

ถึงจะไม่ตัดสินด้วย appearance เพียงอย่างเดียว แต่ก็ยังมีประโยชน์เป็นสัญญาณเสริม

```
1. crop patch ขนาด 24×24 รอบจุดศูนย์กลาง detection
2. ลบวงแหวนทีมออก (mask วงแหวนรอบนอก 2 px)
3. resize เป็น 16×16, แปลงเป็น Lab color space
4. feature = histogram 3D ของ Lab (8×8×8 bins) ทำ normalize
5. ความคล้าย = 1 − Bhattacharyya distance
```

template อ้างอิงต่อ slot สร้างจากสองทาง
- portrait ใน HUD ย่อขนาดลง (มีให้ตั้งแต่เฟรมแรก)
- ค่าเฉลี่ยแบบ online จาก patch ที่ track ได้มั่นใจสูง (อัปเดตเมื่อ conf > 0.9)

อย่าอัปเดต template ตอน confidence ต่ำ เพราะจะเกิด template drift
และทำให้ identity switch กลายเป็นถาวร

### 5.3 Kalman Filter

state vector ต่อ slot

```
[x, y, vx, vy]

process model: constant velocity
Δt = ช่วงเวลาจริงระหว่างเฟรมที่สุ่ม (ไม่ใช่ค่าคงที่)
```

พารามิเตอร์ที่ต้องจูน อยู่ใน `configs/params/track.yaml`

| พารามิเตอร์ | ความหมาย | ค่าเริ่มต้นแนะนำ |
|-------------|----------|------------------|
| `q_pos`, `q_vel` | process noise | จูนจากข้อมูลจริง |
| `r_meas` | measurement noise | จาก MAE ของ detector |
| `max_speed` | ความเร็วสูงสุด (normalized/วินาที) | วัดจาก ground truth ที่ percentile 99 |
| `coast_max_sec` | นานสุดที่ยอมให้ COASTING | 3.0 |

**อย่าเดาค่าเหล่านี้** วัด `max_speed` จาก ground truth จริง
เพราะมันคือ gate ที่กันการกระโดดข้ามแมพผิด ๆ ได้ดีที่สุด

### 5.4 Assignment (G6)

ต่อเฟรม แยกทำทีละทีมเมื่อรู้ทีมจากสี (ลดจาก 10×N เหลือ 5×N สองรอบ)

```
สร้าง cost matrix C ขนาด 5 × (N + 5)
  คอลัมน์ 0..N-1  = detection จริง
  คอลัมน์ N..N+4  = "ไม่จับคู่" ราคาคงที่ c_null

C[i][j] = w_d · d_norm(track_i.predicted, det_j)
        + w_a · (1 − appearance_sim(track_i.template, det_j.patch))
        + penalty

penalty = ∞  ถ้า track_i.alive == False        (จาก HUD, G4)
        = ∞  ถ้า d_norm > max_speed · Δt        (gate ความเร็ว)
        = ∞  ถ้า det_j.team != track_i.team และ team_conf สูง
        = p_teleport  ถ้า det_j อยู่ที่ฐานของฝ่ายตัวเอง
                      และ track_i กำลัง RECALL

แก้ด้วย scipy.optimize.linear_sum_assignment(C)
```

น้ำหนักเริ่มต้นแนะนำ `w_d = 1.0`, `w_a = 0.4`, `c_null = 0.5`
แล้วจูนโดยดูค่า IDF1 บน ground truth

### 5.5 State Machine ต่อ Slot

```
                  ┌──────────────┐
      HUD: dead   │              │  HUD: alive
   ┌─────────────▶│     DEAD     │──────────────┐
   │              │              │              │
   │              └──────────────┘              ▼
   │                                     ┌──────────────┐
   │                     assign สำเร็จ    │              │
   │              ┌──────────────────────▶│   OBSERVED   │
   │              │                       │              │
   │      ┌───────┴──────┐                └──────┬───────┘
   └──────│   COASTING   │◀──────────────────────┘
          │              │   ไม่มี assign
          └───────┬──────┘
                  │ เกิน coast_max_sec
                  ▼
          ┌──────────────┐
          │   UNKNOWN    │  x, y = null
          └──────────────┘
```

กรณีพิเศษที่ต้องจัดการ

| เหตุการณ์ | พฤติกรรมที่ถูกต้อง |
|-----------|-------------------|
| ตาย | HUD บังคับเข้า DEAD ทันที ห้ามรับ detection |
| เกิดใหม่ | ปรากฏที่ฐานฝ่ายตัวเอง reset Kalman ที่พิกัดฐาน |
| Recall กลับฐาน | ตำแหน่งกระโดดไกลแบบถูกกฎหมาย ต้องมีทางผ่าน gate |
| เข้า fog (ถ้ามี) | COASTING → UNKNOWN ห้ามค้างตำแหน่งเดิมไว้เป็น "ความจริง" |
| ออกจาก fog | รับ detection ใหม่ อาจต้องพึ่ง appearance มากขึ้นชั่วคราว |

การจัดการ recall เป็นจุดที่พลาดกันบ่อย ถ้าไม่มีเส้นทางพิเศษ
tracker จะปฏิเสธ detection ที่ฐานเพราะเกิน max_speed แล้วเข้า UNKNOWN ยาว

---

## 6. Zone Mapping

### 6.1 นิยาม Zone

`configs/zones/rov_map_v1.yaml` เก็บ polygon ในพิกัด normalized

```yaml
version: 1
zones:
  - id: DRAGON_PIT
    kind: objective
    polygon: [[0.62,0.72],[0.72,0.72],[0.72,0.82],[0.62,0.82]]
  - id: DRAGON_PIT_APPROACH
    kind: approach
    parent: DRAGON_PIT
    polygon: [...]
  - id: MID
    kind: lane
    polygon: [...]
  # DS_LANE, DRAGON_LANE, RIVER_TOP, RIVER_BOTTOM,
  # TOP_JUNGLE_BLUE, TOP_JUNGLE_RED, BOT_JUNGLE_BLUE, BOT_JUNGLE_RED,
  # SLAYER_PIT, SLAYER_PIT_APPROACH, BASE_BLUE, BASE_RED
```

Zone ประเภท `approach` สำคัญมากสำหรับ objective setup
เพราะทีมจะรวมตัว *รอบ* หลุมก่อนลงหลุม ไม่ใช่ยืนในหลุม

### 6.2 Lookup แบบเร็ว

แทนที่จะทดสอบ point-in-polygon ทุกครั้ง (ช้าที่หลักล้านแถว)
ให้ rasterize zone map ครั้งเดียวเป็นภาพ palette 512×512

```python
zone_id = zone_raster[int(y * 512), int(x * 512)]   # O(1)
```

สร้างครั้งเดียวตอนโหลด config แล้ว cache ไว้

### 6.3 Hysteresis กันการกระพริบ

ผู้เล่นที่เดินอยู่บนขอบ zone จะทำให้เกิด zone change ปลอมนับสิบครั้งต่อนาที
และจะกลายเป็น "rotation" ปลอมทั้งหมด

กติกา: เปลี่ยน zone อย่างเป็นทางการก็ต่อเมื่อ

```
อยู่ใน zone ใหม่ติดต่อกัน ≥ dwell_min_sec  (แนะนำ 1.5 วินาที)
AND ระยะจากขอบ zone ≥ margin              (แนะนำ 0.01 normalized)
```

เก็บทั้ง `zone_raw` (ทันที) และ `zone` (หลัง hysteresis) ไว้ในตาราง
`zone_raw` ใช้ debug `zone` ใช้ทำ event

---

## 7. Metrics และเกณฑ์ผ่าน

### Detection

| Metric | นิยาม | เกณฑ์ผ่าน Milestone 1 |
|--------|-------|----------------------|
| Precision | TP/(TP+FP) ที่ระยะ ≤ 0.02 | ≥ 0.95 |
| Recall (ไม่ occluded) | | ≥ 0.95 |
| Recall (occluded) | | ≥ 0.70 |
| Mean position error | ระยะ normalized เฉลี่ยของ TP | ≤ 0.008 |

### Tracking

| Metric | นิยาม | เกณฑ์ผ่าน Milestone 2 |
|--------|-------|----------------------|
| IDF1 | F1 ของการจับคู่ identity | ≥ 0.90 |
| ID switch | จำนวนครั้งที่ slot สลับกัน | ≤ 3 ต่อเกม 20 นาที |
| Track continuity | สัดส่วนเวลาที่ track เป็น OBSERVED | รายงานไว้ ไม่ตั้งเกณฑ์ |
| MOTA | มาตรฐาน MOT | รายงานไว้ |

ใช้ไลบรารี `motmetrics` หรือ `TrackEval` ไม่ต้องเขียนเอง

**ID switch คือ metric ที่สำคัญที่สุดในโครงการนี้ทั้งหมด**
เพราะ 1 ครั้งที่สลับ jungler กับ mid จะทำให้ player profile ทั้งสองคนผิดทั้งเกม
ในขณะที่ position error 0.01 แทบไม่มีผลต่อข้อสรุปเชิง macro

### รายงาน Coverage เสมอ

ทุกครั้งที่รายงาน metric ต้องแนบ

```
frames evaluated:      100
frames LIVE:           94
observed coverage:     0.87   ← สัดส่วนของ (slot × frame) ที่ OBSERVED
occluded fraction:     0.11
```

ตัวเลข accuracy ที่ไม่มี coverage กำกับ ตีความไม่ได้
