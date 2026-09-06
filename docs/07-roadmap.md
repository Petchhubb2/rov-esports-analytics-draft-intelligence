# 07 — Roadmap และ Acceptance Gate

## 1. หลักการของ Gate

แต่ละเฟสมีเกณฑ์ผ่านที่เป็น **ตัวเลขที่วัดได้** ไม่ใช่ความรู้สึกว่า "น่าจะใช้ได้"
ถ้าไม่ผ่าน ห้ามเดินหน้าไปเฟสถัดไป — ให้เลือกอย่างใดอย่างหนึ่ง

```
1. ปรับปรุงจนผ่าน
2. ลดขอบเขตของเฟสนั้นแล้วนิยาม gate ใหม่อย่างเปิดเผย
3. ยกเลิกโครงการส่วนนั้น
```

ข้อ 3 เป็นตัวเลือกที่ถูกต้องจริง ๆ ในบางกรณี
ถ้า Milestone 1 ไม่ผ่านหลังพยายามเต็มที่ แปลว่าคลิปที่มีไม่เหมาะกับวิธีนี้
และการเดินหน้าต่อจะได้ระบบที่ให้ข้อมูลผิดอย่างมั่นใจ ซึ่งแย่กว่าไม่มีระบบ

---

## 2. ตารางเฟส

| เฟส | ชื่อ | ส่งมอบอะไร | Gate | ประมาณการ |
|-----|------|-----------|------|-----------|
| 0 | Video Forensics | `configs/layouts/*.yaml` + คำตอบ 10 ข้อ | layout-check ถูกต้อง 10/10 เฟรม | 0.5–1 วัน |
| 1 | Icon Detection | detector + eval harness + overlay video | P ≥ 0.95, R ≥ 0.95 (ไม่ occluded), MAE ≤ 0.008 | 1–2 สัปดาห์ |
| 2 | HUD + Identity | HUD reader, slot mapping, clock OCR, **objective state reader** | อ่าน alive ถูก ≥ 98%, clock ถูก ≥ 99%, objective state ถูก ≥ 99% | 1 สัปดาห์ |
| 3 | Tracking | tracker + observations.parquet | IDF1 ≥ 0.90, ID switch ≤ 3/เกม | 1–2 สัปดาห์ |
| 4 | Map Analytics | zone, path, heatmap | zone accuracy ≥ 0.95 เทียบ ground truth | 3–5 วัน |
| 5 | Macro Events | 8 detector + eval | F1 ตามตารางใน 05 | 2–3 สัปดาห์ |
| 6 | Profiles | player/team profile + metric ดิบ | ผ่านการตรวจสอบเชิงคุณภาพจากคนที่รู้เกม | 1 สัปดาห์ |
| 7 | Dashboard | Next.js + video sync | ผู้ใช้จริงใช้วิเคราะห์แมตช์ได้ครบรอบ | 2–3 สัปดาห์ |
| D0 | Draft data import | Liquipedia importer + cache | ตัวเลข pick/ban/win ตรงกับ rovmeta.com | 2.5 วัน + รันข้ามคืน |
| D | Draft v1 | composition engine (ขนานกับ 1–5) | ผู้เชี่ยวชาญเห็นด้วยกับคำแนะนำ ≥ 70% | ~12 วัน |
| D2 | Draft v2 (TEAM) | empirical matchup + shrinkage | เอาชนะการเดาแบบสุ่มบนข้อมูล holdout ได้ | 2 วัน |
| 8 | Integrated | player-specific draft + matchup แยกเลน | ต้องมี ≥ 30 แมตช์ที่ประมวลผลแล้ว | 1–2 สัปดาห์ |
| 9 | ML | prediction models | ต้องเอาชนะ rule-based baseline ได้ | เปิด |

ประมาณการเป็นเวลาของคนคนเดียวที่ทำเต็มเวลา และมี **ความไม่แน่นอนสูงมากในเฟส 1 และ 3**
สองเฟสนี้อาจใช้เวลาสองเท่าของที่ประมาณไว้ หรืออาจไม่สำเร็จเลย

---

## 3. รายละเอียดของเฟสที่ตัดสินชะตาโครงการ

### Phase 0 · Video Forensics — เริ่มพรุ่งนี้ได้

