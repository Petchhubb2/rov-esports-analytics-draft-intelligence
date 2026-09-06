# 02 — สถาปัตยกรรมและโครงสร้างโปรเจกต์

## 1. หลักการออกแบบ 6 ข้อ

หลักการเหล่านี้ใช้ตัดสินข้อถกเถียงทุกข้อในโปรเจกต์

**P1 · ตรรกะทั้งหมดอยู่ใน Python package เดียวที่ import ได้**
API, worker และ CLI เป็นเพียงเปลือกบาง ๆ ที่เรียก package นี้
เหตุผล: งาน CV ต้องรันซ้ำได้จาก command line โดยไม่ต้องเปิด server และ Phase 1
ต้องไม่มี web stack เข้ามาเกี่ยวเลย

**P2 · แต่ละ stage เขียนไฟล์ artifact ของตัวเอง**
`detections.parquet` → `tracks.parquet` → `observations.parquet` → `events.parquet`
เหตุผล: รัน stage ใดใหม่ก็ได้โดยไม่ต้องถอดวิดีโอซ้ำ ซึ่งเป็นขั้นที่แพงที่สุด
นี่คือรูปธรรมของหลัก "ห้ามเขียนทับ Layer ล่าง" ใน §79 ของแผนเดิม

**P3 · Deterministic และ versioned**
ทุก artifact บันทึกเวอร์ชันของอัลกอริทึมและ config hash ที่ใช้สร้าง
input เดิม + config เดิม ต้องได้ output เดิมเสมอ

**P4 · Config อยู่ในไฟล์ ไม่อยู่ในโค้ด**
ROI, threshold, zone polygon, น้ำหนักคะแนน อยู่ใน YAML ทั้งหมด
เหตุผล: broadcast แต่ละรายการมี layout ต่างกัน และการปรับจูนต้องไม่ต้องแก้โค้ด

**P5 · วัดก่อนปรับ**
ทุก stage ที่มี threshold ต้องมีคำสั่ง `rov eval <stage>` คู่กันเสมอ
ห้าม merge การปรับ threshold ที่ไม่มีตัวเลขก่อน/หลัง

**P6 · แยก Observed จาก Inferred ในระดับสคีมา ไม่ใช่แค่ระดับความตั้งใจ**
ทุกแถวของ observation มีฟิลด์ `source` และ `visible` และ query
ที่ใช้ทำสถิติต้องกรองอย่างชัดแจ้ง ไม่มีค่า default ที่กลืนสองอย่างเข้าด้วยกัน

---

## 2. โครงสร้างโปรเจกต์

