# 03 — Data Contracts และ Schema

เอกสารนี้แปลงหลัก "4 Layer" ใน §79 ของแผนเดิมให้เป็นสคีมาที่บังคับใช้ได้จริง

## 1. แผนที่ Layer → Artifact

```text
LAYER 1  RAW           video.mp4 + frames.parquet
   │                   ห้ามแก้ไข ห้ามลบ
   ▼
LAYER 2  OBSERVATION   detections → hud → tracks → observations.parquet
   │                   สิ่งที่ "เห็น" เท่านั้น มี source/visible/confidence ทุกแถว
   ▼
LAYER 3  EVENT         events.parquet
   │                   สิ่งที่ "ตีความ" จาก Layer 2 สร้างใหม่ได้เสมอ
   ▼
LAYER 4  INSIGHT       profiles.json, scores.json
                       สรุปเชิงสถิติ สร้างใหม่ได้เสมอ
```

กฎเหล็ก 3 ข้อ

1. Layer สูงกว่าห้ามเขียนกลับลง Layer ต่ำกว่า
2. ลบ Layer 3 และ 4 ทิ้งทั้งหมดแล้วสร้างใหม่จาก Layer 2 ได้เสมอ
3. Layer 2 สร้างใหม่จาก Layer 1 ได้เสมอ (แต่แพง จึง cache)

---

## 2. Artifact ต่อ Stage

โครงไดเรกทอรีต่อแมตช์

```text
data/artifacts/M001/
├── manifest.json           stage ไหนรันแล้ว ด้วย config hash อะไร
├── meta.json               ผลจาก ffprobe
├── background.png          median background ของ minimap
├── frames.parquet          L1
├── detections.parquet      L2
├── hud.parquet             L2
├── tracks.parquet          L2
├── observations.parquet    L2  ← ตารางหลักที่ทุกอย่างต่อยอด
├── events.parquet          L3
├── profiles.json           L4
└── overlay/
    ├── detect.mp4
    └── track.mp4
```

### manifest.json

ทำให้ P3 (deterministic) บังคับใช้ได้

```json
{
  "match_id": "M001",
  "stages": {
    "sample":   { "at": "2026-09-06T10:00:00Z", "code_version": "0.3.1",
                  "config_hash": "a1b2c3", "rows": 6000 },
    "detect":   { "at": "2026-09-06T10:04:12Z", "code_version": "0.3.1",
                  "config_hash": "d4e5f6", "rows": 58211 }
  }
}
```

runner เทียบ `config_hash` ปัจจุบันกับใน manifest
ถ้าตรงและ artifact มีอยู่ → ข้าม stage นั้น
ถ้าไม่ตรง → รันใหม่ และ **invalidate ทุก stage ที่อยู่ถัดไป**

---

### frames.parquet — Layer 1

หนึ่งแถวต่อหนึ่งเฟรมที่สุ่มมา

| คอลัมน์ | ชนิด | คำอธิบาย |
|---------|------|----------|
| `frame_idx` | int32 | ลำดับเฟรมในไฟล์ |
| `pts` | float64 | presentation timestamp (วินาที) จาก container |
| `video_time` | float64 | วินาทีนับจากต้นไฟล์ |
| `game_id` | string? | รหัสเกมย่อยใน BO3/BO5 · null ถ้ายังไม่ระบุ |
| `game_clock` | float64? | วินาทีในเกมจาก OCR · null ถ้าอ่านไม่ได้ (G2) |
| `clock_conf` | float32 | ความมั่นใจของ OCR |
| `frame_state` | enum | LIVE / REPLAY / PAUSE / DRAFT / NON_GAME (G3) |
| `state_reason` | string | เหตุผลที่จัดเป็น state นั้น ใช้ debug |
| `minimap_ok` | bool | ตรวจพบกรอบ minimap ที่ตำแหน่งคาดหวังหรือไม่ |
| `dragon_state` | enum? | ALIVE / DEAD จากสี mark บน minimap |
| `slayer_state` | enum? | ALIVE / DEAD จากสี mark บน minimap |
| `obj_state_conf` | float32 | ความมั่นใจของการอ่านสี |

**สัญญา:** stage ถัดไปประมวลผลเฉพาะแถวที่ `frame_state == LIVE AND minimap_ok`

