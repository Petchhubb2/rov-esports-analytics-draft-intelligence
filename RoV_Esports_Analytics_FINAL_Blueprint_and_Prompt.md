# RoV Esports Analytics & Draft Intelligence
## Final Project Blueprint + Development Prompt

> ระบบวิเคราะห์การแข่งขัน RoV จาก Broadcast / Spectator Video, วิเคราะห์ Macro, วิเคราะห์ Draft, Counter / Matchup และสร้าง Macro Plan จาก Draft

---

# 1. Project Vision

ระบบนี้มีเป้าหมายเป็น **RoV Esports Analytics Platform** ที่รับวิดีโอการแข่งขันจากมุมมองผู้ชม (Broadcast / Spectator View) แล้วแปลงวิดีโอเป็นข้อมูลเชิงโครงสร้าง ก่อนนำไปวิเคราะห์ Macro, Player, Team และ Draft

ระบบต้องสามารถตอบคำถามได้ว่า:

1. ผู้เล่นแต่ละคนเดินและ Rotate อย่างไร
2. ทีมมี Macro Pattern แบบไหน
3. ผู้เล่นแต่ละคนมี Style แบบใด
4. Draft นี้มี Counter / Synergy อย่างไร
5. Hero ไหนเป็นตัวชนะทางหรือแพ้ทาง
6. Draft นี้ควรใช้ Macro แบบใด
7. ช่วงต้นเกมควรแบ่งผู้เล่นอย่างไร
8. แผน Primary / Secondary / Emergency คืออะไร
9. สิ่งที่ทีมทำจริงตรงกับแผนที่แนะนำหรือไม่
10. คู่แข่งมี Pattern และแนวโน้มอะไรที่สามารถนำไปใช้ Scouting ได้

---

# 2. Core Concept

ระบบต้องไม่ทำ:

```text
Video
↓
AI
↓
"ทีมนี้เล่นดี"
```

แต่ต้องทำ:

```text
RAW VIDEO
↓
OBSERVATION
↓
POSITION DATA
↓
EVENT
↓
PATTERN
↓
STATISTICS
↓
INSIGHT
```

ฝั่ง Draft:

```text
DRAFT
↓
HERO DATA
↓
COUNTER
↓
SYNERGY
↓
COMPOSITION
↓
WIN CONDITION
↓
MACRO PLAN
```

และสุดท้าย:

```text
MACRO PLAN
↓
ACTUAL GAMEPLAY
↓
VIDEO ANALYSIS
↓
ACTUAL MACRO
↓
PLAN VS ACTUAL
```

---

# 3. Final System Architecture

```text
                         RoV Analytics Platform
                                  │
           ┌──────────────────────┼──────────────────────┐
           │                      │                      │
           ▼                      ▼                      ▼
     Video Analysis          Draft System           Scouting
           │                      │                      │
           ▼                      ▼                      ▼
   Player / Team Macro      Counter / Synergy      Player / Team
           │                      │                 Tendencies
           └──────────────────────┼──────────────────────┘
                                  ▼
                           Macro Planner
                                  │
                                  ▼
                          Intelligence Layer
                                  │
                                  ▼
                           Web Dashboard
```

---

# 4. ระบบหลักทั้งหมด

```text
01. Video Ingestion
02. Broadcast Layout Parser
03. Minimap Vision
04. Hero Identification
05. Player Identity
06. Player Tracking
07. Map Calibration
08. Map / Zone Engine
09. Ground Truth / Annotation
10. Event Detection
11. Macro Analytics
12. Heatmap
13. Player Analytics
14. Team Analytics

15. Draft Simulator
16. Pick Engine
17. Ban Engine
18. Counter Engine
19. Matchup Engine
20. Synergy Engine
21. Composition Engine
22. Draft Score Engine
23. Patch / Meta Engine
24. Draft Recommendation
25. Player-specific Draft
26. Team-specific Draft

27. Macro Knowledge Base
28. Macro Rule Engine
29. Macro Planner
30. Primary / Secondary / Emergency Plan
31. Decision Tree
32. Actual vs Recommended

33. Scouting
34. Prediction / ML
35. Dataset Management
36. Model Versioning
37. Data Versioning
38. Authentication / Permission
39. Processing Queue
40. API
41. Database
42. Analytics Dashboard
43. Replay / Event Review
44. Testing / Evaluation
```

---

# 5. Final Project Structure

