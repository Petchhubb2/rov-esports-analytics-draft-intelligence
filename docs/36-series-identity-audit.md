# 36 — Series Identity & Global Ban-Pick Audit

PHASE M2A.5 · STEP 1-2 · 2026-09-12 · **audit + verify กับข้อมูลจริง · ยังไม่แก้ implementation**

โจทย์: สงสัยว่าระบบผูก series history / Global Ban-Pick กับ **BLUE/RED side** แทน
**stable team identity** → เมื่อ BO3/BO5 สลับฝั่ง อาจ lock ฮีโร่ผิดทีม

> RULE 0 — ไม่เดา · ทุกข้อสรุปในเอกสารนี้ trace จากโค้ดจริงและข้อมูลแข่งจริง 305 ซีรีส์

---

## 1. สรุปคำตัดสิน

**สมมติฐานถูกในระดับ model** — runtime ทั้งฝั่ง Python (`DraftState`) และ Web (JS) เก็บ
series history โดย **key = side (BLUE/RED)** ไม่ใช่ team identity · **แต่** ผลกระทบจริงถูกจำกัด
ด้วยเงื่อนไขเฉพาะ (ดู §7) ตรรกะที่ถูกต้อง (key = identity) มีอยู่ **ที่เดียว** คือ method
ตรวจสอบใน importer (`SeriesDraft.global_ban_pick_check`) ซึ่ง **ไม่ได้** ต่อเข้ากับ path
ที่ใช้แนะนำจริง

---

## 2. หลักฐานจากข้อมูลจริง (STEP 2)

trace: `scripts`-style script รันบน cache 305 ซีรีส์ (Liquipedia RPL/GCS 2026)

| ตัวชี้วัด | ค่า |
|---|---|
| ซีรีส์ทั้งหมด | 305 |
| best_of ที่ parse ได้ | Bo5 = 39 · Bo7 = 17 · **None = 249** (best_of หายบ่อย — §8) |
| **side สลับข้ามเกม** | **197** |
| side คงเดิมทุกเกม | 100 |
| side กำกวม/ขาดข้อมูล | 8 |
| swap ที่เป็น strict odd/even | **27 / 197** (อีก 170 ไม่ใช่) |
| Global Ban-Pick violation (key=identity) | **8 ใน 4/305 ซีรีส์** |

### 2.1 identity คงที่ · side เปลี่ยนได้ (ตัวอย่างจริง)

```
fs vs godji check (Bo5):  t1(fs)  = blue, red,  blue        → fs อยู่ทั้งสองฝั่ง
solyx vs bac:             t1(solyx)= blue, blue, red,  blue, blue   → red เกม 3 เกมเดียว
bru vs ea:                t1(bru) = blue, red,  blue
hd vs bac:                t1(hd)  = blue, red,  red,  blue    → red ติดกันสองเกม
```

### 2.2 ⚠️ side ไม่ผูกกับเลขเกม (odd/even)

`solyx` red เฉพาะเกม 3 · `hd` red สองเกมติด (2,3) — **พิสูจน์ว่าอนุมาน side จาก game number ไม่ได้**
(ตรงกับ `SideSelection`: เกมถัดไป "ผู้แพ้เกมก่อนเลือกฝั่ง" — ไม่ใช่สลับตายตัว · [[rov-verified-facts]])

### 2.3 กติกายึด identity จริง

violation 8 รายการ (2.6% ของซีรีส์) นับจาก **ชื่อทีม** — ต่ำมาก ยืนยันว่า (ก) กติกา Global
Ban-Pick มีจริง (ข) parser อ่านถูก · หมายเหตุ: `global_ban_pick_check` ยังไม่หัก
`reset_on_final_game` บางรายการที่เหลือจึงอาจเป็นการ reuse ที่ถูกกติกาในเกมสุดท้าย

---

### 2.4 ⚠️ แก้ denominator (M2A.6A · STEP 6)

ตัวเลข §2 (305 series · side-swap 197/100/8) นับบนหน่วย **parsed slot** — ซึ่งรวม
**706 unplayed slots (45%)** ที่ `parse_map` สร้างต่อทุก `map1..mapN` แม้ยังไม่แข่ง
(ดู [docs/39 §2](39-competition-rule-inventory.md))