สถานะ objective เก็บที่ระดับเฟรมเพราะเป็นคุณสมบัติของภาพ ไม่ใช่ของผู้เล่น
detector ของ `OBJECTIVE_TAKEN` อ่านคอลัมน์นี้ตรง ๆ โดยไม่ต้องพึ่ง event อื่น

---

### detections.parquet — Layer 2

หนึ่งแถวต่อหนึ่ง blob ที่ตรวจพบ ยังไม่รู้ว่าเป็นใคร

| คอลัมน์ | ชนิด | คำอธิบาย |
|---------|------|----------|
| `frame_idx` | int32 | เชื่อมกับ frames |
| `det_id` | int32 | ลำดับใน frame นั้น |
| `px`, `py` | float32 | จุดศูนย์กลางในพิกัด pixel ของ minimap crop |
| `x`, `y` | float32 | พิกัด normalized 0..1 หลังผ่าน transform |
| `radius` | float32 | รัศมีโดยประมาณ |
| `area` | float32 | พื้นที่ contour |
| `circularity` | float32 | 4πA/P² — ใช้กรอง minion และ marker |
| `team_hint` | enum | BLUE / RED / UNKNOWN จากสีวงแหวน |
| `team_conf` | float32 | |
| `patch_ref` | string | คีย์อ้างถึง icon patch ที่เก็บไว้ ใช้ทำ appearance |
| `det_conf` | float32 | คะแนนรวมของ detector |

**หมายเหตุ:** ที่นี่ยังไม่มี `hero_id` และ `player_id` โดยเจตนา
การผูก identity เป็นหน้าที่ของ stage ถัดไปเท่านั้น

---

### hud.parquet — Layer 2

หนึ่งแถวต่อ (เฟรม × slot) โดย slot 0–4 คือทีมน้ำเงิน 5–9 คือทีมแดง

| คอลัมน์ | ชนิด | คำอธิบาย |
|---------|------|----------|
| `frame_idx` | int32 | |
| `slot` | int8 | 0–9 |
| `alive` | bool? | จาก portrait เทา/ปกติ (G4) |
| `respawn_in` | float32? | วินาทีที่เหลือ ถ้าอ่านได้ |
| `level` | int8? | |
| `hp_frac` | float32? | สัดส่วนหลอดเลือด |
| `mana_frac` | float32? | |
| `ult_ready` | bool? | |
| `conf` | float32 | |

**สัญญา:** การจับคู่ slot → player_id → hero_id คงที่ตลอดเกม
กำหนดครั้งเดียวตอนต้นเกมจาก draft หรือจากการยืนยันด้วยมือ

---

### tracks.parquet — Layer 2

ผลของ assignment หนึ่งแถวต่อ (เฟรม × slot)

| คอลัมน์ | ชนิด | คำอธิบาย |
|---------|------|----------|
| `frame_idx` | int32 | |
| `slot` | int8 | |
| `det_id` | int32? | detection ที่ถูกจับคู่ · null ถ้าไม่มี |
| `x`, `y` | float32? | ตำแหน่งหลัง Kalman |
| `vx`, `vy` | float32 | ความเร็วประมาณการ |
| `track_state` | enum | OBSERVED / COASTING / DEAD / UNKNOWN |
| `age_since_obs` | float32 | วินาทีนับจากครั้งสุดท้ายที่เห็นจริง |
| `assign_cost` | float32 | ต้นทุนที่ Hungarian เลือก ใช้ debug |
| `conf` | float32 | |

`track_state` แยกให้ชัด

| ค่า | ความหมาย |
|-----|----------|
| `OBSERVED` | เฟรมนี้เห็น icon จริง ตำแหน่งเชื่อถือได้ |
| `COASTING` | ไม่เห็น แต่ Kalman ยังทำนายอยู่ (ไม่เกิน N วินาที) |
| `DEAD` | HUD ยืนยันว่าตาย ไม่มีตำแหน่ง |
| `UNKNOWN` | ไม่เห็นและเกินเวลาที่จะเดา ตำแหน่งเป็น null |

---

### observations.parquet — Layer 2 · ตารางหลัก

นี่คือตารางที่ §17 ของแผนเดิมอธิบายไว้ เพิ่มฟิลด์ที่จำเป็นเข้าไป
ทุกอย่างใน Layer 3 และ 4 ต่อยอดจากตารางนี้ตารางเดียว