```text
rov-analytics/
│
├── packages/core/                     ← ตรรกะทั้งหมดอยู่ที่นี่ (P1)
│   ├── pyproject.toml
│   └── rov/
│       ├── domain/                    Layer-neutral types
│       │   ├── types.py               Detection, Track, Observation, Event, Slot
│       │   ├── geometry.py            Point, Polygon, normalize, distance
│       │   └── enums.py               Team, Source, EventType, FrameState
│       │
│       ├── config/
│       │   ├── layout.py              โหลด+ตรวจ configs/layouts/*.yaml
│       │   ├── zones.py               โหลด polygon + สร้าง raster lookup
│       │   └── params.py              threshold ทั้งหมดของ pipeline
│       │
│       ├── ingest/
│       │   ├── probe.py               ffprobe: width/height/fps/duration/codec
│       │   ├── sampler.py             สุ่มเฟรมตาม PTS ไม่ใช่ index
│       │   └── segmenter.py           แบ่งไฟล์เป็นหลาย game (BO3/BO5)
│       │
│       ├── broadcast/                 อ่านทุกอย่างที่ไม่ใช่ minimap
│       │   ├── roi.py                 crop ตาม layout config
│       │   ├── clock.py               OCR นาฬิกาเกม → game_clock (G2)
│       │   ├── state.py               LIVE/REPLAY/PAUSE/DRAFT (G3)
│       │   ├── hud.py                 slot 1-10: hero, level, alive, hp (G4)
│       │   └── scoreboard.py          kill score, gold, objective timer
│       │
│       ├── minimap/                   ← หัวใจของระบบ
│       │   ├── calibrate.py           หา ROI + สร้าง transform pixel→normalized
│       │   ├── background.py          rolling median background model (G5)
│       │   ├── detect.py              blob → candidate icon
│       │   ├── appearance.py          สกัด embedding จาก icon patch
│       │   ├── objective_state.py     อ่านสี mark: dragon/slayer ALIVE|DEAD
│       │   └── templates.py           สร้าง template จาก HUD portrait
│       │
│       ├── tracking/
│       │   ├── kalman.py              constant-velocity filter ต่อผู้เล่น
│       │   ├── assign.py              Hungarian + cost function (G6)
│       │   ├── states.py              ALIVE/DEAD/RECALL/UNKNOWN state machine
│       │   └── tracker.py             วนรวมทั้งหมด
│       │
│       ├── mapping/
│       │   ├── zones.py               (x,y) → zone id ด้วย raster lookup
│       │   ├── hysteresis.py          กัน zone กระพริบที่ขอบ
│       │   └── heatmap.py             สะสม density grid
│       │
│       ├── events/                    Layer 3
│       │   ├── base.py                interface: detect(obs) -> [Event]
│       │   ├── rotation.py
│       │   ├── grouping.py
│       │   ├── objective_setup.py
│       │   ├── gank.py
│       │   ├── teamfight.py
│       │   └── recall.py
│       │
│       ├── macro/                     Layer 4
│       │   ├── metrics.py             metric ดิบต่อผู้เล่น/ทีม
│       │   ├── player_profile.py
│       │   ├── team_profile.py
│       │   └── scoring.py             macro score (สรุป ไม่ใช่ข้อมูลต้นฉบับ)
│       │
│       ├── draft/                     แยกจาก vision โดยสิ้นเชิง
│       │   ├── heroes.py              โหลด hero attribute
│       │   ├── importer/              ดึงข้อมูลจากภายนอก
│       │   │   ├── liquipedia.py      client + rate limiter (60/ชม.)
│       │   │   ├── cache.py           cache response ลงดิสก์ ห้ามยิงซ้ำ
│       │   │   └── mapping.py         ชื่อฮีโร่ Liquipedia → hero_id
│       │   ├── state.py               ลำดับ ban/pick + Global Ban-Pick
│       │   ├── composition.py         Draft v1 — จาก attribute ล้วน (G7)
│       │   ├── matchup.py             Draft v2 — empirical + shrinkage (G8)
│       │   ├── synergy.py
│       │   ├── score.py               รวมคะแนนตามน้ำหนัก
│       │   └── recommend.py           จัดอันดับ pick/ban + เหตุผลเชิงตัวเลข
│       │
│       ├── store/
│       │   ├── artifacts.py           อ่าน/เขียน parquet ต่อ stage (P2)
│       │   ├── repo.py                repository ต่อ entity
│       │   ├── models.py              SQLAlchemy models
│       │   └── migrations/            alembic
│       │
│       ├── eval/                      (P5)
│       │   ├── groundtruth.py         โหลด label
│       │   ├── detection.py           precision / recall / F1 / MAE
│       │   ├── tracking.py            IDF1 / MOTA / ID switch
│       │   ├── events.py              precision / recall ต่อ event type
│       │   └── calibration.py         reliability diagram (G10)
│       │
│       ├── pipeline/
│       │   ├── stages.py              นิยาม stage + dependency
│       │   └── runner.py              รัน DAG, ข้าม stage ที่ cache ตรง
│       │
│       └── cli/
│           └── main.py                typer: rov <verb>
│
├── apps/
│   ├── api/                           FastAPI — บาง
│   │   ├── main.py
│   │   ├── routers/                   matches, players, teams, draft, jobs
│   │   └── schemas/                   pydantic request/response
│   │
│   ├── worker/
│   │   └── main.py                    poll ตาราง jobs → เรียก pipeline.runner
│   │
│   ├── web/                           Next.js — เริ่มหลัง Milestone 3
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   │
│   └── annotator/                     เครื่องมือ label (§22)
│       └── ...                        Streamlit หรือหน้า HTML เดียว
│
├── configs/
│   ├── layouts/
│   │   ├── _schema.yaml
│   │   └── rov_pro_league_720p.yaml   ผลลัพธ์ของ Phase 0
│   ├── zones/
│   │   └── rov_map_v1.yaml            polygon ในพิกัด normalized
│   ├── params/
│   │   ├── detect.yaml
│   │   ├── track.yaml
│   │   ├── events.yaml
│   │   └── objectives.yaml            เวลาเกิด dragon/slayer (วัดเอง)
│   └── draft/
│       ├── heroes.yaml                hero attribute (กรอกมือ 126 ตัว)
│       ├── format.yaml                ลำดับ ban/pick + Global Ban-Pick
│       └── weights.yaml               น้ำหนักคะแนน (§37)
│
├── data/                              gitignored ทั้งหมด
│   ├── videos/                        ไฟล์ต้นฉบับ
│   ├── artifacts/<match_id>/          ผลแต่ละ stage
│   ├── groundtruth/<match_id>/        label จากมนุษย์
│   └── exports/
│
├── tests/
│   ├── unit/
│   ├── fixtures/                      เฟรมตัวอย่างที่ commit ได้ (เล็ก)
│   └── integration/
│
├── docs/                              ← เอกสารชุดนี้
├── scripts/
├── docker-compose.yml                 postgres + api + worker
└── Makefile
```

