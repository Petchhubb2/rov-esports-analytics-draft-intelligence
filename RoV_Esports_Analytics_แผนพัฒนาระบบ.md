# RoV Esports Analytics & Draft Intelligence
## แผนพัฒนาระบบวิเคราะห์ Macro จาก Broadcast/Spectator Video + Draft Simulator

---

## 1. ภาพรวมโครงการ

โครงการนี้เป็นระบบวิเคราะห์การแข่งขัน RoV จาก **คลิปการแข่งขันมุมมองผู้ชม (Broadcast / Spectator View)** โดยไม่พึ่งพา API จากตัวเกม

ระบบแบ่งเป็น 2 ระบบหลัก:

1. **RoV Macro Analytics**
   - ตรวจจับตำแหน่งผู้เล่นจาก Minimap
   - ติดตามการเคลื่อนที่
   - วิเคราะห์ Rotation
   - วิเคราะห์ Gank
   - วิเคราะห์ Objective Setup
   - วิเคราะห์ Teamfight
   - สร้าง Heatmap
   - สร้าง Player / Team Profile

2. **RoV Draft Intelligence**
   - จำลอง Pick / Ban
   - วิเคราะห์ Counter
   - วิเคราะห์ Synergy
   - วิเคราะห์ Team Composition
   - ให้คะแนน Draft
   - แนะนำ Pick / Ban
   - รองรับข้อมูลตาม Patch
   - ในอนาคตสามารถเชื่อมกับข้อมูล Player และ Team Style ได้

แนวคิดหลัก:

```text
Broadcast Video
      ↓
Video Processing
      ↓
Computer Vision
      ↓
Player Position Data
      ↓
Movement Tracking
      ↓
Macro Event Detection
      ↓
Macro Analytics

Draft Data
      ↓
Counter / Synergy / Composition Engine
      ↓
Draft Recommendation
```

---

# 2. เป้าหมายของระบบ

ระบบควรตอบคำถามสำคัญ 4 กลุ่ม

### 2.1 วิเคราะห์ว่าผู้เล่นเดินอย่างไร

ตัวอย่าง:

- Jungle เปิดเกมด้วยเส้นทางใด
- Mid Rotation ไปฝั่งไหน
- Support หมุนไป Lane ใดบ่อย
- ผู้เล่นกลับ Base ช่วงใด
- ผู้เล่นเข้าพื้นที่ Objective ก่อนหรือหลังเพื่อน

### 2.2 วิเคราะห์ว่า "ทีม" เล่น Macro อย่างไร

ตัวอย่าง:

- ทีมให้ Priority กับ Abyssal Dragon หรือ Dark Slayer
- ทีมเตรียม Objective อย่างไร
- ใครเข้า Zone ก่อน
- ทีมรวมตัวก่อน Objective กี่วินาที
- ทีมตอบสนองอย่างไรเมื่อเสียป้อมหรือ Objective

### 2.3 วิเคราะห์ Draft

ตัวอย่าง:

- Hero ตัวนี้ Counter Composition ฝั่งตรงข้ามหรือไม่
- Draft ขาด Role หรือไม่
- Team Composition มี Synergy หรือไม่
- Draft เหมาะกับ Early / Mid / Late Game หรือไม่

### 2.4 วิเคราะห์ Player / Team Style

ตัวอย่าง:

- Player A เป็น Objective-oriented Jungler
- Player B มี First Rotation ไป Dragon บ่อย
- Team A ชอบรวม 3 คนก่อน Objective
- Support ของ Team B มีแนวโน้มเดินกับ Jungle

---

# 3. ข้อมูลที่ระบบใช้

## Input หลัก

ใช้ไฟล์วิดีโอการแข่งขัน:

```text
.mp4
```

จาก Broadcast / Spectator View

ตัวอย่างคลิป:

```text
1280 × 720
60 FPS
```

ไม่จำเป็นต้องประมวลผลทุก 60 FPS ตั้งแต่เริ่ม

แนวทางเริ่มต้น:

```text
Raw Video
60 FPS

        ↓

Computer Vision
ประมาณ 5–10 FPS

        ↓

Position Sampling
ประมาณ 1–2 FPS
```

---

# 4. จุดเด่นของ Broadcast / Spectator View

คลิปแบบ Broadcast มีข้อมูลหลายแหล่งใน Frame เดียว:

```text
┌────────────────────────────────────────────┐
│ Minimap                                    │
│                                            │
│                  Main Game                 │
│                                            │
│                                            │
│ Side HUD                         Side HUD │
│                                            │
└────────────────────────────────────────────┘
```

ข้อมูลที่เราสามารถใช้ร่วมกัน:

### Minimap

- ตำแหน่งผู้เล่น
- ตำแหน่งทีม
- ตำแหน่งศัตรูที่มองเห็น
- ป้อม
- Objective
- พื้นที่ Jungle / Lane

### Side HUD

- Team
- Player
- Hero
- Level / State บางส่วน

### Main View

- Combat
- Damage
- Health Bar
- Kill Event
- Skill / Teamfight Event
- Objective Event บางส่วน

หลักการคือ:

```text
Minimap + Side HUD + Main View
                  ↓
             Match State
```

---

# 5. สิ่งที่ระบบไม่ควรทำ

ไม่ควรเริ่มจากการพยายามตรวจจับทุกอย่างพร้อมกัน