| คอลัมน์ | ชนิด | คำอธิบาย |
|---------|------|----------|
| `match_id` | string | |
| `game_id` | string | |
| `game_clock` | float32 | **แกนเวลาหลักสำหรับวิเคราะห์** |
| `video_time` | float32 | สำหรับกระโดดดูวิดีโอ |
| `player_id` | string | |
| `hero_id` | string | |
| `team_id` | string | |
| `slot` | int8 | |
| `x`, `y` | float32? | normalized 0..1 · null เมื่อ UNKNOWN/DEAD |
| `zone` | string? | ผลจาก zone lookup |
| `visible` | bool | เห็นบน minimap จริงในเฟรมนี้หรือไม่ |
| `alive` | bool | จาก HUD |
| `source` | enum | DETECTION / TRACKING / HUD / MANUAL |
| `confidence` | float32 | |

**กฎการใช้งานที่ต้องบังคับในโค้ด**

```python
# ถูก — สถิติที่อ้างตำแหน่งจริง
obs.filter(source == "DETECTION", visible == True)

# ถูก — เส้นทางการเดินที่ยอมให้มีการเติมช่วงสั้น ๆ
obs.filter(source.is_in(["DETECTION", "TRACKING"]), x.is_not_null())

# ผิด — ห้ามทำ
obs.filter(x.is_not_null())   # ปนค่าเดากับค่าจริงโดยไม่รู้ตัว
```

ทุกฟังก์ชันใน `rov.macro` ต้องรับพารามิเตอร์ `min_source` อย่างชัดแจ้ง
และคืน `coverage` (สัดส่วนเวลาที่ observed จริง) กลับมาพร้อมผลลัพธ์เสมอ

---

### events.parquet — Layer 3

| คอลัมน์ | ชนิด | คำอธิบาย |
|---------|------|----------|
| `event_id` | string | uuid |
| `match_id`, `game_id` | string | |
| `event_type` | enum | ROTATION / GANK / GROUPING / OBJECTIVE_SETUP / **OBJECTIVE_TAKEN** / TEAMFIGHT / DEATH / RECALL / SPLIT_PUSH / LANE_SWAP |
| `start_clock`, `end_clock` | float32 | |
| `team_id` | string? | |
| `player_ids` | list[string] | |
| `zone_from`, `zone_to` | string? | |
| `confidence` | float32 | |
| `coverage` | float32 | สัดส่วนของช่วงเวลาที่มีข้อมูล observed |
| `detector_version` | string | |
| `evidence` | json | ตัวเลขดิบที่ทำให้เกิด event นี้ |

ฟิลด์ `evidence` สำคัญมาก มันคือคำตอบของ §41 ที่บอกว่า
"ควรแสดงเหตุผลในรูปของ Metrics ไม่ใช่เพียงข้อความ AI"

ตัวอย่างสำหรับ OBJECTIVE_SETUP

```json
{
  "players_in_zone": 3,
  "zone": "DRAGON_PIT_APPROACH",
  "mean_pairwise_dist": 0.061,
  "seconds_before_spawn": 14.2,
  "arrival_order": ["P03", "P05", "P02"],
  "coverage": 1.0
}
```

---

## 3. PostgreSQL Schema

DDL ย่อของตารางหลัก ตามรายการใน §43 แต่ปรับให้ตรงกับสิ่งที่ pipeline ผลิตจริง

### Reference

```sql
CREATE TABLE patches (
  id          SERIAL PRIMARY KEY,
  version     TEXT NOT NULL UNIQUE,
  released_at DATE NOT NULL
);

CREATE TABLE heroes (
  id         TEXT PRIMARY KEY,            -- slug: 'nakroth'
  name_en    TEXT NOT NULL,
  name_th    TEXT,
  -- แยกสองแนวคิดให้ชัด: class ตามเกม กับ เลนที่เล่นจริง
  hero_class TEXT[] NOT NULL,             -- marksman|mage|assassin|tank|warrior|support
  lane_roles TEXT[] NOT NULL,             -- ds|jungle|mid|dragon|support
  attrs      JSONB NOT NULL               -- ดู 06-draft-engine.md
);
-- ปัจจุบันมี 126 ฮีโร่ · 98 ตัวมีข้อมูลระดับ pro

CREATE TABLE teams   (id TEXT PRIMARY KEY, name TEXT NOT NULL, tag TEXT);
CREATE TABLE players (
  id      TEXT PRIMARY KEY,
  ign     TEXT NOT NULL,
  team_id TEXT REFERENCES teams(id),
  role    TEXT
);
```