สิ่งที่ต้องมีก่อน: คลิปแข่งจริง 2–3 คลิป จากรายการที่ต่างกัน

```
Day 1 เช้า   เปิดคลิปด้วย VLC หยุดทีละเฟรม ตอบคำถาม 10 ข้อใน 01-assessment.md §4
Day 1 บ่าย   เขียน rov probe + rov calibrate + rov layout-check
             ได้ configs/layouts/<id>.yaml ที่ผ่านการยืนยันด้วยตา
```

**Deliverable ที่จับต้องได้:** ภาพเฟรมที่มีกรอบสีวาดทับ minimap, HUD, นาฬิกา
ถูกตำแหน่งทั้งหมด

ถ้าคำตอบข้อ G1 คือ "ไม่มี fog เห็น 10 ตัวเสมอ" ให้ปรับประมาณการของ Phase 3
ลงเหลือครึ่งเดียว เพราะปัญหาที่ยากที่สุดหายไป

---

### Phase 1 · Icon Detection — Gate ที่ตัดสินทั้งโครงการ

ลำดับงานภายในเฟส

```
1.1  rov sample          สุ่มเฟรมตาม PTS                      1 วัน
1.2  rov background      median background model               1 วัน
1.3  eval harness ก่อน   รูปแบบ ground truth + rov eval detect 1 วัน
1.4  annotator ง่าย ๆ    label 100 เฟรม                        1 วัน
1.5  detector v1         residual + color + contour            2-3 วัน
1.6  จูนด้วยตัวเลข        วนแก้จนผ่าน gate                       3-5 วัน
1.7  overlay video       ตรวจด้วยตาว่าสมเหตุสมผล                 0.5 วัน
```

**สังเกตว่า eval harness (1.3) และ label (1.4) มาก่อน detector (1.5)**
นี่คือหัวใจของ G9 ถ้าทำสลับลำดับ จะเสียเวลาไปกับการจูนแบบเดาหลายวัน

**Gate**

```
บนเฟรมทดสอบ 100 เฟรม จากอย่างน้อย 2 แมตช์:

precision (all)              ≥ 0.95
recall (non-occluded)        ≥ 0.95
recall (occluded)            ≥ 0.70
mean position error          ≤ 0.008 normalized
false positive จาก ping/minion ≤ 2%
```

**ถ้าไม่ผ่าน — ลำดับการแก้**

```
1. ตรวจว่า background model สะอาดหรือไม่ (เปิดดู background.png ด้วยตา)
2. ตรวจว่า color threshold ครอบคลุมทุกสภาพแสงของ broadcast หรือไม่
3. ลองเพิ่มความละเอียด: upscale minimap crop 2× ด้วย INTER_CUBIC ก่อน detect
4. ลอง template matching แบบ multi-scale เสริม
5. ถ้ายังไม่ผ่าน → ค่อยพิจารณา train YOLO ขนาดเล็กบน 500 เฟรมที่ label
```

ข้อ 3 มักได้ผลดีเกินคาดและถูกมาก icon ขนาด 18 px ที่ upscale เป็น 36 px
ทำให้ contour detection แม่นขึ้นชัดเจน

ข้อ 5 คือทางหนีสุดท้าย และถึงตอนนั้นเราจะมี label แล้ว 500 เฟรม
ซึ่งพอสำหรับ YOLO-nano ที่ตรวจแค่ 2 class (blue icon, red icon)

---

### Phase 3 · Tracking — ความเสี่ยงสูงสุดอันดับสอง

```
3.1  Kalman filter ต่อ slot                     2 วัน
3.2  cost function + Hungarian                  2 วัน
3.3  state machine (dead/recall/coast/unknown)  2 วัน
3.4  eval: IDF1, ID switch ด้วย motmetrics      1 วัน
3.5  label ground truth identity 200 เฟรม       1 วัน
3.6  จูน w_d, w_a, c_null, max_speed            3-5 วัน
```

**Gate**

```
IDF1                    ≥ 0.90
ID switch               ≤ 3 ต่อเกม 20 นาที
ID switch ระหว่าง teamfight  รายงานแยก (คาดว่าจะสูงกว่า)
track continuity        ≥ 0.85 นอกช่วง teamfight
```