ไม่ควรเริ่มด้วย:

```text
❌ Train YOLO หลายร้อย Class
❌ ทำ Draft AI ก่อนมี Dataset
❌ ให้ LLM เดา Macro
❌ ทำ Dashboard ใหญ่ก่อน Vision สำเร็จ
❌ อ้างว่าตำแหน่งที่ตรวจไม่พบเป็นตำแหน่งจริง
```

ควรเริ่มจาก:

```text
Video
 ↓
Minimap
 ↓
Hero Position
 ↓
Tracking
 ↓
Movement Data
```

ก่อน

---

# 6. Architecture ภาพรวม

```text
                         RoV Broadcast Video
                                  │
                                  ▼
                           Video Ingestion
                                  │
                                  ▼
                          Broadcast Parser
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
             ▼                    ▼                    ▼
          Minimap              Side HUD            Main View
             │                    │                    │
             ▼                    ▼                    ▼
       Player Position        Player/Hero         Game Events
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  ▼
                           Match Database
                                  │
                 ┌────────────────┼────────────────┐
                 │                │                │
                 ▼                ▼                ▼
             Tracking        Macro Engine      Draft Engine
                 │                │                │
                 ▼                ▼                ▼
          Movement Data      Macro Events    Pick / Ban
                 │                │                │
                 └────────────────┼────────────────┘
                                  ▼
                           Analytics Dashboard
```

---

# 7. แบ่งระบบออกเป็น 8 ส่วน

```text
1. Video Ingestion
2. Broadcast Parser
3. Minimap Vision
4. Player Tracking
5. Event Detection
6. Macro Engine
7. Draft Intelligence
8. Analytics Dashboard
```

---

# 8. SYSTEM 1 — Video Ingestion

หน้าที่:

```text
Upload Video
      ↓
Read Metadata
      ↓
ตรวจ Resolution
      ↓
ตรวจ FPS
      ↓
ตรวจ Duration
      ↓
สร้าง Match ID
      ↓
สร้าง Processing Job
```

ตัวอย่าง:

```json
{
  "match_id": 1001,
  "width": 1280,
  "height": 720,
  "fps": 60,
  "duration": 1842
}
```

ควรมีสถานะ Job:

```text
UPLOADED
PROCESSING
DETECTING
TRACKING
ANALYZING
COMPLETED
FAILED
```

ไม่ควรประมวลผล Video ทั้งหมดใน HTTP Request เดียว

---

# 9. SYSTEM 2 — Broadcast Parser

เนื่องจาก Layout ของ Broadcast ค่อนข้างคงที่ เราสามารถกำหนด ROI ได้

ตัวอย่าง:

```text
FULL FRAME
1280 × 720

MINIMAP
ประมาณบริเวณซ้ายบน

LEFT HUD
บริเวณซ้ายด้านข้าง

RIGHT HUD
บริเวณขวาด้านข้าง

TOP SCORE
บริเวณด้านบนกลาง
```

แนวคิด:

```text
Full Frame
    ↓
Crop ROI
    ├── Minimap
    ├── Left HUD
    ├── Right HUD
    └── Top HUD
```

ข้อดี:

- เร็ว
- ลด Noise
- ไม่ต้อง Detect UI ใหม่ทุก Frame
- ทำงานง่ายกว่า Object Detection ทั่วทั้งจอ

---

# 10. SYSTEM 3 — Minimap Vision

นี่คือ Core ของระบบ Macro

Pipeline:

```text
Frame
 ↓
Crop Minimap
 ↓
Image Processing
 ↓
Detect Hero Icon
 ↓
Get Center X/Y
 ↓
Classify / Identify Hero
```

---

# 11. รูปแบบ Hero Icon

จากตัวอย่าง Minimap Hero ถูกแสดงเป็นลักษณะ:

```text
วงกลม
+
Hero Portrait
+
Team / Border
```

ดังนั้น Candidate Object ควรเก็บ:

```text
center_x
center_y
radius
team
appearance
confidence
```

ตัวอย่าง:

```json
{
  "x": 134,
  "y": 87,
  "radius": 8,
  "team": "blue"
}
```

---

# 12. วิธีตรวจจับ Hero Icon

ควรพัฒนาเป็นลำดับ ไม่ใช้ AI ทันที

## Level 1 — OpenCV

ทดลอง:

```text
Color Segmentation
Contour
Circle Detection
Template Matching
```

เป้าหมาย:

```text
ตรวจพบตำแหน่งวงกลม / Icon
```

## Level 2 — Template + Tracking

ใช้:

```text
Detection
+
Previous Frame
```

## Level 3 — Custom Object Detection

หาก OpenCV + Tracking ไม่เพียงพอ ค่อยใช้:

```text
YOLO
PyTorch
```

---

# 13. Hero Identification

ไม่จำเป็นต้องทำ Class ของ Hero ทั้งเกมตั้งแต่แรก

ใน 1 Match มี Hero สูงสุด 10 ตัวที่เกี่ยวข้อง

จึงใช้แนวคิด:

```text
Draft / Match Setup
        ↓
10 Selected Heroes
        ↓
Create Templates
        ↓
Search only those Heroes
```

เช่น:

```text
Nakroth
Tulen
Hayate
Aya
Omen
...
```

จากนั้นตรวจ Icon เฉพาะกลุ่มนี้

---

# 14. Player Identity

ต้องแปลง:

```text
Hero
 ↓
Player
 ↓
Role
 ↓
Team
```

ตัวอย่าง:

```text
Nakroth
 ↓
Player A
 ↓
Jungle
 ↓
SLX
```

ข้อมูลนี้อาจสร้างจาก:

- Draft
- Side HUD
- Match Setup
- Manual Confirmation

---

# 15. Player Tracking

การ Detect ทุก Frame แบบอิสระอาจทำให้ Identity เปลี่ยน

จึงต้องใช้ Tracking

ตัวอย่าง:

```text
10:00
Nakroth → (0.42, 0.61)

10:01
Nakroth → (0.43, 0.60)

10:02
Nakroth → (0.45, 0.58)

10:03
Nakroth → (0.48, 0.55)
```

สามารถใช้:

```text
Kalman Filter
Tracking Algorithm
```

หรือวิธีที่ง่ายกว่าใน Prototype ก่อน

---

# 16. การจัดการกรณี Icon ซ้อน

Teamfight อาจเกิด:

```text
Hero A
Hero B
Hero C
```

ซ้อนกันบน Minimap

จึงต้องมี:

```text
visible
confidence
source
```

ตัวอย่าง:

```json
{
  "hero": "Nakroth",
  "x": 0.45,
  "y": 0.57,
  "visible": true,
  "confidence": 0.96,
  "source": "detection"
}
```

เมื่อหา Icon ไม่ได้:

```json
{
  "hero": "Nakroth",
  "visible": false,
  "confidence": 0.61,
  "source": "tracking"
}
```

สำคัญ:

**Observed และ Inferred ต้องแยกกัน**

ไม่ควรเปลี่ยนค่าที่คาดเดาให้กลายเป็น Ground Truth

---

# 17. Data Model สำหรับ Position

ข้อมูล Position ที่แนะนำ:

```text
timestamp
match_id
player_id
hero_id
team_id
x
y
visible
confidence
source
```

ตัวอย่าง:

```json
{
  "timestamp": 600.5,
  "match_id": 1001,
  "player_id": 3,
  "hero_id": 17,
  "team_id": "blue",
  "x": 0.43,
  "y": 0.57,
  "visible": true,
  "confidence": 0.96,
  "source": "detection"
}
```

---

# 18. Map Coordinate

ตำแหน่ง Pixel จาก Minimap ต้องถูก Normalize:

```text
X = 0.00 → 1.00
Y = 0.00 → 1.00
```

ข้อดี:

รองรับ Video:

```text
720p
1080p
1440p
```

โดยไม่ต้องใช้ระบบ Coordinate คนละชุด

---

# 19. Map Calibration

ก่อนเริ่มวิเคราะห์จริง ต้องมี Calibration

กำหนด:

```text
Minimap Top Left
Minimap Bottom Right
```

แล้ว Mapping:

```text
Pixel Coordinate
      ↓
Normalized Coordinate
      ↓
Map Coordinate
```

ควรบันทึก Calibration ต่อ Broadcast Layout

เพราะ Broadcast แต่ละรายการอาจมีตำแหน่ง UI ต่างกัน

---

# 20. Map Zone

หลังได้ X/Y แล้ว ให้แบ่ง Map เป็น Polygon / Zone

ตัวอย่าง:

```text
DS_LANE
TOP_JUNGLE
MID
BOT_JUNGLE
DRAGON_LANE
RIVER_TOP
RIVER_BOTTOM
DRAGON_PIT
SLAYER_PIT
BASE_BLUE
BASE_RED
```

ดังนั้น:

```text
x = 0.43
y = 0.57
```

จะกลายเป็น:

```text
MID / RIVER
```

---

# 21. Ground Truth Dataset

ก่อน Train Model หรืออ้าง Accuracy เราต้องมี Ground Truth

ตัวอย่าง:

```text
Time     Player       Hero       Team     X      Y
-----------------------------------------------------
05:30    Player A     Nakroth    Blue    .42    .61
05:30    Player B     Tulen      Blue    .48    .50
05:30    Player C     Thane      Red     .55    .47
```

AI ตรวจได้:

```text
Player A → .43, .60
```

จึงคำนวณ Error ได้

---

# 22. Annotation Tool

ควรสร้าง Tool สำหรับ Label Dataset

หน้าจอ:

```text
Video Time: 05:30

┌──────────────────┐
│     MINIMAP      │
│                  │
│        ●         │
│    ●             │
└──────────────────┘
```

ผู้ใช้กำหนด:

```text
Player A
Hero A
Team Blue
X
Y
Visible
```

แล้วบันทึกเป็น JSON / CSV

---

# 23. Sampling Dataset

ไม่ต้อง Label ทุก Frame

Prototype:

```text
1 Frame / 0.5 sec
```

ช่วง Event สำคัญ:

```text
1 Frame / 0.1–0.25 sec
```

เพื่อเก็บข้อมูลละเอียดขึ้น

---

# 24. SYSTEM 4 — Event Detection

เมื่อมี Position Data แล้วจึงสร้าง Event

Event หลัก:

```text
Rotation
Gank
Grouping
Objective Setup
Teamfight
Death
Recall / Return Base
Lane Swap
Split Push
```

---

# 25. Rotation Detection

เงื่อนไขพื้นฐาน:

```text
Zone A
 ↓
Zone B
```

ภายในเวลาที่กำหนด

ตัวอย่าง:

```text
Player:
MID

↓

RIVER

↓

DRAGON SIDE
```

Output:

```text
ROTATION

MID → DRAGON
Duration: 13 sec
```

---

# 26. Gank Detection

ไม่ควรฟันธงจากการเคลื่อนที่อย่างเดียว

ใช้หลาย Feature:

```text
Jungle / Mid / Support
+
เข้าสู่ Lane
+
Enemy อยู่ในพื้นที่
+
ระยะห่างลดลง
+
การปะทะ
```

Output:

```text
Possible Gank
Confidence: 0.87
```

---

# 27. Grouping Detection

เมื่อผู้เล่นหลายคนอยู่ใกล้กัน:

```text
Jungle
Mid
Support
```

แล้วอยู่ใน Radius เดียวกัน

Output:

```text
3-Man Group
```

สามารถใช้ต่อกับ Objective / Teamfight

---

# 28. Objective Setup Detection

ตัวอย่าง:

```text
Jungle
+
Mid
+
Support
```

กำลังเคลื่อนเข้า:

```text
Dragon
```

ก่อน Objective

Output:

```text
OBJECTIVE_SETUP
```

ควรเก็บ:

```text
start_time
end_time
team
players
objective
zone
confidence
```

---

# 29. Teamfight Detection

ใช้ข้อมูลหลายแหล่ง:

```text
Minimap
+
Main View
+
Health State
+
Damage
+
Kill Event
```

หลักการ:

```text
Player count สูง
+
Distance ต่ำ
+
Combat indicators
```

Output:

```text
TEAMFIGHT

Time: 10:08
Location: Mid / Jungle
Blue: 4
Red: 3
Duration: 18 sec
```

---

# 30. Kill / Death Event

ใช้ Main View / HUD ร่วมกับ Minimap

ตัวอย่าง:

```text
Alive
 ↓
Death Event
 ↓
Disappear
 ↓
Respawn
```

สร้าง:

```text
PLAYER_DEATH
PLAYER_RESPAWN
```

---

# 31. SYSTEM 5 — Macro Engine

แบ่ง Macro เป็น 4 Layer

## Layer 1 — Movement

```text
Position
Distance
Time
Path
```

## Layer 2 — Pattern

```text
Rotation
Grouping
Lane Swap
Objective Setup
```

## Layer 3 — Behavior

```text
Aggressive
Farming
Roaming
Objective-oriented
Split Push
```

## Layer 4 — Strategic Insight

ตัวอย่าง:

```text
Team A มี Dragon Priority สูง

Support มักรวมกับ Jungle ก่อน Objective

Jungle มี First Rotation ไป Dragon สูง
```

Insight ควรสร้างจาก Raw Metrics + Rule + Statistics

ไม่ควรให้ LLM เดาสุ่ม

---

# 32. Player Profile

ตัวอย่าง:

```text
Player: ABC
Role: Jungle
Matches: 42
```

### Opening

```text
Blue Start      71%
Red Start       19%
Invade          10%
```

### First Rotation

```text
Dragon Side     64%
Mid             23%
Top Side        13%
```

### Objective

```text
Dragon Priority 0.72
Slayer Priority 0.51
```

### Style

```text
Aggression      78
Farming         61
Roaming         83
Objective       88
```

---

# 33. Macro Score

สามารถสร้าง Score เพื่อสรุปได้ แต่ต้องเก็บ Raw Metrics ด้วย

ตัวอย่าง:

```text
Rotation       18 / 20
Objective      19 / 20
Map Control    15 / 20
Teamplay       17 / 20
Timing         16 / 20

Total          85 / 100
```

คะแนนเป็น Summary ไม่ใช่ข้อมูลต้นฉบับ

---

# 34. SYSTEM 6 — Draft Intelligence

Draft Engine แยกจาก Video Engine แต่เชื่อม Database ได้

Draft State:

```text
BAN
PICK
BAN
PICK
...
```

ข้อมูล:

```text
match_id
phase
order
team_id
action
hero_id
```

---

# 35. Draft Simulator

หน้าหลัก:

```text
┌──────────────────────────────────────┐
│           DRAFT SIMULATOR            │
├──────────────────┬───────────────────┤
│ BLUE TEAM        │ RED TEAM          │
│                  │                   │
│ BAN              │ BAN               │
│ Hero A           │ Hero B            │
│ Hero C           │ Hero D            │
│                  │                   │
│ PICK             │ PICK              │
│ Hero X           │ Hero Y            │
└──────────────────┴───────────────────┘
```

---

# 36. Counter Engine

ไม่ควรดูแค่:

```text
Hero A > Hero B
```

ต้องแยกอย่างน้อย:

```text
1v1 Counter
Lane Counter
Teamfight Counter
Composition Counter
```

เพราะ Lane Counter ไม่เท่ากับ Composition Counter

---

# 37. Draft Score

สูตรเริ่มต้น:

```text
Final Score =

Counter       × 0.30
Synergy       × 0.25
Role Balance  × 0.15
Early Game    × 0.10
Late Game     × 0.10
Objective     × 0.10
```

รวม = 100%

ควรเริ่มจาก Rule-Based Scoring ก่อน

---

# 38. Hero Synergy

Database:

```text
hero_1
hero_2
synergy_score
```

ตัวอย่าง:

```text
Hero A + Hero B = 92
Hero A + Hero C = 74
```

---