### Match

```sql
CREATE TABLE matches (
  id            TEXT PRIMARY KEY,
  tournament_id TEXT,
  patch_id      INT REFERENCES patches(id),
  played_at     DATE,
  blue_team_id  TEXT REFERENCES teams(id),
  red_team_id   TEXT REFERENCES teams(id),
  winner_team_id TEXT REFERENCES teams(id),
  layout_id     TEXT NOT NULL,            -- configs/layouts/<id>.yaml
  status        TEXT NOT NULL
);

-- ผูก slot ใน HUD เข้ากับผู้เล่นและฮีโร่ คงที่ทั้งเกม
CREATE TABLE match_players (
  match_id  TEXT REFERENCES matches(id) ON DELETE CASCADE,
  slot      SMALLINT CHECK (slot BETWEEN 0 AND 9),
  player_id TEXT REFERENCES players(id),
  hero_id   TEXT REFERENCES heroes(id),
  team_id   TEXT REFERENCES teams(id),
  role      TEXT,
  PRIMARY KEY (match_id, slot)
);

CREATE TABLE match_draft (
  match_id   TEXT REFERENCES matches(id) ON DELETE CASCADE,
  turn_order SMALLINT,
  phase      SMALLINT,                    -- 1 หรือ 2
  team_id    TEXT REFERENCES teams(id),
  action     TEXT CHECK (action IN ('BAN','PICK')),
  hero_id    TEXT REFERENCES heroes(id),
  PRIMARY KEY (match_id, turn_order)
);

-- ซีรีส์ จำเป็นสำหรับกติกา Global Ban-Pick (soft fearless)
-- ทีมห้ามใช้ฮีโร่ที่ "ตัวเอง" เคย pick ในเกมก่อนหน้าของซีรีส์เดียวกัน
CREATE TABLE series (
  id            TEXT PRIMARY KEY,
  tournament_id TEXT,
  best_of       SMALLINT NOT NULL,
  team_a_id     TEXT REFERENCES teams(id),
  team_b_id     TEXT REFERENCES teams(id)
);

ALTER TABLE matches
  ADD COLUMN series_id  TEXT REFERENCES series(id),
  ADD COLUMN game_index SMALLINT;         -- เกมที่เท่าไรในซีรีส์ เริ่มที่ 1
```

### Observation — ตารางใหญ่

```sql
CREATE TABLE player_positions (
  match_id   TEXT       NOT NULL,
  game_id    TEXT       NOT NULL,
  game_clock REAL       NOT NULL,
  slot       SMALLINT   NOT NULL,
  player_id  TEXT       NOT NULL,
  hero_id    TEXT       NOT NULL,
  team_id    TEXT       NOT NULL,
  x          REAL,
  y          REAL,
  zone       TEXT,
  visible    BOOLEAN    NOT NULL,
  alive      BOOLEAN    NOT NULL,
  source     TEXT       NOT NULL CHECK (source IN
                ('DETECTION','TRACKING','HUD','MANUAL')),
  confidence REAL       NOT NULL,
  PRIMARY KEY (match_id, game_id, game_clock, slot)
) PARTITION BY HASH (match_id);
-- สร้าง 16 partition ตอน migrate

CREATE INDEX ON player_positions (player_id, game_clock);
CREATE INDEX ON player_positions (match_id, zone);
CREATE INDEX ON player_positions (match_id, source) WHERE visible;
```

เหตุผลที่ partition: ที่ 500 แมตช์จะมีราว 12 ล้านแถว
การลบและประมวลผลใหม่ทั้งแมตช์เป็นการทำงานที่พบบ่อยที่สุด
partition ทำให้ `DROP` เร็วกว่า `DELETE` มาก

### Event

```sql
CREATE TABLE macro_events (
  id               UUID PRIMARY KEY,
  match_id         TEXT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  game_id          TEXT NOT NULL,
  event_type       TEXT NOT NULL,
  start_clock      REAL NOT NULL,
  end_clock        REAL NOT NULL,
  team_id          TEXT,
  player_ids       TEXT[] NOT NULL DEFAULT '{}',
  zone_from        TEXT,
  zone_to          TEXT,
  confidence       REAL NOT NULL,
  coverage         REAL NOT NULL,
  detector_version TEXT NOT NULL,
  evidence         JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX ON macro_events (match_id, start_clock);
CREATE INDEX ON macro_events (event_type, team_id);
```

