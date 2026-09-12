# 37 — Series Identity & Global Ban-Pick Spec

PHASE M2A.5 · STEP 3 · 2026-09-12 · **corrected domain model** · audit: [docs/36](36-series-identity-audit.md)

แก้ correctness bug: series history / Global Ban-Pick ผูกกับ **side** ไม่ใช่ **team identity**
(docs/36 §4) · **correctness เท่านั้น — ไม่แตะ weights / scoring / clean-window / กติกาใหม่**

---

## 1. หลักการ

- **Side** (BLUE/RED) มีอายุแค่ **หนึ่งเกม**
- **TeamIdentity** คงที่ข้ามซีรีส์ · **id คงที่ ≠ display_name ที่แก้ได้**
- **`GameRecord[]` เป็น source of truth เดียว (immutable)** · ทุกอย่างอื่น derive จากมัน
- lock/score ทุกอย่าง key ด้วย **team_id** ไม่ใช่ side

---

## 2. Domain model

```
TeamIdentity
  id: str            # เสถียร ไม่เปลี่ยน (เช่น "TEAM_A"/"TEAM_B" สำหรับ manual · หรือ team id จากข้อมูลแข่ง)
  display_name: str  # แก้ได้ ใช้แสดงผลเท่านั้น — เปลี่ยนแล้วห้ามขยับ history/wins/locks/scouting

GameSideAssignment
  blue_team_id: str
  red_team_id: str
  team_for_side(side) -> team_id
  side_for_team(team_id) -> Team | None
  swapped() -> GameSideAssignment          # blue<->red · ไม่แตะอย่างอื่น

GameRecord            # IMMUTABLE (frozen) — บันทึกแล้วห้ามเขียนทับ
  game_no: int
  assignment: GameSideAssignment           # snapshot ของเกมนั้น
  blue_picks, red_picks: tuple[str,...]
  blue_bans, red_bans: tuple[str,...]
  winner_team_id: str | None               # ★ เก็บเป็น team_id ไม่ใช่ "blue"/"red"
  picks_of(team_id) -> tuple                # ใช้ assignment แปลง side->identity
  won_by(team_id) -> bool

SeriesState
  teams: dict[team_id, TeamIdentity]
  games: list[GameRecord]                   # canonical, immutable records
  current_assignment: GameSideAssignment | None
  best_of: int | None
  heroes_used_by(team_id) -> set[str]        # derived จาก games
  wins_of(team_id) -> int                    # derived จาก games
  game_no() -> int · is_final_game() -> bool
  locked_heroes_for(team_id, fmt) -> set[str]  # ใช้กติกา GBP ของ fmt

DraftState            # หนึ่งเกมที่กำลังดราฟต์
  fmt, pool, moves ...
  sides: GameSideAssignment | None
  series: SeriesState | None
  locked_by_series(side) = series.locked_heroes_for(sides.team_for_side(side), fmt)
```