### ทำไมถึงแยกแบบนี้

โครงสร้างใน §59 ของแผนเดิมแยก `backend/` กับ `cv/` ออกจากกัน
ปัญหาคือ tracking ต้องใช้ทั้งข้อมูล HUD (ฝั่ง backend) และ detection (ฝั่ง cv)
การแยกแบบนั้นจะทำให้เกิด import ไขว้ไปมาและทดสอบ CV แยกไม่ได้

โครงสร้างนี้ให้ `packages/core` เป็นก้อนเดียวที่ไม่มี dependency ไปยัง web หรือ HTTP เลย
จึงรันบนเครื่องเปล่าได้ทันทีด้วยคำสั่งเดียว

---

## 3. Command Line Interface

CLI คือหน้าตาหลักของระบบตลอด Phase 0–4 ไม่ใช่ web

```bash
# Phase 0
rov probe            video.mp4
rov calibrate        video.mp4 --out configs/layouts/pro_720p.yaml
rov layout-check     video.mp4 --layout pro_720p     # วาดกรอบ ROI ทับเฟรม

# Phase 1
rov sample           M001 --fps 2
rov background       M001
rov detect           M001 --overlay          # เขียน detections.parquet + วิดีโอ overlay
rov eval detect      M001

# Phase 2-3
rov hud              M001
rov track            M001 --overlay
rov eval track       M001

# Phase 4-5
rov zones            M001
rov events           M001
rov eval events      M001
rov profile          --player P07

# Draft (ทำขนานได้ ไม่ต้องรอ vision)
rov draft import     --league rpl --from 2024 --resume   # เคารพ rate limit
rov draft simulate   --blue A,B,C --red D,E,F --bans ...
rov draft recommend  --state draft.json --series-game 2/5

# ทั้งหมด
rov run              M001 --from sample --to events
```

`rov run --from X --to Y` คือรูปธรรมของ P2 — รันเฉพาะช่วง stage ที่ต้องการ

---

## 4. การตัดสินใจด้าน Technology

| หัวข้อ | เลือก | เหตุผล | ทางเลือกที่ปฏิเสธ |
|--------|-------|--------|-------------------|
| ภาษาแกน | Python 3.11+ | OpenCV / NumPy / SciPy / scikit-learn อยู่ที่นี่หมด | ตรงตามแผนเดิม |
| อ่านวิดีโอ | PyAV (libav binding) | เข้าถึง PTS จริง จำเป็นสำหรับ G2 · seek แม่นกว่า | `cv2.VideoCapture` เดา timestamp จาก index ซึ่งเพี้ยนกับ VFR |
| CV | OpenCV + NumPy | เพียงพอต่อ Milestone 1–3 | YOLO — ยังไม่มีหลักฐานว่าจำเป็น |
| Assignment | `scipy.optimize.linear_sum_assignment` | Hungarian พร้อมใช้ ไม่ต้องเขียนเอง | เขียนเอง / greedy nearest |
| OCR | Tesseract (`pytesseract`) + preprocessing | นาฬิกาเป็นตัวเลขฟอนต์คงที่ ทำ template digit matching เองก็ได้ถ้า OCR แย่ | EasyOCR — หนักเกินสำหรับตัวเลข 5 ตัว |
| Artifact | Parquet + `pyarrow` | ตาราง typed, บีบอัดดี, อ่านด้วย pandas/polars ได้ทันที | CSV — ไม่มี type และไฟล์ใหญ่ · JSON — ช้าตอนอ่านหลักแสนแถว |
| DataFrame | Polars (fallback pandas) | เร็วกว่ามากกับ position หลักล้านแถว และ API ชัดกว่า | pandas ล้วน |
| ฐานข้อมูล | PostgreSQL 16 (local docker) | ตรงตามแผนเดิม · partition ตาม match ได้ | SQLite — เขียนพร้อมกันจาก worker ไม่ดี |
| ORM/migration | SQLAlchemy 2.0 + Alembic | มาตรฐาน | SQL ดิบ — migration จะรวน |
| Queue | ตาราง `jobs` + worker poll | หนึ่ง dependency น้อยลง เพียงพอสำหรับเครื่องเดียว | Celery/Redis — เลื่อนไปจนมีหลาย worker |
| API | FastAPI | ตรงตามแผนเดิม · pydantic ใช้ร่วมกับ core ได้ | — |
| CLI | Typer | ประกาศ command จาก type hint | argparse |
| Frontend | Next.js + TypeScript + Tailwind | ตรงตามแผนเดิม | — |
| Charts | Recharts + canvas สำหรับ heatmap | heatmap 128×128 ต้องใช้ canvas ไม่ใช่ SVG | D3 ล้วน — เกินจำเป็น |
| Config | YAML + pydantic validation | อ่านง่าย แก้ด้วยมือได้ และ validate ตอนโหลด | JSON — ไม่มี comment |
| ทดสอบ | pytest + fixture เฟรมจริง | CV ต้องทดสอบกับภาพจริง ไม่ใช่ mock | — |