- **played games จริง = 861** (parsed slots = 1,567) — เลข 861 ที่ใช้ที่อื่นถูกต้อง
- side-swap tallies ข้างบนจึงเป็น "per series บน slot" ไม่ใช่ per played game
- **ข้อสรุปเชิงคุณภาพไม่เปลี่ยน**: identity คงที่ · side ต่อเกม · ไม่ใช่ odd/even —
  พิสูจน์บน played games ใน `tests/fixtures/series_identity.json` (ใช้เฉพาะ complete games)

---

## 3. โมเดลปัจจุบัน — แยก 4 ชั้น

| ชั้น | team identity | side | series history key | ถูกไหม |
|---|---|---|---|---|
| **A. importer/parser** | `GameDraft.blue_team/red_team` (ต่อ side) · `SeriesDraft.team1/team2` (คงที่) | อ่านจริงจาก `team1side/team2side` ต่อเกม | `global_ban_pick_check()` key = **ชื่อทีม** | ✅ **ถูก** |
| **B. Python `DraftState`** | **ไม่มี** — มีแค่ `blue_name/red_name` (ข้อความแสดงผล) | `Team` enum (BLUE/RED) | `series_used: dict[Team, set]` = **by side** | ⚠️ side-keyed · inert |
| **C. Web Draft Room (JS)** | **ไม่มี** — ใช้ช่องชื่อ + blue/red เป็นสล็อต | `move.team` = "blue"/"red" ตอนเล่นเกมนั้น | `S.results[].moves[].team` = **by side** | ⚠️ ถูกเฉพาะเมื่อกดปุ่ม swap |
| **D. benchmark/replay** | ตั้ง `blue_name/red_name` จาก `blue_team/red_team` | — | **ไม่ populate `series_used`** | ⛔ series lock ไม่ทำงานเลย |

### 3.A importer/parser — ถูกต้อง

- [`parser.py:185 parse_map`](../packages/core/rov/draft/importer/parser.py) อ่าน `team1side/team2side`
  ต่อเกม แล้ว map `blue_team/red_team` ตาม side จริง — ทีมเดียวกันเป็น blue เกมนึง red เกมนึงได้
- [`parser.py:81 global_ban_pick_check`](../packages/core/rov/draft/importer/parser.py) จับคู่
  `(blue_team, blue_picks)` / `(red_team, red_picks)` แล้วสะสมใน `used` ที่ **key = ชื่อทีม**
  → per-identity ถูกต้อง · แต่เป็น **validation method** ไม่ได้ผลิต state ให้ recommend

### 3.B Python `DraftState` — side-keyed แต่ inert

- [`state.py:150`](../packages/core/rov/draft/state.py): `series_used: dict[Team, set[str]]`
- [`state.py:190 locked_by_series(team: Team)`](../packages/core/rov/draft/state.py) คืน
  `series_used.get(team)` — lookup ด้วย **side**
- ไม่มี concept team identity ใน DraftState เลย (`blue_name/red_name` เป็นแค่ label)
- **populate ที่ไหน?** เฉพาะใน unit test (`test_draft_state.py`, `test_ban_intelligence.py`)
  ที่ใส่ `series_used={Team.BLUE: {...}}` ตรง ๆ · **CLI และ benchmark ไม่เคยใส่** → lock ไม่ทำงาน
- เทสต์ที่มีตรวจแค่ "กลไก" (own locked / opponent allowed / final reset / both_teams) —
  **ไม่มีเทสต์ identity ข้าม side-swap เลย** (ช่องโหว่)

### 3.C Web Draft Room (JS) — swap re-tags ทั้งหมด · ไม่มี identity anchor

[`apps/web/draft_board.tpl.html`](../apps/web/draft_board.tpl.html)

- `S.results = [{w, moves:[{team,action,hero}]}]` — `team` = side ตอนเล่นเกมนั้น (บรรทัด ~1333)
- `lockedFor(team)` (บรรทัด ~1379) = `S.results` ทุกเกม เอา PICK ของ **side** นั้น
- ปุ่ม `⇄ สลับฝั่ง` (บรรทัด ~3339): สลับชื่อ + **rewrite `S.results` ทั้งหมด** (flip `w` และ
  flip `move.team` ทุกอัน) + flip `S.moves` → ทำให้ blue/red เป็น "สล็อตทีม" ที่ย้ายพร้อมกันทั้งชุด
