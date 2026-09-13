# 43 — Broadcast Draft Verification (Track A)

PHASE M2A.6A · Track A · 2026-09-13 · **verification จาก broadcast footage · ไม่แก้ engine / weights / benchmark**

ยืนยัน draft sequence + turn clock จากคลิปแข่งจริง · แยก **VERIFIED (RPL 2026 Winter Regular Season)**
ออกจาก **UNRESOLVED** อย่างเคร่งครัด · scope ของ config ดู [docs/40 §4](40-global-ban-pick-rule-audit.md) · **ไม่อ้างว่าเป็น timing มาตรฐานของ RoV ทั้งหมด**

---

## 1. Broadcast source record (provenance)

| field | ค่า |
|---|---|
| primary video | `data/videos/tenvshd_draf_gameplay2.mp4` (draft + gameplay) |
| match | **TEN vs HD** |
| game | **Game 2** (series score 1–0 ตอน draft) |
| stage | **RPL 2026 Winter · Regular Season** · Bo5 |
| overlay label | "PRO LEAGUE 2026/WINTER" · "REGULAR SEASON : TEN VS HD : GAME 2 [BO5]" |
| corroborating video | `data/videos/gjcvsbrugameplay1.mp4` — **GJC vs BRU · Game 1** · RPL 2026 Winter Regular Season · Bo5 (**ใช้ยืนยัน clock เท่านั้น**) |
| ตรวจเพิ่ม (ban1) | `gjcvsbrugameplay2.mp4` (GJC G2) |
| resolution / fps | 1280×720 · 60 fps |

> วินาที (t) ทั้งหมดในเอกสารนี้อ้างอิง **เวลาในไฟล์วิดีโอ (clip-relative)** · draft อยู่ช่วงต้นคลิป

### 1.1 Independent BLUE / RED identification (ไม่ circular)

- **TEN = BLUE (ฝั่งซ้าย)** · **HD = RED (ฝั่งขวา)**
- วิธี: **in-game HUD health-bar colors** (`ingame_430.jpg`) — ฮีโร่ฝั่ง HD มีแถบเลือดสีแดง = red side · TEN อยู่ซ้าย = blue
- corroborate: convention ของ broadcast (ซ้าย = blue / ขวา = red) + ป้ายชื่อผู้เล่นบน overlay
  (blue: SRV EREZ FAKEPLAYZ MOOP DIFOXN · red: ACAPAE WONDERWALL BARELY COMMIW POSSU)
- **ไม่ได้อนุมานจากลำดับ draft ที่กำลังตรวจ** — side identity มาจาก UI cue อิสระ

---

## 2. VERIFIED — RPL 2026 Winter Regular Season เท่านั้น

| item | ค่า | หลักฐาน |
|---|---|---|
| bans_per_team | **4** | ban row เต็ม 4 ช่องต่อฝั่ง (`th_ban_151`) · ตรงข้อมูล 861 เกม |
| picks_per_team | **5** | pick row เต็ม 5 ช่องต่อฝั่ง |
| phase structure | ban1 → pick1 → ban2 → pick2 | ลำดับเฟสตรงกับ format.yaml |
| **Pick 1 sequence** | **B R R B B R** | prior-session (hero portrait fill order) · ป้ายผู้เล่น `th_full_35/50/65` |
| **Ban 2 sequence** | **R B R B** | **fully observed session นี้** (§2.1) |
| **Pick 2 sequence** | **R B B R** | prior-session (hero portrait fill order) |
| **BAN turn clock (nominal)** | **40 วินาที** | reset → 00:40 (§2.2) |
| **PICK turn clock (nominal)** | **60 วินาที** | reset → 01:00 (§2.2) |
| post-draft countdown | **~60s แยกต่างหาก** จาก turn timer | หลัง pick2 มี pre-game countdown คนละตัวกับนาฬิกาต่อตา |

### 2.1 Ban 2 = R B R B — fully observed

ทุกตาเห็นทั้ง **cyan active-slot highlight บน ban bar** และ **timer reset** ตรงกัน (cross-confirm):

| ตา | ฝั่ง (team) | ช่วง t (คลิป) | หลักฐาน ban bar | timer reset |
|---|---|---|---|---|
| ban2-1 | **RED** (HD) | t≈62–88 | `th_ban2t1_74..86` — cyan บน cluster ขวา (Red แบนตัวที่ 3) | เริ่ม 00:40 |
| ban2-2 | **BLUE** (TEN) | t≈88–115 | `th_ban_089` — cyan บน cluster ซ้าย slot3 | reset 00:39 @ t≈89 |
| ban2-3 | **RED** (HD) | t≈115–135 | `th_ban_116` — cyan บน cluster ขวา | reset 00:39 @ t≈116 |
| ban2-4 | **BLUE** (TEN) | t≈135–150 | `th_ban_137` — cyan บน cluster ซ้าย slot4 · จบ `th_ban_151` | reset 00:39 @ t≈136 |

→ **R B R B** ตรงกับ `format.yaml` sequence เฟส 2 (ban) ทุกตา

### 2.2 Turn clock — measured resets

ลำดับ timer (MM:SS) จับหนา ๆ รอบ transition · reset = ตัวเลขกระโดดขึ้นเมื่อขึ้นตาใหม่:

**TEN vs HD** (`th_tmr_pick1a/b`, `th_tmr_ban2a/b`):