**ตัวชี้วัดที่สำคัญกว่าตัวเลขรวม:** ดู ID switch ที่เกิดกับ jungler โดยเฉพาะ
เพราะ jungler เคลื่อนที่มากที่สุดและ profile ของ jungler มีค่าวิเคราะห์สูงสุด
ถ้า jungler สลับ identity บ่อย ระบบจะให้ข้อสรุปที่ผิดในเรื่องที่คนสนใจที่สุด

---

## 4. เส้นทางขนาน

งานสองสายนี้ไม่แย่งทรัพยากรกันและควรทำพร้อมกัน

```
สาย VISION (เสี่ยงสูง)         สาย DRAFT (เสี่ยงต่ำ)
─────────────────────          ─────────────────────
                               D0  Liquipedia importer  ← เริ่มวันแรก
Phase 0  layout                D0c รันดึงข้อมูลข้ามคืน   ← รันเบื้องหลัง
Phase 1  detection             D1-D2 attribute schema + กรอก 30 ตัว
Phase 2  HUD + objective       D3  state machine + Global Ban-Pick
Phase 3  tracking              D4  composition analysis
Phase 4  zones                 D5  trait counter/synergy
Phase 5  events                D6  recommendation + series value
                               D7  CLI
                               D8  empirical matchup (context TEAM)
        └──────────┬───────────┘
                   ▼
            Phase 7  Dashboard
            Phase 8  Integrated + matchup แยกเลน
```

ประโยชน์ของการทำขนาน: ถ้าสาย vision ติดขัด ยังมีของส่งมอบจากสาย draft
และ Draft v1 เป็นเครื่องมือที่ทีม esports ใช้ได้จริงโดยไม่ต้องรออะไรเลย

**D0 ควรเริ่มวันแรกสุดของโครงการ** เพราะการดึงข้อมูลถูกจำกัดที่
60 requests/ชั่วโมง จึงกินเวลาจริงเป็นวัน ยิ่งเริ่มเร็วยิ่งดี
และมันรันเบื้องหลังโดยไม่แย่งเวลาคนไปทำงาน vision

---

## 5. Dataset Plan

ตาม §76 ของแผนเดิม เริ่มที่ 10–20 แมตช์ ขยายทีหลัง
แต่ต้องเจาะจงกว่านั้นว่าจะ label อะไรเท่าไร

| ประเภท label | ปริมาณ | ใช้ทำอะไร | เวลาโดยประมาณ |
|--------------|--------|-----------|----------------|
| Position (เฟรมเดี่ยว) | 100 เฟรม × 2 แมตช์ | eval detection | 4 ชม. |
| Identity (ต่อเนื่อง) | 200 เฟรม × 2 แมตช์ | eval tracking | 4 ชม. |
| Occluded case | 50 เฟรมจาก teamfight | eval กรณียากโดยเฉพาะ | 2 ชม. |
| Zone boundary | 50 เฟรมที่ขอบ zone | จูน hysteresis | 1 ชม. |
| Event | 3 แมตช์เต็ม | eval event detector | 6 ชม. |
| Draft | ~~200 แมตช์~~ | ~~draft v2~~ | **0 ชม. — ดึงจาก Liquipedia API แทน** |

รวมประมาณ 17 ชั่วโมงของการ label ซึ่งเป็นการลงทุนที่คุ้มที่สุดในโครงการนี้
(ลดจาก 24 ชั่วโมงเพราะข้อมูล draft ดึงอัตโนมัติได้)

**เลือกแมตช์อย่างไร:** อย่าเลือกแมตช์ที่ดูสวย เลือกให้ครอบคลุมกรณียาก

```
1 แมตช์ที่มี teamfight เยอะ (กรณี occlusion)
1 แมตช์ที่ยาว 25+ นาที (late game ที่ทุกคนรวมกลุ่ม)
1 แมตช์จาก broadcast คนละรายการ (ทดสอบว่า layout config ใช้ซ้ำได้ไหม)
```

---

## 6. สิ่งที่ต้องทำในสัปดาห์แรก

เรียงตามลำดับ ไม่ข้ามขั้น

