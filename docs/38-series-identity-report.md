# 38 — Series Identity & Global Ban-Pick Report

PHASE M2A.5 · 2026-09-12 · **correctness fix — ไม่แตะ weights / scoring / clean-window / กติกา**

audit: [docs/36](36-series-identity-audit.md) · spec: [docs/37](37-series-identity-spec.md)

---

## 1. Root cause

runtime series-history model key ด้วย **side (BLUE/RED)** ไม่ใช่ **team identity** ทั้งฝั่ง
Python (`DraftState.series_used: dict[Team,…]`) และ Web (JS `S.results[].moves[].team`) ·
ตรรกะที่ถูก (key = identity) มีเฉพาะใน `SeriesDraft.global_ban_pick_check()` ซึ่งเป็น validation
ไม่ได้ต่อเข้า path ที่ใช้แนะนำ → เมื่อ BO3/BO5 สลับฝั่ง จะ lock ฮีโร่ผิดทีม

---

## 2. โมเดลเดิม → โมเดลใหม่

| | เดิม | ใหม่ |
|---|---|---|
| source of truth | side-keyed set (2 ที่ mutate ได้) | **`GameRecord[]` immutable ที่เดียว** · used/wins เป็น derived |
| team identity | ไม่มี (มีแต่ side + ชื่อแสดงผล) | `TeamIdentity(id คงที่, display_name แก้ได้)` |
| side | ปนกับ identity | `GameSideAssignment` ต่อเกม (ephemeral) |
| lock key | side | **team_id** ผ่าน side → assignment → identity |
| winner | "blue"/"red" | **winner_team_id** |

`rov/draft/series.py` (ใหม่): `TeamIdentity` · `GameSideAssignment` · `GameRecord` (frozen) ·
`SeriesState.heroes_used_by / wins_of / locked_heroes_for` (derived, key=identity)

---

## 3. Python changes

- **ใหม่** `packages/core/rov/draft/series.py` — domain model ทั้งหมด
- `packages/core/rov/draft/state.py` — `DraftState` เลิกใช้ `series_used`/`is_final_game`
  (side-keyed) เปลี่ยนเป็น `sides: GameSideAssignment` + `series: SeriesState` ·
  `locked_by_series(side)` resolve ผ่าน identity · `team_name(side)` ตามทีมที่อยู่ฝั่งนั้น
- `packages/core/rov/eval/version.py` — เพิ่ม `series.py` + `state.py` เข้า engine fingerprint
- **legacy `series_used` ลบทิ้ง** (ไม่เหลือ shim) · migrate เทสต์ 5+1 ที่ใช้มันไปเป็น identity

## 4. JS changes (`apps/web/draft_board.tpl.html`)

- `S`: เพิ่ม `names` (by team id) + `assign` (side→team id) · `results` เก็บ
  `{winnerId, assignment, moves:[{teamId,…}]}` (by identity + snapshot)