# 39. Hero Matchup

Database:

```text
hero_id
enemy_hero_id
patch_id
win_rate
counter_score
sample_size
```

ควรเก็บ `sample_size` เพื่อช่วยประเมินความน่าเชื่อถือของสถิติ

---

# 40. Patch System

เพราะ Meta เปลี่ยนตาม Patch

Database:

```text
patches

id
version
release_date
```

Hero Statistics:

```text
hero_stats

hero_id
patch_id
pick_rate
ban_rate
win_rate
```

ห้ามรวมข้อมูลทุก Patch โดยไม่แยกเวลา

---

# 41. Draft Recommendation

Input:

```text
Our Team
+
Enemy Team
+
Ban
+
Available Heroes
```

Output:

```text
Recommended Pick

Hero Z

Counter: 89
Synergy: 94
Role Balance: 91
```

ควรแสดงเหตุผลในรูปของ Metrics ไม่ใช่เพียงข้อความ AI

---

# 42. Player-Specific Draft Intelligence

หลังจากมีข้อมูล Macro + Player Profile แล้ว สามารถวิเคราะห์เพิ่มได้

ตัวอย่าง:

```text
Player A
Jungle

Hero X:
48 Matches
72% Win Rate
First Rotation → Dragon 70%
```

ตอน Draft:

```text
Recommended Ban:
Hero X
```

เหตุผล:

```text
Player-specific threat
```

แยกจาก:

```text
Meta Ban
```

---

# 43. SYSTEM 7 — Database

แนะนำ PostgreSQL / Supabase

ตารางหลัก:

```text
teams
players
heroes
roles
patches

tournaments
matches
match_players
match_draft

video_files
video_frames

player_positions
macro_events
teamfights
objectives

hero_matchups
hero_synergies
player_hero_stats
team_stats
```

---

# 44. player_positions

```text
id
match_id
timestamp
player_id
hero_id
team_id
x
y
visible
confidence
source
```

---

# 45. macro_events

```text
id
match_id
start_time
end_time
event_type
team_id
player_ids
zone
confidence
metadata
```

ตัวอย่าง:

```text
ROTATION
02:13
02:25
SLX
Player A
MID → DRAGON
0.91
```

---

# 46. match_draft

```text
id
match_id
phase
turn_order
team_id
action
hero_id
```

เช่น:

```text
BAN
PICK
BAN
PICK
```

---

# 47. SYSTEM 8 — Dashboard

## Match Overview

```text
SLX 15 - 9 GJC

Gold
42.3K - 38.9K

Game Time
18:32
```

---

# 48. Movement Dashboard

```text
PLAYER MOVEMENT

          MAP

      ●───────●
             /
            ●

Rotation: 7
Gank: 3
Objective Setup: 5
```

---

# 49. Macro Timeline

ควรมี Timeline แบบ:

```text
00:00 ───────────────────────── 20:00

      G      R       O      F
      │      │       │      │
```

โดย:

```text
G = Gank
R = Rotation
O = Objective
F = Fight
```

เมื่อกด Event ให้ Video กระโดดไปเวลานั้น

---

# 50. Heatmap

Filter:

```text
Player
Role
Team
Time Range
```

แสดง:

```text
Movement Heatmap
```

ตัวอย่าง:

```text
Player ABC
00:00–05:00
```

หรือ:

```text
First 8 Minutes
```

---

# 51. Player Comparison

เปรียบเทียบ:

```text
Player A
VS
Player B
```

Metrics:

```text
First Rotation
Objective Participation
Lane Presence
Teamfight Participation
Movement Distance
Grouping Frequency
```

---

# 52. Team Comparison

```text
Team A
VS
Team B
```

Metrics:

```text
Dragon Priority
Slayer Priority
Average Rotation
Objective Setup Time
Fight Frequency
Map Control
```

---

# 53. Video → Analytics Pipeline จริง

```text
1. Upload Video
       ↓
2. Read Metadata
       ↓
3. Extract Key Frames
       ↓
4. Crop Regions
       ↓
5. Detect Minimap Icons
       ↓
6. Identify Hero
       ↓
7. Track Players
       ↓
8. Normalize Coordinates
       ↓
9. Map to Zones
       ↓
10. Detect Events
       ↓
11. Build Macro Timeline
       ↓
12. Save Database
       ↓
13. Dashboard
```

---

# 54. Draft Pipeline

```text
Draft Input
    ↓
Pick / Ban
    ↓
Hero Database
    ↓
Counter Engine
    ↓
Synergy Engine
    ↓
Composition Engine
    ↓
Patch Data
    ↓
Recommendation
```

---

# 55. Architecture ด้าน Backend

แนะนำ:

```text
Next.js
   │
   ▼
FastAPI
   │
   ├── Video Service
   ├── Vision Service
   ├── Tracking Service
   ├── Macro Engine
   └── Draft Engine
   │
   ▼
PostgreSQL / Supabase
```

เหตุผลที่ใช้ Python Backend:

```text
OpenCV
NumPy
PyTorch
YOLO
Scikit-learn
```

เหมาะกับ Python Ecosystem

---

# 56. Frontend

แนะนำ:

```text
Next.js
Tailwind CSS
```

หน้าหลัก:

```text
/dashboard
/matches
/matches/[id]
/players
/players/[id]
/teams
/teams/[id]
/draft
/draft/simulator
```

---