```text
rov-analytics/

├── frontend/
│   ├── app/
│   │   ├── dashboard/
│   │   ├── matches/
│   │   ├── players/
│   │   ├── teams/
│   │   ├── heroes/
│   │   ├── draft/
│   │   ├── counter/
│   │   ├── matchups/
│   │   ├── macro-planner/
│   │   └── scouting/
│   │
│   ├── components/
│   │   ├── map/
│   │   ├── video/
│   │   ├── draft/
│   │   ├── macro/
│   │   ├── charts/
│   │   ├── player/
│   │   └── ui/
│   │
│   └── lib/
│       ├── api.ts
│       ├── types.ts
│       └── utils.ts
│
├── backend/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── matches.py
│   │   ├── videos.py
│   │   ├── players.py
│   │   ├── teams.py
│   │   ├── heroes.py
│   │   ├── draft.py
│   │   ├── macro.py
│   │   └── analytics.py
│   │
│   ├── services/
│   │   ├── video/
│   │   ├── broadcast/
│   │   ├── vision/
│   │   ├── tracking/
│   │   ├── events/
│   │   ├── macro/
│   │   ├── draft/
│   │   ├── counter/
│   │   ├── scouting/
│   │   └── prediction/
│   │
│   ├── models/
│   ├── repositories/
│   └── database/
│
├── cv/
│   ├── datasets/
│   ├── labels/
│   ├── templates/
│   ├── models/
│   └── experiments/
│
├── knowledge/
│   ├── macro/
│   │   ├── opening/
│   │   ├── wave/
│   │   ├── roaming/
│   │   ├── jungle/
│   │   ├── objective/
│   │   ├── teamfight/
│   │   ├── split_push/
│   │   └── lane_swap/
│   │
│   ├── draft/
│   ├── counter/
│   └── sources/
│
├── data/
│   ├── raw/
│   ├── frames/
│   ├── minimap/
│   ├── annotations/
│   ├── processed/
│   ├── exports/
│   └── cache/
│
├── scripts/
├── tests/
├── docker/
├── requirements.txt
├── docker-compose.yml
├── .env
└── README.md
```

---

# 6. Tech Stack

## Frontend

```text
Next.js
TypeScript
Tailwind CSS
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

เริ่มต้น:

```text
Scikit-learn
```

ภายหลังเมื่อ Dataset พร้อม:

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
Object Storage / Supabase Storage
```

---

# 7. System 01 — Video Ingestion

## Input

```text
.mp4
```

## Workflow

```text
Upload
↓
Read Metadata
↓
Resolution
↓
FPS
↓
Duration
↓
Create Match
↓
Create Processing Job
```

## Output

```text
match_id
video_id
fps
width
height
duration
processing_status
```

Status:

```text
UPLOADED
PROCESSING
DETECTING
TRACKING
ANALYZING
COMPLETED
FAILED
```

---

# 8. System 02 — Broadcast Layout Parser

## หน้าที่

กำหนดตำแหน่งของ UI ใน Broadcast

```text
FULL FRAME
│
├── MINIMAP
├── LEFT HUD
├── RIGHT HUD
├── TIMER
├── SCORE
└── MAIN VIEW
```

## Workflow

```text
Video
↓
Select Broadcast Profile
↓
Load ROI
↓
Crop Regions
```

ต้องรองรับหลาย Layout / Resolution

---

# 9. System 03 — Minimap Vision

## เป้าหมาย

ตรวจจับ Hero Icon จาก Minimap

```text
Frame
↓
Crop Minimap
↓
Preprocess
↓
Detect Candidate
↓
Find Center X/Y
↓
Team
↓
Confidence
```

## Algorithm ลำดับแรก

```text
Color Segmentation
Contour
Circle Detection
Template Matching
```

ถ้าไม่พอ:

```text
Custom Object Detection
```

---

# 10. System 04 — Hero Identification

ไม่ต้องให้ Model จำ Hero ทุกตัวตั้งแต่ต้น

ใช้ Draft เป็น Constraint:

```text
Draft
↓
10 Selected Heroes
↓
Create Templates
↓
Search Candidate
↓
Identify Hero
```

---

# 11. System 05 — Player Identity

แปลง:

```text
Hero
↓
Player
↓
Role
↓
Team
```

แหล่งข้อมูล:

```text
Draft
Side HUD
Match Setup
Manual Confirmation
```

---

# 12. System 06 — Player Tracking

## Input

```text
Hero Detection
```

## Output

```text
timestamp
player_id
hero_id
team_id
x
y
confidence
source
visible
```

## Algorithm

```text
Detection
↓
Associate with Previous Frame
↓
Track
↓
Update State
```

อาจใช้:

```text
Kalman Filter
Tracking Algorithm
```

ต้องระวัง Identity Switch

---

# 13. System 07 — Map Calibration

```text
Pixel Coordinate
↓
Normalized Coordinate
↓
Map Coordinate
```

ใช้:

```text
X = 0.00–1.00
Y = 0.00–1.00
```

Broadcast แต่ละ Layout ต้องมี Calibration ของตัวเอง

---

# 14. System 08 — Map / Zone Engine

แบ่ง Map เป็น Zone เช่น:

```text
DS_LANE
TOP_JUNGLE
MID
RIVER_TOP
RIVER_BOTTOM
BOT_JUNGLE
DRAGON_LANE
DRAGON_PIT
SLAYER_PIT
BASE_BLUE
BASE_RED
```

Algorithm:

```text
X/Y
↓
Point-in-Polygon
↓
Zone
```

---

# 15. System 09 — Ground Truth / Annotation

สร้างข้อมูลจริงสำหรับตรวจ Accuracy

```text
Video Frame
↓
Human Label
↓
Ground Truth
```

Label:

```text
Player
Hero
Team
X
Y
Visible
Event
```

---

# 16. System 10 — Event Detection