**ไม่มี SeriesHeroHistory เป็น store แยก** — `heroes_used_by()` เป็น derived view จาก `games[]`
เท่านั้น (แก้ correction #2: ไม่มี source of truth ที่ mutate ได้สองที่)

---

## 3. Lock resolution flow

```
recommend ต้องรู้ locks ของตาปัจจุบัน (side S)
  → DraftState.sides.team_for_side(S)      = team_id
  → DraftState.series.locked_heroes_for(team_id, fmt)
      → ถ้า GBP ปิด หรือ reset_on_final_game & is_final_game → ∅
      → scope own_team_only → heroes_used_by(team_id)
      → scope both_teams    → ∪ heroes_used_by(ทุกทีม)
```

`legal_moves()` / `why_illegal()` เรียก `locked_by_series(turn.team_enum)` เหมือนเดิม —
เปลี่ยนแค่ **ข้างใน** ให้ resolve ผ่าน identity

---

## 4. Invariants (บังคับด้วยเทสต์ · STEP 7)

1. history follows **team_id** ไม่ใช่ side
2. เปลี่ยน `display_name` ไม่ขยับ history/locks/wins
3. `swap(swap(assignment)) == assignment`
4. side swap ห้าม mutate `GameRecord` เก่าใด ๆ (records เป็น frozen)
5. ถ้า Team A ใช้ hero X → X ผูกกับ A ทุก side assignment ถัดไป
6. Team B ไม่รับ locks ของ Team A
7. series wins follow team_id
8. replay ซีรีส์เดิม → locks เดิม ไม่ว่าจะแสดง side ไหน
9. **Python และ JS ตรงกัน**: team identity · side assignment · used heroes · current locks · series score

> **Permanent invariant (เพิ่มใน [[.ai/DECISIONS.md]]):** a recorded game is immutable —
> its blue/red identities, picks↔identity, และ winner_team_id ห้ามเปลี่ยน · "swap sides"
> แก้ได้เฉพาะ assignment ของเกมปัจจุบัน/ถัดไป

---

## 5. Global Ban-Pick — คงกติกาเดิม

ไม่ infer กติกาใหม่ · คง `enabled / scope / applies_to_bans / reset_on_final_game`
จาก `configs/draft/format.yaml` · **ห้ามแก้ `reset_on_final_game` เพื่อลบ violation**

### 5.1 การจำแนก 8 violations (docs/36 §2.3 · investigate ก่อน ไม่แก้กติกา)

| ซีรีส์ | เกม | จำแนก |
|---|---|---|
| `bac vs bru` (Bo7) | reuse ทั้งหมดในเกม 7 (= best_of) | ✅ **final-game reset** — ถูกกติกา · check ยังไม่หัก reset |
| `hd vs bac` (ต.ค. 2025) | reuse กลางซีรีส์ (g1→g3→g5) | ⚠️ คนละฤดูกาล/อีเวนต์ · own-team GBP ไม่ผูก · **unresolved (event rule)** |
| `godji check vs bac` (BoNone) | g1→g4 | ⚠️ **unresolved** (best_of ไม่ parse · อาจเป็นสเตจที่ไม่ใช้ GBP) |
| `bmg vs one` (BoNone) | g1→g4 | ⚠️ **unresolved** |

ทั้งหมด **ไม่ได้เกิดจากบั๊ก side/identity** — การจับคู่ identity อ่านถูก (เช่น `bac marja`
g3-blue→g4-red ผูกกับ bac ทั้งสอง side ถูกต้อง) → ยืนยันว่า identity pairing ทำงาน
`global_ban_pick_check()` จะเพิ่มโหมดหัก final-game เพื่อแยก legit reset ออกจาก unresolved

---

## 6. Real-data fixtures (committed · STEP 6)

distill จาก series จริงที่ parse แล้ว → commit เป็น JSON (ไม่พึ่ง `data/cache/` ที่ gitignore)
แต่ละ fixture บันทึก provenance (tournament · series · game numbers · source ids ถ้ามี)

ต้องมีเคส:

| เคส | รูปแบบ | series ตัวอย่างจริง |
|---|---|---|
| A | team RED → BLUE | fs (godji check series) |
| B | team BLUE → RED | fs g1→g2 |
| C | side เดิมต่อเนื่อง | hd red g2→g3 |
| D | non-parity pattern | hd blue,red,red,blue |
| E | multi-game | fs vs godji check (Bo5) |

เทสต์ต้องพิสูจน์ side มาจาก **assignment จริงของแต่ละเกม** ไม่ใช่ parity ของเลขเกม

---

## 7. Python / JS parity (STEP 9)

JS ไม่มี runtime ในเทสต์ (test_web_board.py ใช้ regex + re-simulate ใน Python)
parity จึงทำแบบเดียวกับ `test_js_and_python_agree_on_a_real_composition`:

1. golden series vector (จาก fixture · มี side swap)
2. คำนวณ locks/wins ด้วย `SeriesState` ตัวจริง
3. re-simulate อัลกอริทึม lock ฝั่ง JS ใน Python (mirror template) แล้วเทียบ
4. regex guard ว่า template มี logic identity-based จริง (ไม่ใช่ side-based)

`test_series_state_is_derived_not_duplicated` เดิม assert บรรทัด `winsOf` แบบ side —
ต้อง migrate เป็น identity (`winsOf(teamId)` filter `winner_team_id`)

---

## 8. Legacy `series_used`

**ลบทิ้ง** — ไม่เก็บ shim · migrate 5 เทสต์ (`test_draft_state.py`) + 1 (`test_ban_intelligence.py`)
ให้สร้าง state ผ่าน `SeriesState`/`GameSideAssignment` · ถ้าจำเป็นต้องมี migration shim
ให้ mark deprecated + เพิ่ม migration test + ลบเมื่อ caller ย้ายครบ (แต่เป้าหมายคือลบเลย)

---

## 9. Benchmark — series-aware replay analysis (STEP · correctness ไม่ใช่ tuning)

benchmark ปัจจุบัน replay ทีละเกมอิสระ ไม่ populate series locks → ไม่สร้าง candidate pool
แบบ Global Ban-Pick · **งานเฟสนี้: วิเคราะห์อย่างเดียว ไม่เปลี่ยน headline number**

รายงาน: ถ้า replay แบบ series-aware (identity-correct) จะมีกี่ตาที่ legal candidate pool
**ต่างไปจากเดิม** (ตาที่ถูก lock เพิ่มเพราะทีมนั้นใช้ฮีโร่ไปแล้วในเกมก่อนของซีรีส์)
→ ตัวเลขนี้บอกขนาดของ correctness gap · ไม่แก้ fixture snapshot ในเฟสนี้

---

## 10. ไม่ทำ

- ไม่แตะ Counter/Synergy/Composition · ไม่ tune weights · ไม่ใช้ clean-window
- ไม่ infer side rules · ไม่แก้ `reset_on_final_game`
- ไม่เปลี่ยน recommendation ranking ของตาที่ไม่มี series context (เส้นเดิมต้องนิ่ง)

## 11. Deliverables

`rov/draft/series.py` (ใหม่) · `DraftState` แก้ · migrate tests · fixtures + property tests +
parity · benchmark analysis · [docs/38](38-series-identity-report.md)