- `S.swapped` (บรรทัด 1328) **ประกาศไว้แต่ไม่มีใครอ่าน** (dead state)
- ผล: **ถูกก็ต่อเมื่อผู้ใช้เปลี่ยนฝั่งด้วยปุ่ม swap** · ถ้าเปลี่ยนฝั่งด้วยการพิมพ์ชื่อทีมใหม่
  history จะยังติด side เดิม → lock ผิดทีม · และไม่มีทางโหลดซีรีส์จริง (ที่ side ต่อเกมมาจากข้อมูล) เข้ากระดานได้ถูก

### 3.D benchmark/replay — series lock ปิดสนิท

- [`draftbench.py:218 replay_draft`](../packages/core/rov/eval/draftbench.py) สร้าง `DraftState`
  ต่อ **หนึ่งเกม** · ตั้งแค่ `blue_name/red_name` · **ไม่ตั้ง `series_used`/`is_final_game`**
- fixture หนึ่ง "draft" = หนึ่งเกม ไม่มีการจัดกลุ่มเป็นซีรีส์ → benchmark **ไม่วัด** Global Ban-Pick เลย

---

## 4. Root cause

**runtime series-history model key = side ไม่ใช่ identity** ในทั้ง B (Python) และ C (JS)
ตรรกะที่ถูก (key = identity) มีเฉพาะใน A (`global_ban_pick_check`) ซึ่งเป็น validation
ไม่ได้ต่อเข้า recommend/board · ไม่มี domain type สำหรับ `TeamIdentity` / `GameSideAssignment`
/ `SeriesHeroHistory(by identity)` ใน runtime เลย

---

## 5. ทำไมยังไม่ระเบิดในโปรดักชัน (active vs latent)

| ชั้น | สถานะ | ทริกเกอร์ที่จะทำให้ผิดจริง |
|---|---|---|
| B Python | **latent** | `series_used` ว่างใน CLI/benchmark → คำแนะนำไม่ได้รับผลตอนนี้ · จะผิดถ้ามีใคร wire ซีรีส์จริงเข้า state โดยไม่ map identity |
| C JS board | **active-conditional** | ผิดถ้าเปลี่ยนฝั่งด้วยการพิมพ์ชื่อ (ไม่กดปุ่ม swap) · หรือถ้าจะโหลดซีรีส์จริงที่ side ต่อเกม |
| D benchmark | inert | series lock ไม่ทำงาน → ไม่ผิด แต่ก็ไม่ได้วัดกติกา |

> จึงเป็น **correctness bug เชิงสถาปัตยกรรม** (abstraction ผิด) มากกว่าการคำนวณผิดที่ผู้ใช้เห็นอยู่ตอนนี้
> — แต่ต้องแก้ก่อน wire series history เข้าจริง ไม่งั้นจะกลายเป็น active

---

## 6. สิ่งที่ audit นี้ **ไม่** สรุป (กันเดา)

- ไม่สรุปว่า "ทุกเกมสลับ side" — ข้อมูลค้าน (100/297 ไม่สลับ)
- ไม่สรุปว่า side มาจาก odd/even — ข้อมูลค้าน (170/197 ไม่ alternate)
- ไม่แตะ semantics ของ Global Ban-Pick (scope/applies_to_bans/reset) — ยืนยันแล้วใน [[rov-verified-facts]] คงไว้
- ไม่สรุป best_of ต่อซีรีส์จากจำนวนเกม — best_of หายบ่อย (249 None) เป็นเรื่อง data (§8 ของสเปคถัดไป)

---

## 7. คำถามกติกาที่ยังค้าง (ต้องแยกจากงานแก้โค้ด)

1. `SideSelection.later_games` = `previous_loser` ยัง `verified: false` — ยืนยันได้ด้วย rulebook/คลิป
2. `reset_on_final_game` มีผลกับ violation 8 รายการแค่ไหน (บางอันอาจถูกกติกา)
3. ซีรีส์ 8 รายการที่ side กำกวม — ข้อมูลขาด `teamNside` หรือเกมไม่ได้เล่น

---

## 8. ต่อไป (ยังไม่ทำ — รออนุมัติ)

corrected domain model (แยก `TeamIdentity` / `Side` / `GameSideAssignment` / `SeriesHeroHistory`
key=identity) จะเสนอหลัง audit นี้ · จากนั้นค่อยทำ spec (docs/37) และ implementation +
regression fixtures + property tests + Python/JS parity (docs/38) — **correctness first, ไม่แตะ weights/scoring/clean-window**