จาก Position + Main View สร้าง:

```text
Rotation
Grouping
Gank
Objective Setup
Objective Contest
Objective Taken
Objective Lost
Teamfight
Death
Respawn
Recall
Lane Swap
Split Push
```

---

# 17. Rotation Algorithm

```text
Current Zone
↓
Previous Zone
↓
Zone Changed?
↓
Check Time
↓
Check Distance
↓
Rotation Event
```

Output:

```text
Player A
MID → DRAGON
Duration: 13 sec
Confidence: 0.91
```

---

# 18. Grouping Algorithm

```text
Players
↓
Calculate Pairwise Distance
↓
Cluster Players
↓
Count Members
↓
Detect Group
```

เช่น:

```text
Jungle + Mid + Roam
```

=

```text
3-Man Group
```

---

# 19. Gank Algorithm

ต้องใช้หลาย Feature:

```text
Jungle / Mid / Roam
+
Enemy Nearby
+
Entering Lane
+
Distance Closing
+
Combat Evidence
```

Output:

```text
Possible Gank
Confidence
```

---

# 20. Objective Algorithm

ตรวจ:

```text
Player Position
+
Objective Position
+
Objective Timer
+
Grouping
+
Combat
```

Event:

```text
Objective Setup
Objective Contest
Objective Taken
Objective Lost
```

---

# 21. Teamfight Algorithm

ใช้:

```text
Minimap
+
Main View
+
Player Count
+
Distance
+
Combat Signal
+
HP / Damage
+
Kill Event
```

ผล:

```text
Teamfight
Start
End
Location
Participants
Result
```

---

# 22. Macro Analytics

ระบบวิเคราะห์:

```text
Movement
↓
Pattern
↓
Behavior
↓
Insight
```

ตัวอย่าง:

```text
Raw:
JG → Mid → Dragon

Pattern:
First Rotation

Statistic:
Dragon-side first rotation = 68%

Insight:
Objective-oriented Jungler
```

---

# 23. Heatmap

Input:

```text
player_positions
```

Output:

```text
Movement Heatmap
Path
Time in Zone
Distance
Zone Frequency
```

Filter:

```text
Player
Role
Team
Time Range
Game Phase
```

---

# 24. Player Analytics

ตัวอย่าง Metrics:

```text
Opening Route
First Rotation
Gank Frequency
Objective Participation
Time in Zone
Movement Distance
Grouping Frequency
Teamfight Participation
```

สร้าง Player Profile

---

# 25. Team Analytics

Metrics:

```text
Dragon Priority
Slayer Priority
Rotation Pattern
Objective Setup
Grouping Pattern
Teamfight Pattern
Map Control
```

สร้าง Team Profile

---

# 26. Draft Simulator

ระบบ:

```text
Pick
Ban
Timer
Undo
Reset
Skip
History
Notes
Swap Sides
Search
Role Filter
```

Draft State ต้องบันทึกทุก Action

---

# 27. Counter Engine

ต้องแยก:

```text
1v1 Counter
Lane Counter
Teamfight Counter
Composition Counter
```

อย่าใช้คำว่า "ตัวนี้แพ้ทาง" โดยไม่มี Context

---

# 28. Matchup Engine

เก็บ:

```text
Hero A
Hero B
Patch
Role
Lane
Games
Wins
Losses
Win Rate
Sample Size
```

หน้า:

```text
Best Matchups
Worst Matchups
```

---

# 29. Synergy Engine

วิเคราะห์:

```text
Hero + Hero
Hero + Hero + Hero
```

Metrics:

```text
Win Rate
Performance
Composition Synergy
```

---

# 30. Composition Engine

ตรวจ:

```text
Role Coverage
Damage
Frontline
Engage
Peel
Poke
Dive
Scaling
Objective
Teamfight
Split Push
```

---

# 31. Patch / Meta Engine

ข้อมูลทั้งหมดต้องผูกกับ:

```text
Patch
Date
Region / Tournament Context
```

Hero Stats:

```text
Pick Rate
Ban Rate
Win Rate
Priority
```

---

# 32. Draft Score Engine

เริ่มต้น Rule-Based:

```text
Counter       × 0.30
Synergy       × 0.25
Role Balance  × 0.15
Early Game    × 0.10
Late Game     × 0.10
Objective     × 0.10
```

ภายหลังสามารถเปรียบเทียบกับ ML

---

# 33. Draft Recommendation

Input:

```text
Our Team
Enemy Team
Available Heroes
Patch
```

Output:

```text
Counter Pick
Synergy Pick
Safe Pick
Anti-Composition Pick
```

พร้อมเหตุผลจาก Metrics

---

# 34. Player-Specific Draft

Input:

```text
Enemy Player
Role
Hero Pool
Recent Performance
Macro Profile
```

Output:

```text
Player-specific Ban
Player-specific Counter
```

---

# 35. Team-Specific Draft

ใช้:

```text
Enemy Team
Historical Draft
Favorite Heroes
Common Duo
First Pick Pattern
Ban Pattern
Macro Pattern
```

Output:

```text
Recommended Ban
Recommended Pick
Recommended Macro Counter
```