```
□ ตั้ง repo: git init, pyproject.toml, pre-commit (ruff + mypy)
□ เขียน Liquipedia importer แล้วสั่งรันดึงข้ามคืน  ← ทำก่อน เพราะกินเวลาจริง
□ รวบรวมคลิปแข่งจริง 3 คลิป จาก 2 รายการขึ้นไป
□ ตอบคำถาม Phase 0 ทั้ง 12 ข้อ ด้วยการดูคลิปจริง
□ วัดเวลาเกิด objective ซ้ำ เพราะแพตช์ มิ.ย. 2026 แก้ระบบ jungle
□ บันทึกคำตอบลง configs/layouts/<id>.yaml
□ เขียน rov probe + rov calibrate + rov layout-check
□ ยืนยันด้วยภาพว่า ROI ถูกต้องทุกเฟรม
□ ตัดสินใจจากคำตอบ G1 ว่าจะออกแบบ tracking แบบมี fog หรือไม่มี
□ จัดลำดับฮีโร่จากข้อมูลที่ดึงมา แล้วกรอก attribute 30 ตัวแรก
```

**ห้ามทำในสัปดาห์แรก:** ตั้ง Postgres, เขียน FastAPI, เปิดโปรเจกต์ Next.js,
ติดตั้ง PyTorch, ออกแบบหน้า dashboard

ทุกอย่างข้างต้นทำได้ด้วยไฟล์ Python ไม่กี่ไฟล์กับ OpenCV
และถ้าเริ่มจากการตั้ง infrastructure จะเสียเวลาไปหนึ่งสัปดาห์
โดยยังไม่รู้ว่าปัญหาหลักแก้ได้หรือเปล่า

---

## 7. สัญญาณเตือนที่ต้องหยุดและทบทวน

| สัญญาณ | ความหมาย | ทำอย่างไร |
|--------|----------|-----------|
| จูน threshold มา 5 วันแล้ว metric ไม่ขยับ | วิธีการอาจผิด ไม่ใช่พารามิเตอร์ผิด | เปลี่ยนวิธี อย่าจูนต่อ |
| detection ดีแต่ tracking แย่ | cost function หรือ gate ผิด | ตรวจ max_speed จาก ground truth จริง |
| metric ดีแต่ overlay ดูผิด | ground truth มีปัญหา หรือ eval มี bug | เชื่อสายตา ตรวจ eval ก่อน |
| event เยอะเกินจริง | hysteresis ไม่พอ หรือ threshold หลวม | ดู zone_raw เทียบ zone |
| profile ของผู้เล่นทุกคนดูเหมือนกัน | metric ไม่แยกแยะ หรือ normalize ผิด | ตรวจ distribution ของ metric ดิบ |
| อยากเพิ่ม LLM มาช่วยตีความ | เป็นสัญญาณว่าข้อมูลยังไม่พอ | กลับไปแก้ข้อมูล ไม่ใช่เพิ่ม LLM |

แถวสุดท้ายตรงกับหลักการข้อ §5 ของแผนเดิมที่ว่า "อย่าให้ LLM เดา Macro"
ซึ่งเป็นข้อที่ถูกต้องและควรยึดไว้

---

## 8. นิยามของ "เสร็จ" สำหรับ V1

ระบบถือว่าใช้งานได้จริงเมื่อ

```
□ อัปโหลดคลิปแข่ง 1 คลิป แล้วได้ผลวิเคราะห์ครบภายใน 15 นาที
□ ตำแหน่งผู้เล่นแม่นถึงระดับที่ heatmap อ่านแล้วตรงกับที่คนดูเกมจำได้
□ timeline ของ event กดแล้ววิดีโอกระโดดไปถูกจุด
□ ทุกตัวเลขบนหน้าจอกดดูที่มาได้ ว่ามาจากกี่ observation และ coverage เท่าไร
□ Draft simulator ให้คำแนะนำที่โค้ชอ่านแล้วเข้าใจเหตุผล
□ ระบบบอกได้ว่า "ไม่รู้" ในจุดที่ไม่รู้จริง ๆ
```

ข้อสุดท้ายสำคัญที่สุด และเป็นสิ่งที่แยกระบบวิเคราะห์ที่ใช้ได้จริง
ออกจากระบบที่ดูดีแต่เชื่อไม่ได้