| phase | เห็น reset ที่ (t) | ค่าเริ่ม | สรุป |
|---|---|---|---|
| PICK 1 | t≈20 · t≈32 (00:59@33) · t≈50 (00:59@51) | **01:00** | pick = 60s (≥3 reset) |
| PICK 2 | t≈150 (00:59@151) | **01:00** | pick = 60s |
| BAN 2 | t≈88 (00:39) · t≈115 (00:39) · t≈135 (00:39) | **00:40** | ban = 40s (≥3 reset) |

**GJC vs BRU G1** (`gjc_tmr_a/b`) — cross-match, RPL 2026 Winter เดียวกัน:

| phase | เห็น reset ที่ (t) | ค่าเริ่ม |
|---|---|---|
| PICK | t≈79 (00:56@80) · t≈98 (00:58@100) · t≈155 (00:57@156) | **01:00** |
| BAN | t≈178 (00:38@180) | **00:40** |

→ **ban = 40s · pick = 60s** · ผ่านมาตรฐานหลักฐาน (≥2 reset ต่อเฟส · 2 แมตช์) ·
`reserve = 0` ไม่มีหลักฐานขัด (reset สะอาดกลับค่าเต็มทุกครั้ง) ·
"drop" 50→39 ช่วง t≈60→63 = **รอยต่อเฟส pick(60s)→ban(40s)** ไม่ใช่ error

---

## 3. UNRESOLVED (ยังไม่ยืนยัน · ห้ามเดา)

| item | สถานะ | เหตุผล |
|---|---|---|
| **Ban 1 order** (B R B R?) | **UNRESOLVED** | broadcast ตัดไปกล้องผู้เล่นตอน ban1 **ทุกคลิป** → overlay ขึ้นตอน ban1 จบแล้ว (§3.1) · **นับได้ 2+2 ต่อฝั่ง แต่ลำดับดูไม่ได้** |
| **declined / no-ban `×`** | **UNRESOLVED** | `×` = ช่องแบนว่าง (เห็นเปลี่ยนเป็นรูปตอนแบน) · แต่ไม่เคยเห็นตาที่ปล่อยไม่แบน → แยก "declined" กับ "empty placeholder" ไม่ได้ |
| **timing นอก RPL 2026 Winter** | **UNRESOLVED** | มีคลิปแค่ RPL 2026 Winter · RPL 2026 Summer / RPL 2025 Winter / GCS Spring / GCS Summer **ไม่มี footage** → ห้าม assume 40/60 |

### 3.1 ทำไม Ban 1 ดูไม่ได้ (off-overlay pattern)

| clip | ช่วงกล้องผู้เล่น (ไม่มี overlay) | overlay ขึ้นครั้งแรก | สถานะ ban row ตอน overlay ขึ้น |
|---|---|---|---|
| TEN-HD G2 | t≈1–8 | t≈12 | **frozen Blue 2 / Red 2** (ban1 จบแล้ว) |
| GJC-BRU G1 | t≈2–69 | t≈70 | **frozen Blue 2 / Red 2** |
| GJC-BRU G2 | t≈3–65 | — | กล้องผู้เล่นตลอดช่วง ban1 |

→ เป็น **production pattern สม่ำเสมอ**: ban phase 1 เกิดตอนกล้องจับผู้เล่น · overlay ขึ้นสำหรับ pick phase 1 เป็นต้นไป
· **ban1 order จับจาก broadcast เหล่านี้ไม่ได้** (ต้องการ source อื่น เช่นคลิปที่โชว์ overlay ตั้งแต่ต้น)

---

## 4. Config scope (สรุป · รายละเอียด audit ใน report)

- `configs/draft/format.yaml` (`id: rpl_2026`, "RPL / GCS มาตรฐาน") เป็น **config เดียวใช้ร่วมทั้ง 5 รายการ**
  (KNOWN_TOURNAMENTS) · web board ใช้ `turn_clock` ก้อนเดียว (`CLOCK` ใน `draft_board.tpl.html`)
- หลักฐาน Track A มาจาก **RPL 2026 Winter อย่างเดียว** → **ไม่มี per-competition/stage override ในระบบตอนนี้**
  (layer นั้นเป็น M2A.6B · [docs/40 §4](40-global-ban-pick-rule-audit.md))
- ผล: **ยังไม่ตั้ง shared `turn_clock.verified: true`** และ**ไม่เปลี่ยนค่า 30→40/60 ในค่ากลาง**
  (จะกลายเป็นการเอา timing ของ RPL Winter ไปทับ GCS/ฤดูอื่นโดยเงียบ ๆ) ·
  **บันทึกค่า measured (ban 40 / pick 60) ไว้เป็น override รอ competition config layer** — comment ใน format.yaml ชี้มาที่เอกสารนี้
- `turn_clock` **ไม่ถูกอ่านโดย recommend/benchmark/DraftState** — มีผลแค่ตัวเลขนาฬิกาบนกระดานเว็บ ·
  การไม่แก้ค่าจึงไม่กระทบ ranking/score ใด ๆ

---

## 5. เฉพาะที่ทำใน Track A

- **ยืนยัน**: pick1 (B R R B B R) · ban2 (R B R B) · pick2 (R B B R) · phase structure · ban 40s · pick 60s
  · post-draft countdown แยก — **เฉพาะ RPL 2026 Winter Regular Season**
- **ค้าง**: ban1 order · declined `×` · timing รายการอื่น
- **format.yaml sequence values ตรงกับทุกเฟสที่ดูได้อยู่แล้ว → ไม่แก้** · overall `verified` ยัง false เพราะ ban1 ยังไม่ยืนยัน
  (เฟสเดี่ยวเป็น VERIFIED ได้ แต่ complete sequence ยัง UNVERIFIED)