---

# 36. Macro Knowledge Base

นี่คือฐานความรู้ของระบบ Planner

โครงสร้าง:

```text
knowledge/
├── opening/
├── wave/
├── roaming/
├── jungle/
├── objective/
├── teamfight/
├── split_push/
└── lane_swap/
```

ข้อมูลแต่ละ Rule:

```text
rule_id
name
phase
conditions
action
priority
patch
source
confidence
notes
```

Macro knowledge ต้องเป็น evidence-based

---

# 37. Macro Planner

ความแตกต่าง:

```text
MACRO ANALYZER
= วิเคราะห์สิ่งที่เกิดขึ้นจริง

MACRO PLANNER
= แนะนำสิ่งที่ควรทำ
```

Workflow:

```text
Draft
↓
Hero Characteristics
↓
Team Composition
↓
Matchups
↓
Win Condition
↓
Objective Priority
↓
Macro Rules
↓
Macro Plan
```

---

# 38. Hero Macro Characteristics

Hero Database ต้องเพิ่ม:

```text
Early Power
Mid Power
Late Power

Wave Clear
Roaming
Mobility
Engage
Peel
Dive
Poke

Objective Damage
Lane Pressure
Jungle Pressure

Scaling
Teamfight
Split Push
```

---

# 39. Macro Tags

ตัวอย่าง:

```text
FAST_CLEAR
EARLY_GANK
EARLY_PRESSURE
SCALING
OBJECTIVE
ENGAGE
PEEL
POKE
DIVE
SPLIT_PUSH
```

---

# 40. Win Condition Engine

ระบบต้องตอบ:

> ทีมนี้ควรชนะเกมด้วยอะไร?

ตัวอย่าง:

```text
Early Objective
+
Mid Skirmish
+
ADC Scaling
```

หรือ:

```text
Split Push
+
Side Lane
+
Pick-off
```

หรือ:

```text
Poke
+
Siege
+
Teamfight
```

---

# 41. Early Game Macro Planner

ช่วงเริ่มต้น:

```text
0:00–1:00
1:00–2:00
2:00–5:00
5:00–8:00
8:00+
```

แต่อย่าใช้เวลาอย่างเดียว

ใช้:

```text
Game Time
+
Objective State
+
Level
+
Power Spike
+
Wave State
+
Gold
+
Vision
+
Player Location
```

---

# 42. ตัวอย่าง Rule

```text
IF

Mid = Fast Clear
AND
Roam = Early Tempo
AND
Jungle = Early Skirmish
AND
Objective is approaching

THEN

Mid + Roam + Jungle
→ Mid Priority
→ River Control
→ Objective Setup
```

Rule ต้องเป็นเงื่อนไข ไม่ใช่สูตรตายตัวทุกเกม

---

# 43. Macro Shape

ระบบสามารถเลือกโครงสร้างทีม เช่น:

```text
3-1-1
3-2
4-1
1-3-1
5-Man
2-2-1
```

แต่ต้องเลือกจาก:

```text
Side Lane Strength
Teamfight
Engage
Wave Clear
Objective
Enemy Threat
```

---

# 44. Primary / Secondary / Emergency Plan

ทุก Draft ควรมี:

```text
PRIMARY PLAN
SECONDARY PLAN
EMERGENCY PLAN
```

ตัวอย่าง:

```text
Primary:
Mid + Jungle + Roam → Dragon

Secondary:
Jungle + DS Pressure

Emergency:
Trade Dragon → Cross-map
```

---

# 45. Decision Tree

```text
Objective Spawn
↓
Mid Priority?
├── YES
│   ↓
│   Contest
│   ↓
│   3-Man Setup
│
└── NO
    ↓
    Cross-map Trade
```

---

# 46. Dynamic Macro

Plan ต้องเปลี่ยนตามสถานการณ์

ตัวอย่าง:

```text
Enemy Jungle Top
→ Dragon Side Advantage
→ Continue Dragon Plan
```

แต่:

```text
Our Jungle Dead
→ Cancel Dragon Contest
→ Cross-map
→ Trade
```

---

# 47. Counter → Macro

ถ้า:

```text
Our DS
แพ้ Enemy DS
```

ระบบไม่ควรบอกแค่:

```text
แพ้ทาง
```

แต่:

```text
Avoid isolated 1v1
↓
Jungle Cover
↓
Mid Rotation
↓
Cross-map Objective
```

---

# 48. Draft → Macro

ตัวอย่าง:

```text
Strong Mid
+
Strong Jungle
+
Strong Roam
+
Weak ADC Early
```

ระบบสร้าง:

```text
Win Condition:
Mid-Jungle-Roam Tempo

Macro:
3-Man River Control

Avoid:
Long ADC Fight
```

---

# 49. Macro → Draft

ถ้าทีมมี Style:

```text
3-Man Mid / River
```

Draft Engine สามารถแนะนำ Hero ที่มี:

```text
Wave Clear
Roam
Skirmish
Objective
Synergy
```

ดังนั้น:

```text
Draft ↔ Macro
```

---

# 50. Actual vs Recommended

หลังจบเกม:

```text
Recommended
↓
Actual Video
↓
Compare
```

ตัวอย่าง:

```text
Recommended:
Mid + Jungle + Roam → River

Actual:
Mid → Side Lane
Jungle → Top Jungle
Roam → ADC
```

Output:

```text
PLAN DEVIATION
```

ไม่ควรสรุปว่า Deviation = เล่นผิดอัตโนมัติ ต้องให้บริบทและหลักฐานประกอบ

---

# 51. Scouting

ก่อนแข่ง:

```text
Enemy Team
↓
Historical Data
↓
Player Tendencies
↓
Team Tendencies
↓
Draft Tendencies
↓
Macro Tendencies
```

Output:

```text
Likely First Pick
Likely Ban
Likely First Rotation
Likely Objective
Common Player Pairing
```

---

# 52. Prediction / ML

เมื่อมีข้อมูลเพียงพอ:

```text
Current State
+
Historical Data
↓
Model
↓
Prediction
```

ตัวอย่าง:

```text
Likely Next Rotation

Dragon Side    71%
Mid            19%
Top Side       10%
```

ต้องแสดงเป็น Model-estimated probability

---

# 53. Draft ML

Input:

```text
Hero Picks
Hero Bans
Team Composition
Players
Patch
Match Result
```

Target:

```text
P(Win | Draft, Patch, Team)
```

Rule-Based ต้องมี Benchmark ก่อน

---

# 54. Data Layers

ห้ามรวมทุกอย่างเป็นข้อมูลเดียว

```text
LAYER 1
RAW VIDEO

LAYER 2
OBSERVATION

LAYER 3
EVENT

LAYER 4
ANALYTICS

LAYER 5
INSIGHT
```

ตัวอย่าง:

```text
Video
↓
Jungle X/Y
↓
Rotation
↓
Dragon First Rotation 68%
↓
Objective-oriented Pattern
```

---

# 55. Database Final

```text
teams
players
roles
heroes
patches

tournaments
series
matches
match_players
match_draft
match_results

videos
video_processing_jobs
broadcast_profiles
video_frames

player_positions
player_states

macro_events
teamfights
objectives
kills
deaths

hero_matchups
hero_synergies
hero_patch_stats

player_hero_stats
player_macro_stats
team_macro_stats

macro_rules
macro_rule_sources
macro_plans
macro_plan_steps

draft_simulations
draft_recommendations

annotations
ground_truth

model_versions
analysis_versions
audit_logs
```

---

# 56. Processing Architecture

Video processing ต้องเป็น asynchronous

```text
Frontend
↓
API
↓
Create Job
↓
Queue
↓
Worker
↓
Video Processing
↓
Computer Vision
↓
Analysis
↓
Database
```

สถานะ:

```text
UPLOADED
EXTRACTING
DETECTING
TRACKING
ANALYZING
COMPLETED
FAILED
```

---

# 57. Frontend Pages

```text
/dashboard

/matches
/matches/[id]
/matches/[id]/macro
/matches/[id]/draft
/matches/[id]/timeline
/matches/[id]/replay

/players
/players/[id]

/teams
/teams/[id]

/heroes
/heroes/[id]

/draft
/draft/simulator

/counter
/matchups

/macro-planner
/scouting
```

---

# 58. Match Dashboard

ควรมี:

```text
Video
Map
Player Positions
Heatmap
Macro Timeline
Events
Draft
Score
```

คลิก Event:

```text
Teamfight 10:23
```

→ Video กระโดดไป 10:23

พร้อม Map Overlay

---

# 59. Draft Dashboard

```text
BLUE                  RED

BAN                   BAN

PICK                  PICK

BAN                   BAN

PICK                  PICK
```

ด้านข้าง:

```text
Draft Score

Counter
Synergy
Composition
Early
Late
Objective
```

และ:

```text
Recommended Pick
Recommended Ban
```

---

# 60. Macro Planner Dashboard

```text
DRAFT → MACRO PLAN

OUR COMPOSITION

DS       Hero A
JUNGLE   Hero B
MID      Hero C
ROAM     Hero D
ADC      Hero E

WIN CONDITION

★ Early Objective
★ Mid-Jungle Pressure
★ 3-Man Rotation

EARLY PLAN

ROAM → MID
MID → RIVER
JG → MID / RIVER
ADC → FARM
DS → HOLD

PRIMARY PLAN
MID + JG + ROAM → DRAGON

SECONDARY PLAN
JG + DS PRESSURE

EMERGENCY PLAN
CROSS-MAP TRADE
```

---

# 61. Replay

```text
Video Player
+
Macro Timeline
+
Map Overlay
+
Player Paths
```

สามารถ:

```text
Pause
Play
Jump to Event
Toggle Player
Toggle Team
Toggle Path
Toggle Heatmap
```

---

# 62. Data Quality

ทุก Observation ต้องมี:

```text
confidence
source
visible
```

ทุก Event ต้องมี:

```text
confidence
evidence
```

ควรแยก:

```text
OBSERVED
INFERRED
UNKNOWN
```

---

# 63. Evaluation

## Computer Vision