# 57. Backend API ที่ควรมี

ตัวอย่าง:

```text
POST   /matches
GET    /matches
GET    /matches/{id}

POST   /matches/{id}/video
GET    /matches/{id}/processing

GET    /matches/{id}/positions
GET    /matches/{id}/events
GET    /matches/{id}/timeline

GET    /players/{id}
GET    /players/{id}/matches
GET    /players/{id}/macro

POST   /draft/simulate
GET    /heroes
GET    /heroes/{id}/counters
GET    /heroes/{id}/synergy
```

---

# 58. Video Processing Queue

ไม่ควร:

```text
POST /upload
↓
รอนาน
↓
response
```

ควร:

```text
Upload
 ↓
Create Job
 ↓
Queue
 ↓
Worker
 ↓
Process
 ↓
Database
 ↓
Frontend Poll / WebSocket
```

---

# 59. โครงสร้างโปรเจกต์

```text
rov-analytics/

├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   └── lib/
│
├── backend/
│   ├── main.py
│   ├── api/
│   ├── services/
│   │   ├── video/
│   │   ├── minimap/
│   │   ├── tracking/
│   │   ├── events/
│   │   ├── macro/
│   │   └── draft/
│   ├── models/
│   └── database/
│
├── cv/
│   ├── detector/
│   ├── tracker/
│   ├── templates/
│   └── calibration/
│
├── data/
│   ├── raw/
│   ├── frames/
│   ├── labels/
│   └── processed/
│
└── scripts/
```

---

# 60. Technology Stack

## Frontend

```text
Next.js
Tailwind CSS
TypeScript
```

## Backend

```text
Python
FastAPI
```

## Computer Vision

```text
OpenCV
NumPy
```

## Machine Learning

ช่วงแรก:

```text
Scikit-learn
```

ภายหลัง:

```text
PyTorch
YOLO
```

## Database

```text
PostgreSQL
Supabase
```

## Storage

```text
Supabase Storage
```

หรือ Object Storage อื่นที่เหมาะกับไฟล์ Video

---

# 61. Roadmap การพัฒนา

## Phase 0 — วิเคราะห์ Video Format

เป้าหมาย:

```text
รู้ตำแหน่ง Minimap
รู้ตำแหน่ง HUD
รู้ขนาด Icon
รู้รูปแบบ Broadcast
```

Output:

```text
Calibration Config
```

---

## Phase 1 — Proof of Concept

เป้าหมายเดียว:

**ตรวจจับ Hero Icon จาก Minimap**

Pipeline:

```text
Video
 ↓
Crop Minimap
 ↓
Detect Icon
 ↓
Draw Circle
```

Output:

```text
Frame
+
Detected Centers
```

---

# 62. Milestone Phase 1

ต้องสามารถ:

```text
✓ เปิด Video
✓ Crop Minimap
✓ Extract Frame
✓ Detect Candidate Icon
✓ วาดตำแหน่งลง Frame
✓ Save Output
```

ยังไม่ทำ:

```text
❌ Draft AI
❌ Counter
❌ Gank
❌ Teamfight
❌ Player Rating
```

---

# 63. Phase 2 — Hero Identification

```text
Icon
 ↓
Hero Identification
 ↓
Team
 ↓
Player
```

Output:

```text
Player A
Hero A
Blue
X
Y
```

---

# 64. Phase 3 — Tracking

```text
Frame 1
 ↓
Frame 2
 ↓
Frame 3
 ↓
Tracking
```

Output:

```text
time
player
hero
team
x
y
confidence
```

บันทึกเป็น CSV / JSON ก่อน แล้วค่อยลง Database

---

# 65. Phase 4 — Map Analytics

```text
X/Y
 ↓
Map Coordinate
 ↓
Zone
 ↓
Path
 ↓
Heatmap
```

เป้าหมาย:

```text
Movement Path
Movement Distance
Time in Zone
```

---

# 66. Phase 5 — Macro Events

เพิ่ม:

```text
Rotation
Grouping
Objective Setup
Gank
Teamfight
Death
```

---

# 67. Phase 6 — Player / Team Analytics

เพิ่ม:

```text
Player Profile
Team Profile
Role Profile
Heatmap
Timeline
Comparison
```

---

# 68. Phase 7 — Draft Simulator

เพิ่ม:

```text
Pick
Ban
Counter
Synergy
Composition Score
Patch
```

---

# 69. Phase 8 — Integrated Intelligence

รวม:

```text
Draft
+
Player Profile
+
Team Profile
+
Macro
+
Match Result
```

สร้าง:

```text
Player-Specific Ban
Player-Specific Counter
Team-Specific Draft
```

---

# 70. Phase 9 — Machine Learning

เมื่อ Dataset จำนวนมาก:

```text
50 Matches
100 Matches
500 Matches
...
```

ค่อยเริ่มทำ ML

เช่น:

```text
Predict Next Rotation
Predict Objective Setup
Draft Win Probability
Player Style Classification
```

---

# 71. ML สำหรับการทำนาย Rotation

Input:

```text
Current Position
Current Zone
Time
Objective State
Nearby Allies
Nearby Enemies
Player History
Team History
```

Output:

```text
Dragon Side     71%
Mid             19%
Slayer Side     10%
```

ควรเรียกว่า:

```text
Model-estimated probability
```

ไม่ใช่บอกว่าเป็นความจริงแน่นอน

---