### Draft statistics

```sql
CREATE TABLE hero_stats (
  hero_id   TEXT REFERENCES heroes(id),
  patch_id  INT  REFERENCES patches(id),
  games     INT  NOT NULL DEFAULT 0,
  wins      INT  NOT NULL DEFAULT 0,
  picks     INT  NOT NULL DEFAULT 0,
  bans      INT  NOT NULL DEFAULT 0,
  PRIMARY KEY (hero_id, patch_id)
);

CREATE TABLE hero_matchups (
  hero_id       TEXT REFERENCES heroes(id),
  enemy_hero_id TEXT REFERENCES heroes(id),
  patch_id      INT  REFERENCES patches(id),
  context       TEXT NOT NULL CHECK (context IN ('LANE','TEAM')),
  games         INT  NOT NULL DEFAULT 0,
  wins          INT  NOT NULL DEFAULT 0,
  PRIMARY KEY (hero_id, enemy_hero_id, patch_id, context)
);

CREATE TABLE hero_synergies (
  hero_a   TEXT REFERENCES heroes(id),
  hero_b   TEXT REFERENCES heroes(id),
  patch_id INT  REFERENCES patches(id),
  games    INT  NOT NULL DEFAULT 0,
  wins     INT  NOT NULL DEFAULT 0,
  PRIMARY KEY (hero_a, hero_b, patch_id),
  CHECK (hero_a < hero_b)                 -- บังคับให้เก็บทิศทางเดียว
);
```

จุดสำคัญ: **เก็บ `games` และ `wins` ดิบ ห้ามเก็บ `win_rate` เป็นคอลัมน์**
เพราะ win_rate ต้องคำนวณพร้อม shrinkage เสมอ (G8) ถ้าเก็บไว้จะมีคนหยิบไปใช้ดิบ ๆ

### Job

```sql
CREATE TABLE jobs (
  id          UUID PRIMARY KEY,
  match_id    TEXT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  stages      TEXT[] NOT NULL,
  stage_idx   INT NOT NULL DEFAULT 0,
  status      TEXT NOT NULL,   -- QUEUED/RUNNING/COMPLETED/FAILED
  progress    REAL NOT NULL DEFAULT 0,
  error       TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 4. รูปแบบ Ground Truth

หนึ่งไฟล์ต่อแมตช์ `data/groundtruth/M001/positions.jsonl`
หนึ่งบรรทัดต่อหนึ่งเฟรมที่ label

```jsonc
{
  "frame_idx": 18420,
  "game_clock": 307.0,
  "labeler": "cm",
  "labeled_at": "2026-09-06",
  "annotations": [
    { "slot": 0, "x": 0.421, "y": 0.612, "visible": true,  "occluded": false },
    { "slot": 1, "x": 0.480, "y": 0.503, "visible": true,  "occluded": true  },
    { "slot": 5, "visible": false, "reason": "FOG" }
  ]
}
```

ฟิลด์ `occluded` จำเป็นเพราะกรณี icon ทับกันคือความเสี่ยงอันดับหนึ่งใน §77
ต้องรายงาน metric แยกระหว่างเฟรมที่ occluded กับไม่ occluded
ไม่งั้นตัวเลขรวมจะดูดีเกินจริง

Ground truth ของ event `data/groundtruth/M001/events.jsonl`

```jsonc
{ "event_type": "ROTATION", "start_clock": 133.0, "end_clock": 146.0,
  "player_ids": ["P02"], "zone_from": "MID", "zone_to": "DRAGON_LANE" }
```

---

## 5. เกณฑ์การจับคู่ตอนประเมิน

ต้องนิยามให้ชัด ไม่งั้นตัวเลข precision/recall เปรียบเทียบข้ามครั้งไม่ได้

| อย่าง | เกณฑ์นับว่าตรงกัน |
|-------|-------------------|
| Detection | ระยะ normalized ≤ 0.02 (ราว 3–4 px บน minimap 180 px) |
| Track identity | detection ตรงกัน **และ** slot ตรงกัน |
| Event ช่วงเวลา | IoU ของช่วงเวลา ≥ 0.5 และ event_type ตรงกัน |
| Rotation | เพิ่มเงื่อนไข zone_from และ zone_to ต้องตรงกัน |

ค่าเหล่านี้เก็บใน `configs/params/eval.yaml` และห้ามแก้โดยไม่บันทึกเหตุผล