```text
Precision
Recall
F1
Pixel Error
Coordinate Error
Track Continuity
Identity Switch
```

## Macro

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

# 64. Dataset Strategy

เริ่ม:

```text
10–20 Matches
```

ครอบคลุม:

```text
Early
Mid
Late
Normal Movement
Gank
Objective
Teamfight
```

แล้วเพิ่ม:

```text
50
100
500+
```

---

# 65. Human-in-the-loop

ระบบต้องมี:

```text
AI Detection
↓
Human Review
↓
Confirm / Reject / Edit
↓
Ground Truth
↓
Dataset
↓
Retrain
```

---

# 66. Algorithm Hierarchy

ต้องใช้ให้ถูกงาน:

```text
OpenCV
↓
Tracking Algorithm
↓
Rule Engine
↓
Statistics
↓
Machine Learning
↓
LLM
```

## OpenCV

```text
Crop
Image Processing
Position
```

## Tracking

```text
Identity
Movement
```

## Rule Engine

```text
Rotation
Objective
Macro Plan
```

## Statistics

```text
Counter
Synergy
Win Rate
Pattern
```

## ML

```text
Prediction
Classification
Probability
```

## LLM

```text
Summary
Explanation
Natural Language
```

LLM ไม่ควรเป็นแหล่งสร้างข้อมูลดิบ

---

# 67. Development Roadmap Final

## Phase 1 — Vision Foundation

```text
Video
→ Minimap
→ Icon
→ X/Y
```

## Phase 2 — Tracking

```text
Icon
→ Hero
→ Player
→ Tracking
```

## Phase 3 — Map

```text
X/Y
→ Coordinate
→ Zone
→ Path
→ Heatmap
```

## Phase 4 — Event

```text
Rotation
Grouping
Gank
Objective
Teamfight
Death
```

## Phase 5 — Analytics

```text
Player
Team
Heatmap
Timeline
Comparison
```

## Phase 6 — Draft Foundation

```text
Hero DB
Pick
Ban
Simulator
```

## Phase 7 — Counter

```text
Matchup
Counter
Synergy
Composition
```

## Phase 8 — Macro Planner

```text
Draft
→ Win Condition
→ Macro Rules
→ Primary
→ Secondary
→ Emergency
```

## Phase 9 — Scouting

```text
Player
Team
Draft
Macro
```

## Phase 10 — AI / ML

```text
Historical Data
→ Prediction
→ Recommendation
```

---

# 68. Milestones

## M1

```text
Video → Minimap → Icon
```

## M2

```text
Icon → Hero → Tracking
```

## M3

```text
Tracking → Map → Heatmap
```

## M4

```text
Heatmap → Macro Events
```

## M5

```text
Macro → Player / Team Profile
```

## M6

```text
Draft → Counter / Synergy
```

## M7

```text
Draft → Macro Plan
```

## M8

```text
Actual vs Recommended
```

## M9

```text
Scouting
```

## M10

```text
ML / AI
```

---

# 69. Final End-to-End Workflow

```text
                           MATCH VIDEO
                                │
                                ▼
                         VIDEO INGESTION
                                │
                                ▼
                      BROADCAST PARSER
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
           MINIMAP           SIDE HUD          MAIN VIEW
              │                 │                 │
              ▼                 ▼                 ▼
           POSITION           IDENTITY          EVENTS
              │                 │                 │
              └─────────────────┼─────────────────┘
                                ▼
                         OBSERVATION DB
                                │
                                ▼
                          EVENT ENGINE
                                │
                                ▼
                         MACRO ANALYTICS
                                │
                  ┌─────────────┴─────────────┐
                  ▼                           ▼
              PLAYER PROFILE              TEAM PROFILE
                  │                           │
                  └─────────────┬─────────────┘
                                ▼
                            SCOUTING


                              DRAFT
                                │
                  ┌─────────────┼─────────────┐
                  ▼             ▼             ▼
               COUNTER       SYNERGY      COMPOSITION
                  │             │             │
                  └─────────────┼─────────────┘
                                ▼
                         WIN CONDITION
                                │
                                ▼
                         MACRO PLANNER
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
                 PRIMARY     SECONDARY   EMERGENCY
                    │
                    ▼
                   GAME
                    │
                    ▼
              VIDEO ANALYSIS
                    │
                    ▼
              ACTUAL MACRO
                    │
                    ▼
             PLAN VS ACTUAL
                    │
                    ▼
                INSIGHT
                    │
                    ▼
              NEXT DRAFT
```

---

# 70. กฎสำคัญของการพัฒนา

1. ห้ามเริ่มจาก UI ก่อน Vision
2. ห้ามเริ่ม Train AI ใหญ่ก่อนมี Ground Truth
3. ห้ามให้ LLM สร้างข้อมูลดิบ
4. ห้ามรวม Observed กับ Inferred
5. ห้ามรวมสถิติคนละ Patch
6. ห้ามใช้ Counter แบบไม่มี Context
7. ห้ามสร้าง Macro Rule แบบสูตรตายตัวทุกเกม
8. ทุก Recommendation ต้องมีเหตุผลจาก Data / Rule / Statistics
9. Raw Data ต้องเก็บไว้เสมอ
10. ทุก Model ต้องมี Version
11. ทุก Analysis ต้องรู้ว่าใช้ Model/Rule Version ไหน
12. ทุก Macro Plan ต้องสามารถตรวจสอบย้อนกลับไปยัง Rule และ Source ได้

