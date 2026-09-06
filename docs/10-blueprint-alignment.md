# 10 — การเทียบ Blueprint กับโค้ดจริง

เอกสารนี้ทำให้ [`RoV_Esports_Analytics_FINAL_Blueprint_and_Prompt.md`](../RoV_Esports_Analytics_FINAL_Blueprint_and_Prompt.md)
กับโค้ดในเครื่องนับตรงกัน

---

## 1. สามเสาหลัก

Blueprint §3 กำหนดโครงสร้างระดับบนสุดเป็นสามเสา

```
Video Analysis  ·  Draft System  ·  Scouting
                        ↓
                  Macro Planner
                        ↓
                Intelligence Layer
                        ↓
                  Web Dashboard
```

ต่างจากแผนเดิมที่ §1 เขียนว่า 2 ระบบ (Macro Analytics + Draft Intelligence)
สิ่งที่เพิ่มคือ **Scouting** ยกขึ้นเป็นเสาหลัก และ **Macro Planner**
เป็นจุดบรรจบที่แผนเดิมไม่มีเลย

---

## 2. แผนที่ 44 โมดูล → โค้ด

สถานะ: ✅ ใช้งานได้และมีเทสต์ · 🟡 มีบางส่วน · ⬜ ยังไม่เริ่ม

### เสา 1 · Video Analysis

| # | โมดูล | สถานะ | ที่อยู่ในโค้ด |
|---|-------|-------|----------------|
| 01 | Video Ingestion | ✅ | `rov/ingest/{probe,sampler,service}.py` · `apps/api` · `rov/store` |
| 02 | Broadcast Layout Parser | 🟡 | `rov/config/layout.py` (สคีมา ROI) · ยังไม่มีตัวอ่าน HUD/นาฬิกา |
| 03 | Minimap Vision | ✅ | `rov/minimap/{background,detect}.py` |
| 04 | Hero Identification | ⬜ | จะอยู่ที่ `rov/minimap/{appearance,templates}.py` |
| 05 | Player Identity | 🟡 | `rov/domain/types.py::MatchPlayer` (ชนิดข้อมูล) |
| 06 | Player Tracking | ⬜ | จะอยู่ที่ `rov/tracking/` |
| 07 | Map Calibration | 🟡 | `rov/config/layout.py::Layout.scaled_to` · ยังไม่มี auto-calibrate |
| 08 | Map / Zone Engine | ✅ | `rov/config/zones.py` (raster lookup O(1)) |
| 09 | Ground Truth / Annotation | 🟡 | `rov/eval/synthetic.py` (สร้าง GT ได้) · ยังไม่มีเครื่องมือ label |
| 10 | Event Detection | ⬜ | จะอยู่ที่ `rov/events/` |
| 11 | Macro Analytics | ⬜ | จะอยู่ที่ `rov/macro/` |
| 12 | Heatmap | ⬜ | จะอยู่ที่ `rov/mapping/heatmap.py` |
| 13 | Player Analytics | ⬜ | |
| 14 | Team Analytics | ⬜ | |

### เสา 2 · Draft System

| # | โมดูล | สถานะ | ที่อยู่ในโค้ด |
|---|-------|-------|----------------|
| 15 | Draft Simulator | ✅ | `rov/draft/state.py` + `rov draft sim` · undo/reset/history/Global Ban-Pick |
| 16 | Pick Engine | ✅ | `rov/draft/recommend.py` — จัดอันดับจากข้อมูลจริง |
| 17 | Ban Engine | ✅ | `rov/draft/recommend.py` — มองจากมุมศัตรูตอนแบน |
| 18 | Counter Engine | 🟡 | `rov/draft/meta.py` — context=TEAM · LANE รอ vision |
| 19 | Matchup Engine | 🟡 | `rov/draft/stats.py` — context=TEAM พร้อม shrinkage · LANE รอ vision |
| 20 | Synergy Engine | 🟡 | `rov/draft/stats.py` — มี expected_synergy แล้ว ยังไม่หักความแข็งของทีม |
| 21 | Composition Engine | ✅ | `rov/draft/composition.py` — 10 มิติ ปฏิเสธการให้คะแนนเมื่อ attribute ไม่ครบ |
| 22 | Draft Score Engine | ⬜ | |
| 23 | Patch / Meta Engine | 🟡 | `rov/store/models.py::Patch` + `rov/draft/stats.py` (pick/ban/win rate จริง) |
| 24 | Draft Recommendation | ✅ | 4 องค์ประกอบ พร้อมเหตุผลและจำนวนเกมกำกับ |
| 25 | Player-specific Draft | ⬜ | |
| 26 | Team-specific Draft | ⬜ | |
| — | **Draft Data Import** | ✅ | `rov/draft/importer/` — ไม่ได้อยู่ใน 44 แต่จำเป็นต่อทั้ง 15–26 |