- `lockedFor(side)` → `heroesUsedBy(S.assign[side])` (identity) · `winsOf(tid)` by `winnerId`
- ปุ่ม `⇄ สลับฝั่ง` → สลับเฉพาะ `S.assign` · **ไม่ rewrite `S.results` อีกต่อไป** (invariant #4)
- ชื่อทีมแก้ได้ เก็บ by identity → เปลี่ยนชื่อไม่ขยับ history · ลบ dead flag `swapped`
- history/score/game-dots render จาก identity + assignment snapshot

## 5. Importer changes

**ไม่มี** — `parser.py` ถูกอยู่แล้ว (`parse_map` อ่าน `team1side/team2side` ต่อเกม ·
`global_ban_pick_check` key ด้วยชื่อทีม) · M2A.5 แค่เอาโมเดลที่ถูกไปใช้ใน runtime

---

## 6. Real-series fixtures ที่ใช้

`tests/fixtures/series_identity.json` (committed · distill จาก cache · ไม่พึ่ง data/cache/)
พร้อม provenance (tournament · teams · game numbers)

| series | tournament | รูปแบบ side (t1) | เคส |
|---|---|---|---|
| fs vs godji check (Bo5) | RPL 2026 Summer | blue, red, blue | A (red→blue) · B (blue→red) · E |
| solyx vs bac | RPL 2026 Summer | blue, blue, red, blue, blue | C (blue ติดกัน) · D (non-parity) · E |
| hd vs bac | RPL 2026 Summer | blue, red, red | C (red ติดกัน) · D (non-parity) · E |

เทสต์พิสูจน์ side มาจาก `GameRecord.assignment` ไม่ใช่เลขเกม (มีเคส side ติดกัน = ไม่ใช่ odd/even)

---

## 7. การจำแนก 8 GBP violations (ไม่แก้กติกา)

| series | จำแนก |
|---|---|
| bac vs bru (Bo7) — reuse ในเกม 7 | ✅ **final-game reset** ถูกกติกา (`global_ban_pick_check` ยังไม่หัก reset จึงติดธง) |
| hd vs bac (ต.ค. 2025) · godji vs bac · bmg vs one (BoNone) | ⚠️ reuse กลางซีรีส์ → **unresolved (event rule)** · อาจเป็นสเตจที่ไม่ใช้ own-team GBP |

ทั้งหมด **ไม่ได้เกิดจากบั๊ก side/identity** · identity pairing อ่านถูก · **ไม่แตะ `reset_on_final_game`**

---

## 8. Benchmark legal-pool correctness (analysis เท่านั้น · ไม่เปลี่ยน headline)

benchmark ปัจจุบัน replay ทีละเกมอิสระ (`draftbench.replay_draft` ไม่ตั้ง series/sides) →
ไม่สร้าง candidate pool แบบ Global Ban-Pick · วัดขนาด gap ถ้า replay แบบ series-aware:

| ตัวชี้วัด | ค่า |
|---|---|
| เกมที่เป็นเกม N>1 (non-final) ของซีรีส์ | 640 |
| เกมที่ pool ของทีมดราฟต์ถูกตัด ≥1 ตัวจริง | 640 |
| PICK turns ในเกมเหล่านั้น (สองทีม) | 6,400 |
| **PICK turns ที่ legal pool จะต่างไป** | **6,395 (99.9%)** |
| candidate removals รวม (hero×team×game) | 9,580 |
| เกมที่ best_of ไม่รู้ (ใส่ lock แบบ conservative) | 526 |

**ข้อควรระวัง:** (ก) "pool ต่าง" เป็น **upper bound** ของ "อันดับต่าง" — ตัวที่ถูกตัดอาจไม่ได้อยู่ top-K
(ข) 526 เกม best_of ไม่รู้ → ระบุเกมสุดท้ายไม่ได้ อาจนับ final game เกินจริง (ค) บางอีเวนต์อาจไม่ใช้ GBP (§7)
· **ยังไม่ wire series-aware replay เข้า benchmark ในเฟสนี้** (จะเปลี่ยน headline — เป็นงานเฟสหน้า)

---

## 9. Tests

| | ก่อน | หลัง |
|---|---|---|
| unit total | 650 passed · 11 skipped | **666 passed · 11 skipped** |
| series identity (ใหม่) | — | `test_series_identity.py` (15 ข้อ · invariant 1-9 + integration + parity) |
| migrated | — | `test_draft_state.py` (5 GBP) · `test_ban_intelligence.py` (1) → identity |
| web board | 15 | 17 (+2 identity guards) |

**invariant 9 (Python/JS parity):** รัน helper lock ของ template จริงใน **node** เทียบกับ
`SeriesState` — used · wins · locks ตรงกัน (ข้าม side swap: fs ใช้ตอน red เกม 2 → lock ฝั่ง blue เกม 3)

behavior before/after: คำแนะนำของ**เกมเดี่ยว** (ไม่มี series) เท่าเดิมทุกประการ (regression 650→ผ่าน) ·
สิ่งที่เปลี่ยน = series lock ที่เคยผิด (side) กลายเป็นถูก (identity) เมื่อมี series context

---

## 10. Remaining UNKNOWNs

1. `SideSelection.later_games = previous_loser` ยัง `verified: false`
2. own-team GBP ใช้กับทุกอีเวนต์/สเตจไหม (3 series ใน §7 ค้าน) — ต้องดู rulebook ต่ออีเวนต์
3. `best_of` หายบ่อย (249/305 = None) → ระบุ final game ไม่ได้ในหลายซีรีส์ (data gap)
4. series-aware benchmark replay (จะกระทบ headline) — เฟสหน้า

---

## 11. ยืนยันขอบเขต

ไม่แตะ Counter/Synergy/Composition · ไม่ tune weights · ไม่ใช้ clean-window · ไม่ infer side rules ·
ไม่แก้ `reset_on_final_game` · เกมเดี่ยว behavior เท่าเดิม