---

# 71. Master Prompt สำหรับ AI Coding Agent

```text
You are a senior software architect, computer vision engineer, backend engineer, data engineer, esports analytics engineer, and full-stack developer.

We are building a RoV Esports Analytics & Draft Intelligence Platform.

PROJECT CONTEXT

The system analyzes RoV matches from Broadcast / Spectator View video files. We do NOT depend on direct game API access.

The system must detect players from the minimap, identify heroes and player identities, track movement, convert positions into map coordinates, detect macro events, analyze player/team macro behavior, simulate drafts, analyze hero counters and synergies, and recommend macro plans based on the current draft and game state.

The system must be developed incrementally, one system at a time.

CORE MODULES

Video:
- Video Ingestion
- Broadcast Layout Parser
- Minimap Vision
- Hero Identification
- Player Identity
- Player Tracking
- Map Calibration
- Map / Zone Engine
- Ground Truth / Annotation
- Event Detection
- Macro Analytics
- Heatmap
- Player Analytics
- Team Analytics

Draft:
- Draft Simulator
- Pick Engine
- Ban Engine
- Counter Engine
- Matchup Engine
- Synergy Engine
- Composition Engine
- Draft Score Engine
- Patch / Meta Engine
- Draft Recommendation
- Player-specific Draft
- Team-specific Draft

Macro Planning:
- Macro Knowledge Base
- Macro Rule Engine
- Macro Planner
- Primary Plan
- Secondary Plan
- Emergency Plan
- Decision Tree
- Actual vs Recommended

Intelligence:
- Scouting
- Prediction / ML
- Dataset Management
- Model Versioning
- Data Versioning

INFRASTRUCTURE

- PostgreSQL / Supabase
- FastAPI
- Next.js
- TypeScript
- Tailwind CSS
- OpenCV
- NumPy
- Scikit-learn initially
- PyTorch / YOLO only when justified by data

ARCHITECTURE PRINCIPLE

Use this hierarchy:

OpenCV
→ Tracking Algorithm
→ Rule Engine
→ Statistics
→ Machine Learning
→ LLM

Do not use an LLM as the source of raw match data.

VIDEO PRINCIPLE

The input is Broadcast / Spectator View video.

Minimap is the primary source for player position.
Side HUD is used for player / hero identity.
Main View is used for combat and event evidence.

Always distinguish:
- OBSERVED
- INFERRED
- UNKNOWN

Never turn an inferred state into ground truth.

MINIMAP STRATEGY

Start with:
- fixed/calibrated ROI
- crop
- preprocessing
- color / contour / circle detection
- template matching

Only use custom object detection if traditional CV is insufficient.

Use Draft information to constrain Hero Identification to the 10 heroes in the current match when possible.

TRACKING

Maintain:
- player_id
- hero_id
- team_id
- role
- timestamp
- x
- y
- visible
- confidence
- source

Identity Switch is a critical error.

MAP

Normalize coordinates into:
X = 0.00–1.00
Y = 0.00–1.00

Then map coordinates into polygon zones.

EVENTS

Support:
- Rotation
- Grouping
- Gank
- Objective Setup
- Objective Contest
- Objective Taken
- Objective Lost
- Teamfight
- Death
- Respawn
- Recall
- Lane Swap
- Split Push

Every event should include:
- start_time
- end_time
- event_type
- team
- players
- zone/location
- confidence
- evidence/metadata

MACRO ANALYTICS

Macro analysis is:
Movement
→ Pattern
→ Behavior
→ Insight

Do not make strategic claims without metrics or rules behind them.

DRAFT

Draft must maintain an explicit state machine.

Support:
- Pick
- Ban
- Timer
- Undo
- Reset
- Skip
- History
- Notes
- Search
- Role Filter
- Side Swap

COUNTER

Separate:
- 1v1 Counter
- Lane Counter
- Teamfight Counter
- Composition Counter

Do not reduce Counter to a generic “Hero A beats Hero B” statement without context.

DRAFT SCORING

Initial configurable scoring:
Counter       × 0.30
Synergy       × 0.25
Role Balance  × 0.15
Early Game    × 0.10
Late Game     × 0.10
Objective     × 0.10

This is a decision score, not automatically a real-world win probability.

MACRO PLANNER

Macro Analyzer answers:
“What happened?”

Macro Planner answers:
“What should we do?”

Planner pipeline:
Draft
→ Hero Characteristics
→ Team Composition
→ Matchups
→ Win Condition
→ Objective Priority
→ Macro Rules
→ Macro Plan

The planner must support:
- Primary Plan
- Secondary Plan
- Emergency Plan
- Dynamic decision trees

Do not use universal rules like:
“Roam must always go Mid.”

Rules must consider:
- Hero composition
- Lane / wave state
- Power spikes
- Objective state
- Vision
- Player state
- Enemy state
- Patch

MACRO KNOWLEDGE BASE

Each rule should store:
- rule_id
- name
- phase
- conditions
- action
- priority
- patch
- source
- confidence
- notes

Never fabricate strategic knowledge. Mark assumptions clearly.

ACTUAL VS RECOMMENDED

Compare the recommended macro plan with what actually happened in the video.

Do not assume any deviation is automatically bad. Provide context and evidence.

DATA LAYERS

Layer 1: RAW VIDEO
Layer 2: OBSERVATION
Layer 3: EVENT
Layer 4: ANALYTICS
Layer 5: INSIGHT

Never overwrite raw observations with insights.

PROCESSING

Video processing must be asynchronous:

Frontend
→ API
→ Job
→ Queue
→ Worker
→ Processing
→ Database

Do not process long videos synchronously in a normal API request.

DEVELOPMENT METHOD

Build one system at a time.
Do not implement the entire platform at once.

Recommended order:

1. Video Ingestion
2. Broadcast / Minimap Calibration
3. Minimap Icon Detection
4. Hero Identification
5. Player Identity
6. Tracking
7. Map / Zone
8. Ground Truth / Annotation
9. Event Detection
10. Macro Analytics
11. Player / Team Analytics
12. Draft Simulator
13. Counter / Matchup / Synergy / Composition
14. Macro Planner
15. Actual vs Recommended
16. Scouting
17. ML / AI

WHEN IMPLEMENTING A SYSTEM

Before writing code:
1. Explain the system boundary.
2. Show the folder structure.
3. Define inputs and outputs.
4. Define data structures.
5. Define algorithm.
6. Define workflow.
7. Define API.
8. Define database changes.
9. Define tests.
10. Define acceptance criteria.

Then implement only that system.

Do not implement unrelated or future systems unless explicitly requested.

QUALITY RULES

- Keep code understandable and maintainable.
- Prefer simple algorithms before complex AI.
- Add validation and error handling.
- Add unit and integration tests where appropriate.
- Do not fabricate sample statistics as real statistics.
- Clearly label mock/demo data.
- Preserve raw data.
- Support versioning.
- Make recommendations explainable.
- Keep patch context explicit.

FIRST TARGET

Start with Video Ingestion.

After that, implement Minimap Calibration and Icon Detection.

The first measurable computer vision goal is:

Broadcast Video
→ Crop Minimap
→ Detect Candidate Hero Icons
→ Return X/Y coordinates
→ Draw detections on the minimap

Do not begin Macro Planner, Draft AI, or ML prediction until the position pipeline has a working prototype.
```