### เสา 3 + Macro Planning

| # | โมดูล | สถานะ | หมายเหตุ |
|---|-------|-------|----------|
| 27 | Macro Knowledge Base | ⬜ | ออกแบบไว้ใน [11-macro-planner.md](11-macro-planner.md) |
| 28 | Macro Rule Engine | ⬜ | |
| 29 | Macro Planner | ⬜ | |
| 30 | Primary/Secondary/Emergency | ⬜ | `rov/domain/enums.py::PlanTier` มีแล้ว |
| 31 | Decision Tree | ⬜ | |
| 32 | Actual vs Recommended | ⬜ | |
| 33 | Scouting | ⬜ | |
| 34 | Prediction / ML | ⬜ | ห้ามเริ่มก่อนมี ground truth (กฎข้อ 2) |

### โครงสร้างพื้นฐาน

| # | โมดูล | สถานะ | ที่อยู่ในโค้ด |
|---|-------|-------|----------------|
| 35 | Dataset Management | 🟡 | `data/` + `tests/fixtures/` |
| 36 | Model Versioning | 🟡 | `ProcessingJob.code_version` |
| 37 | Data Versioning | 🟡 | `Params.config_hash()` · `ProcessingJob.config_hash` |
| 38 | Authentication | ⬜ | ยังไม่มีผู้ใช้หลายคน |
| 39 | Processing Queue | ✅ | `video_processing_jobs` + `JobRepo.claim_next()` (SKIP LOCKED) |
| 40 | API | 🟡 | `apps/api/` — ครอบคลุมเฉพาะ System 01 |
| 41 | Database | 🟡 | `rov/store/` — ตารางของ System 01 |
| 42 | Analytics Dashboard | ⬜ | |
| 43 | Replay / Event Review | ⬜ | |
| 44 | Testing / Evaluation | ✅ | `rov/eval/` + `tests/` |

**สรุป: ✅ 13 · 🟡 13 · ⬜ 19**

อัปเดต 2026-09-06 รอบสาม — เพิ่ม Draft Simulator, Pick/Ban Engine, Recommendation

---

## 3. โครงสร้างโฟลเดอร์ — เหตุผลที่ไม่ทำตาม §5 ตรง ๆ

Blueprint §5 เสนอ `frontend/ backend/ cv/ knowledge/`
โครงในเครื่องใช้ `packages/core/rov/ + apps/`

**เหตุผล:** การแยก `cv/` ออกจาก `backend/` ทำให้ tracking มีปัญหา
เพราะ tracking ต้องใช้ทั้งสถานะจาก HUD (ฝั่ง backend) และ detection (ฝั่ง cv)
ในฟังก์ชันเดียวกัน จะเกิด import ไขว้ไปมาและทดสอบ CV แยกไม่ได้

โครงปัจจุบันให้ `packages/core/rov` เป็นก้อนเดียวที่ **ไม่มี dependency
ไปยัง web หรือ HTTP เลย** จึงรันจาก CLI บนเครื่องเปล่าได้ทันที
และ `apps/api` เป็นเปลือกบางตามที่ Blueprint §56 ต้องการ

### ตารางเทียบ

| Blueprint §5 | ในเครื่อง |
|--------------|-----------|
| `backend/api/` | `apps/api/` |
| `backend/services/video/` | `rov/ingest/` |
| `backend/services/broadcast/` | `rov/broadcast/` |
| `backend/services/vision/` | `rov/minimap/` |
| `backend/services/tracking/` | `rov/tracking/` |
| `backend/services/events/` | `rov/events/` |
| `backend/services/macro/` | `rov/macro/` |
| `backend/services/draft/` | `rov/draft/` |
| `backend/services/scouting/` | `rov/scouting/` (ยังไม่มี) |
| `backend/models/` + `repositories/` + `database/` | `rov/store/` |
| `cv/` | `rov/minimap/` + `rov/eval/` + `data/` |
| `knowledge/` | `knowledge/` (เหมือนกัน) |
| `frontend/` | `apps/web/` (ยังไม่มี) |
| `data/` | `data/` (เหมือนกัน) |