---

## 5. Runtime Topology

**ระหว่างพัฒนา (Phase 0–4)** — ไม่มี server เลย

```
นักพัฒนา → rov CLI → data/artifacts/ → เปิดดูวิดีโอ overlay + parquet
```

**ตอนมี dashboard (Phase 5+)**

```
                 ┌──────────────┐
   Browser ─────▶│  Next.js     │
                 └──────┬───────┘
                        │ REST
                 ┌──────▼───────┐        ┌──────────────┐
                 │  FastAPI     │───────▶│  PostgreSQL  │
                 │  (บาง)       │        └──────▲───────┘
                 └──────┬───────┘               │
                        │ INSERT job            │
                 ┌──────▼───────┐               │
                 │  jobs table  │               │
                 └──────┬───────┘               │
                        │ poll                  │
                 ┌──────▼───────┐               │
                 │  Worker      │───────────────┘
                 │  rov.pipeline│
                 └──────┬───────┘
                        │
                 ┌──────▼───────────────┐
                 │ data/artifacts/<id>/ │
                 └──────────────────────┘
```

API ห้ามประมวลผลวิดีโอเองเด็ดขาด (ตรงตาม §58) หน้าที่ของ API คือ
สร้าง job, รายงานสถานะ, และอ่านผลลัพธ์เท่านั้น

### Job model

```
UPLOADED → QUEUED → RUNNING → COMPLETED
                        │
                        └──▶ FAILED (เก็บ stage ที่พัง + traceback)
```

ฟิลด์ `stage` และ `progress` ให้ frontend polling ทุก 2 วินาที
job หนึ่งอันเก็บเป็นรายการของ stage ที่ต้องรัน ทำให้ resume จากจุดที่พังได้

---

## 6. ประมาณการทรัพยากร

สมมติแมตช์ยาว 20 นาที ที่ 720p 60fps

| รายการ | ค่า | หมายเหตุ |
|--------|-----|----------|
| เฟรมทั้งหมด | 72,000 | ไม่ประมวลผลทุกเฟรม |
| อัตราสุ่มสำหรับ detect | 5 fps → 6,000 เฟรม | เพียงพอต่อ tracking |
| อัตราบันทึก observation | 2 Hz → 2,400 sample | ×10 ผู้เล่น = 24,000 แถว/แมตช์ |
| position rows ที่ 500 แมตช์ | ~12 ล้านแถว | Postgres รับไหวสบายถ้ามี index ถูก |
| ขนาด detections.parquet | ~2–5 MB/แมตช์ | |
| เวลา decode + crop | ~2–4 นาที/แมตช์ | คอขวดอยู่ที่ decode |
| เวลา detect+track | ~1–3 นาที/แมตช์ | ขึ้นกับ threshold |

ข้อสรุป: **ไม่จำเป็นต้องใช้ time-series database** Postgres ธรรมดาพอ
และไม่ต้องใช้ GPU สำหรับ Milestone 1–4

---

## 7. Threading model ของ worker

Decode วิดีโอเป็นงาน I/O + CPU ผสม
ใช้รูปแบบ producer/consumer หนึ่ง process ต่อหนึ่งแมตช์

```
[PyAV decode thread] → queue เฟรม → [worker pool: crop + detect] → รวมผลตาม PTS
```

อย่ารัน multiprocessing ข้ามแมตช์บนเครื่องเดียวในช่วงแรก
เพราะ memory จาก background model และ frame buffer จะบวมเร็ว
ขนานระดับแมตช์เมื่อย้ายขึ้น server จริงเท่านั้น