# 72. Draft ML

หลังมีข้อมูลเพียงพอ:

```text
Hero Picks
Hero Bans
Team Composition
Players
Patch
Match Result
```

Train Model:

```text
P(Win | Draft, Patch, Team)
```

เริ่มจาก Rule-Based ก่อน

แล้วค่อยเปรียบเทียบกับ ML

---

# 73. Data Quality

ทุก Observation ควรมี:

```text
confidence
source
visible
```

Dashboard ควรสามารถแสดง:

```text
Position Confidence
Event Confidence
```

ตัวอย่าง:

```text
Position Accuracy: 94%
Event Confidence: 87%
```

ตัวเลขเหล่านี้ต้องมาจากการประเมินจริง ไม่ควรตั้งขึ้นเอง

---

# 74. Metrics สำหรับ Computer Vision

## Detection

```text
Precision
Recall
F1 Score
```

## Position

```text
Mean Pixel Error
Normalized Coordinate Error
```

## Tracking

```text
Track Continuity
Identity Switch
```

สิ่งสำคัญคือ Identity Switch

เพราะ:

```text
Hero A → Hero B
```

เป็นข้อผิดพลาดที่มีผลต่อ Macro Analysis มาก

---

# 75. Metrics สำหรับ Macro

ต้องมี Ground Truth Event จากมนุษย์

ตัวอย่าง:

```text
Rotation Precision
Rotation Recall
Rotation F1

Gank Precision
Gank Recall
Gank F1

Teamfight Precision
Teamfight Recall
Teamfight F1
```

---

# 76. Dataset เริ่มต้น

ไม่ต้องเริ่มจากหลายร้อยเกม

เริ่ม:

```text
10–20 Matches
```

ให้ครอบคลุม:

```text
Early Game
Mid Game
Late Game
Normal Movement
Gank
Objective
Teamfight
```

หลังจากนั้นค่อยขยาย:

```text
50
100
500+
```

---

# 77. ความเสี่ยงของระบบ

โดยประมาณจากยากไปง่าย:

```text
★★★★★
Hero Tracking ตอนซ้อนกัน

★★★★★
Identity Tracking

★★★★☆
Teamfight Detection

★★★★☆
Gank Detection

★★★☆☆
Objective Detection

★★☆☆☆
Rotation Detection

★★☆☆☆
Heatmap

★☆☆☆☆
Dashboard
```

ดังนั้นควรลงทุนเวลาให้ Vision และ Data มากกว่า UI ในช่วงต้น

---

# 78. การจัดการ Uncertainty

ระบบต้องแยกระดับ:

```text
Observed
Inferred
Unknown
```

ตัวอย่าง:

```text
Observed:
Hero ถูกมองเห็นบน Minimap

Inferred:
Position จาก Tracking

Unknown:
Hero ไม่อยู่ใน Vision
```

นี่สำคัญมากกับการวิเคราะห์ Macro

เพราะระบบไม่ควรสร้างข้อมูลปลอมจากการไม่มี Vision

---

# 79. Layer ของข้อมูล

แนะนำแบ่งเป็น 4 Layer

```text
LAYER 1
RAW VIDEO

LAYER 2
OBSERVATION

Position
Hero
Team
Combat
Objective

LAYER 3
EVENT

Rotation
Gank
Teamfight
Objective Setup

LAYER 4
INSIGHT

Macro Pattern
Player Style
Team Style
Draft Recommendation
```

หลักการ:

**อย่าเขียนทับ Layer 2 ด้วย Insight**

เพื่อให้สามารถเปลี่ยน Algorithm แล้วประมวลผลใหม่ได้

---

# 80. ตัวอย่าง End-to-End

สมมติ:

```text
Video
```

ระบบตรวจพบ:

```text
10:00
Jungle → Jungle

10:07
Mid → River

10:10
Support → River

10:12
Jungle → Dragon Side
```

ระบบ Event Engine:

```text
Jungle + Mid + Support
        ↓
Dragon Area
```

สร้าง:

```text
OBJECTIVE_SETUP
Confidence: 0.91
```

จากนั้นพบ Combat:

```text
3 Blue
+
3 Red
```

สร้าง:

```text
TEAMFIGHT
```

หลัง Event:

```text
Dragon Taken
```

ระบบสร้าง Timeline:

```text
10:00 Jungle Route
10:07 Mid Rotation
10:10 Support Rotation
10:12 Objective Setup
10:16 Teamfight
10:21 Dragon Taken
```

นี่คือ Macro Timeline

---

# 81. ตัวอย่าง Player Profile จากหลาย Match

```text
PLAYER ABC
JUNGLE

Matches: 42

Opening
Blue Start        71%
Red Start         19%
Invade            10%

First Rotation
Dragon Side       64%
Mid               23%
Top Side           13%

Objective
Dragon Priority   72
Slayer Priority    51

Style
Objective         88
Roaming           83
Aggression        78
Farming           61
```

จากข้อมูลนี้สามารถสร้าง:

```text
Player Style:
Objective-Oriented / Roaming Jungler
```

โดยข้อความสรุปต้องมี Metrics รองรับ

---

# 82. ตัวอย่าง Draft Analysis

Input:

```text
OUR TEAM

DS: Hero A
Jungle: Hero B
Mid: Hero C

ENEMY

DS: Hero D
Jungle: Hero E
Mid: Hero F
```