ถ้าต้องการย้ายไปตาม §5 จริง ๆ ทำได้ แต่ควรทำหลัง Milestone 3
เพราะการย้ายตอนนี้จะทำให้ import พังทั้งหมดโดยไม่ได้ประโยชน์อะไร

---

## 4. Data Layer 4 → 5

Blueprint §54 แทรก ANALYTICS เข้ามา

```
L1 RAW VIDEO      video.mp4, frames.parquet
L2 OBSERVATION    detections, hud, tracks, observations.parquet
L3 EVENT          events.parquet
L4 ANALYTICS      สถิติที่รวมแล้ว เช่น "dragon first rotation 68%"
L5 INSIGHT        ข้อสรุป เช่น "objective-oriented jungler"
```

เหตุผลที่ต้องแยก L4 กับ L5: ตัวเลข 68% ตรวจสอบย้อนกลับไปหา event ได้
แต่คำว่า "objective-oriented" เป็นการตีความที่ต้องมีเกณฑ์กำกับ
ถ้ารวมเป็นชั้นเดียวจะแยกไม่ออกว่าอันไหนวัดได้ อันไหนตีความ

อยู่ในโค้ดที่ `rov/domain/enums.py::DataLayer`

---

## 5. Event 13 ชนิด

Blueprint §16 เพิ่มจากแผนเดิม 2 ชนิด

| Event | ที่มา |
|-------|-------|
| ROTATION, GROUPING, GANK | แผนเดิม |
| OBJECTIVE_SETUP | แผนเดิม |
| **OBJECTIVE_CONTEST** | ใหม่ |
| **OBJECTIVE_TAKEN** | เพิ่มจากการค้นพบว่า minimap บอกสถานะด้วยสี |
| **OBJECTIVE_LOST** | ใหม่ |
| TEAMFIGHT, DEATH, RESPAWN, RECALL | แผนเดิม |
| LANE_SWAP, SPLIT_PUSH | แผนเดิม |

ครบทั้ง 13 ใน `rov/domain/enums.py::EventType`

---

## 6. ข้อเท็จจริงใหม่ที่ได้จากข้อมูลจริง

ยืนยันจากการดึง `RoV Pro League/2026/Summer` จริง

| ข้อ | ค่า | ที่มา |
|-----|-----|-------|
| แบนต่อทีมต่อเกม | **4 ตัว** (รวม 8) | ช่อง `t1b1`–`t1b4` |
| เลือกต่อทีมต่อเกม | **5 ตัว** | ช่อง `t1h1`–`t1h5` |
| ฝั่ง blue/red | **สลับได้ทุกเกมในซีรีส์** | `team1side` ต่อ map |
| ความยาวเกม | มีให้ | `length=11:58` |
| Global Ban-Pick | **ยืนยันแล้ว** 270 จาก 272 เกมเป็นไปตามกติกา | ตรวจอัตโนมัติใน parser |
| ฮีโร่ที่พบใน pro | **96 ตัว** | หลังรวมชื่อที่สะกดต่างกันเข้าด้วยกัน (ก่อนแก้บั๊กนับได้ 98) |

**สิ่งที่ Liquipedia ไม่มี:** ลำดับการสลับกันแบนระหว่างสองทีม
เก็บเป็นช่องของแต่ละทีมเท่านั้น จึงสร้าง `turn_order` ที่แท้จริงไม่ได้
ต้องถือว่าลำดับภายในทีมถูก แต่การสลับระหว่างทีมเป็นการประมาณ

**ต้นทุนการดึงถูกกว่าที่ประเมินไว้มาก** หนึ่งหน้า Group Stage
ให้ 272 เกม จึงไม่ต้องยิงทีละแมตช์ตามที่กังวลไว้ใน
[08-game-reference.md](08-game-reference.md) §8