---

# 72. Prompt สำหรับสั่ง AI ให้ทำทีละระบบ

```text
Implement the next system only.

SYSTEM:
[ระบุชื่อระบบ]

OBJECTIVE:
[เป้าหมาย]

INPUT:
[ข้อมูลเข้า]

OUTPUT:
[ข้อมูลออก]

ALGORITHM:
[วิธีการ]

DATABASE:
[ตารางที่เกี่ยวข้อง]

API:
[Endpoint]

WORKFLOW:
[ขั้นตอน]

ACCEPTANCE CRITERIA:
[เงื่อนไขผ่าน]

CONSTRAINTS:
- Do not implement future systems.
- Do not add unrelated features.
- Keep implementation simple.
- Preserve the architecture in the master project prompt.
- Do not fabricate data.
- Add tests.
- Provide sample input/output.
- Provide run instructions.
```

---

# 73. Prompt เริ่มระบบแรก: Video Ingestion

```text
Implement System 1: Video Ingestion.

Goal:
Create a minimal service that accepts a RoV broadcast MP4 video and extracts metadata.

Requirements:
- Accept MP4 upload
- Read width
- Read height
- Read FPS
- Read duration
- Generate match_id
- Generate video_id
- Create processing job
- Save metadata to PostgreSQL
- Return processing status

Use:
- Python
- FastAPI
- OpenCV
- PostgreSQL

Do not implement:
- Minimap detection
- Hero detection
- Tracking
- Macro
- Draft
- AI

Create:
1. Folder structure
2. Database tables
3. API
4. Service
5. Repository
6. Validation
7. Error handling
8. Tests
9. Sample request
10. Sample response
11. Run instructions

Acceptance:
Uploading a valid MP4 creates a Match, Video, and Processing Job and returns their IDs.
```

---

# 74. Final Principle

ระบบนี้มีเป้าหมายไม่ใช่เพียง “จับผู้เล่นบน Minimap” หรือ “บอกตัวแพ้ทาง” แต่ต้องสร้างวงจร:

```text
DRAFT
↓
MACRO PLAN
↓
GAMEPLAY
↓
VIDEO ANALYSIS
↓
ACTUAL MACRO
↓
PLAN VS ACTUAL
↓
SCOUTING / INSIGHT
↓
NEXT DRAFT
```

ทุกคำแนะนำควรสามารถย้อนกลับไปหา:

```text
Data
→ Rule
→ Source
→ Patch
→ Analysis Version
```

เพื่อให้ระบบสามารถตรวจสอบ อธิบาย และพัฒนาต่อได้