ระบบคำนวณ:

```text
Counter        86
Synergy        91
Role Balance   90
Early Game     78
Late Game      88
Objective      92
```

Final:

```text
Recommended Pick: Hero X
Score: 87.5 / 100
```

---

# 83. Feature ในเวอร์ชันสุดท้าย

## Match Analysis

```text
✓ Video Player
✓ Minimap Overlay
✓ Player Movement
✓ Heatmap
✓ Macro Timeline
✓ Event Detection
✓ Teamfight Analysis
✓ Objective Analysis
```

## Player Analysis

```text
✓ Player Profile
✓ Hero Pool
✓ Movement Profile
✓ Rotation Profile
✓ Objective Profile
✓ Teamfight Profile
```

## Team Analysis

```text
✓ Team Macro
✓ Rotation Pattern
✓ Objective Pattern
✓ Player Interaction
✓ Match Comparison
```

## Draft

```text
✓ Pick / Ban
✓ Counter
✓ Synergy
✓ Composition
✓ Patch
✓ Player-specific Ban
✓ Recommendation
```

---

# 84. เป้าหมายสุดท้ายของระบบ

ผู้ใช้อัปโหลด:

```text
MATCH VIDEO
```

ระบบสร้าง:

```text
MATCH ANALYSIS
```

### Team Macro

```text
SLX

Dragon Priority       82
Objective Setup       76
Early Rotation        91
Teamfight Grouping    84
```

### Player

```text
Jungle

Opening:
Blue → Mid → Dragon

Style:
Objective Oriented
```

### Timeline

```text
01:42 Rotation
02:13 Gank
03:05 Objective Setup
03:18 Teamfight
03:26 Dragon Taken
```

### Draft

```text
Best Counter
Hero A

Best Synergy
Hero B

Recommended Ban
Hero C
```

เมื่อกด Event:

```text
03:05 Objective Setup
```

Video กระโดดไปเวลานั้น และแสดง Map Overlay

---

# 85. Roadmap ฉบับสั้นสำหรับการทำจริง

```text
PHASE 1
Minimap Crop
        ↓
Icon Detection

PHASE 2
Hero Identification
        ↓
Tracking

PHASE 3
Coordinate
        ↓
Zone
        ↓
Heatmap

PHASE 4
Rotation
        ↓
Gank
        ↓
Objective
        ↓
Teamfight

PHASE 5
Player Profile
        ↓
Team Profile

PHASE 6
Draft Simulator
        ↓
Counter
        ↓
Synergy
        ↓
Composition

PHASE 7
Integrated Intelligence

PHASE 8
ML / AI
```

---

# 86. Milestone ที่ควรใช้เป็นตัวตัดสิน

## Milestone 1

```text
Video → Minimap → Icon
```

ถ้ายังไม่ผ่าน ให้หยุดที่นี่

## Milestone 2

```text
Icon → Hero → Tracking
```

## Milestone 3

```text
Tracking → Map → Heatmap
```

## Milestone 4

```text
Heatmap → Macro Events
```

## Milestone 5

```text
Macro → Player/Team Profile
```

## Milestone 6

```text
Draft → Counter/Synergy
```

## Milestone 7

```text
Draft + Player + Macro
```

## Milestone 8

```text
ML / AI
```

---

# 87. Prototype แรกที่ควรเริ่มทันที

เป้าหมาย:

> **จาก Broadcast Video 1280×720 → Crop Minimap → Detect Hero Icon → หา X/Y → วาดตำแหน่งบน Minimap**

Output:

```text
Timestamp
Hero
Team
X
Y
Confidence
```

ตัวอย่าง:

```text
10.00
Nakroth
Blue
0.42
0.61
0.96
```

หากทำขั้นนี้สำเร็จ ระบบทั้งหมดที่เหลือสามารถต่อยอดจากข้อมูลชุดนี้ได้

---

# 88. หลักการสำคัญของโครงการ

1. **Video เป็นแหล่งข้อมูลหลัก**
2. **Minimap เป็นแหล่งข้อมูล Position หลัก**
3. **Side HUD ใช้ช่วย Identity**
4. **Main View ใช้ช่วยตรวจ Event**
5. **Observed ต้องแยกจาก Inferred**
6. **Raw Data ต้องเก็บไว้**
7. **Macro Insight ต้องเกิดจากข้อมูล**
8. **Draft ต้องผูกกับ Patch**
9. **AI ควรมาเมื่อ Dataset พร้อม**
10. **Vision ต้องผ่านการวัด Accuracy ก่อนนำไปใช้วิเคราะห์**

---

# 89. ข้อสรุป

ระบบที่ควรสร้างไม่ใช่เพียง:

```text
"ระบบจับคนเดินบน Minimap"
```

แต่เป็น:

# RoV Esports Analytics & Draft Intelligence Platform

โดยมีแกนหลัก:

```text
Broadcast Video
      ↓
Computer Vision
      ↓
Player Tracking
      ↓
Macro Events
      ↓
Player / Team Analytics
      ↓
Draft Intelligence
      ↓
Scouting / Recommendation
```

และจุดเริ่มต้นที่ถูกต้องที่สุดคือ:

```text
V0.1
Crop Minimap
+
Detect Hero Icon
+
Get Position
```

เมื่อ V0.1 ผ่าน จึงค่อยเพิ่ม Tracking, Macro, Draft และ AI ตามลำดับ
