# 39 — Competition Rule Inventory

PHASE M2A.6A · STEP 1 + 6 · 2026-09-12 · **verification only — ไม่แตะ engine / benchmark / weights**

นับจากข้อมูลจริงใน cache (offline) · ไม่มีการอนุมานกติกาจาก picks

---

## 1. ชุดข้อมูลที่มีอยู่ (STEP 1)

`_regions()` โหลดจาก `KNOWN_TOURNAMENTS` (5 รายการ) · ทุกรายการใช้ `configs/draft/format.yaml`
(`id: rpl_2026`, "RPL / GCS มาตรฐาน") ชุดเดียวร่วมกัน

| tournament | key | Liquipedia page (source id) | ซีรีส์ | played games | best-of (parsed) | ปี |
|---|---|---|---|---|---|---|
| RPL 2026 Summer | TH | `RoV Pro League/2026/Summer` | 76 | **291** | Bo5×8 · Bo7×4 · None×64 | 2026 |
| RPL 2026 Winter | TH | `RoV Pro League/2026/Winter` | 76 | 93 | Bo5×8 · Bo7×4 · None×64 | 2026 |
| RPL 2025 Winter | TH | `RoV Pro League/2025/Winter` | 60 | 232 | Bo5×8 · Bo7×4 · None×48 | 2025 |
| GCS 2026 Spring | TW | `Garena Challenger Series/2026/Spring` | 46 | 196 | Bo5×7 · Bo7×2 · None×37 | 2026 |
| GCS 2026 Summer | TW | `Garena Challenger Series/2026/Summer` | 47 | 49 | Bo5×8 · Bo7×3 · None×36 | 2026 |
| **รวม** | | | **305** | **861** | Bo5×39 · Bo7×17 · **None×249** | |

**stage:** `KNOWN_TOURNAMENTS` ไม่ได้แยก stage (group/playoff) — หนึ่ง page = หนึ่ง season รวมทุก stage
· date range ต่อ season อยู่ในข้อมูลแต่ยังไม่แยก stage (ต้องดู match dates ถ้าต้องการ)

### 1.1 ที่มาของ format/rule ปัจจุบัน

- **format เดียวใช้ทั้ง 5 รายการ** — `configs/draft/format.yaml`
- `global_ban_pick.verified: true` · `source:` = **"RoV Pro League/2026/Summer" Format · Global Ban-Pick Rules** เท่านั้น
- `sequence` (ลำดับ ban/pick) `verified: false` · `turn_clock` `verified: false`
- **ไม่มี source แยกต่อ event** สำหรับ RPL 2026 Winter / RPL 2025 Winter / GCS Spring / GCS Summer

> **ช่องว่างหลัก:** กติกาที่ verified มาจาก RPL 2026 Summer **รายการเดียว** แต่ถูกนำไปใช้กับ
> อีก 4 รายการ (570/861 = 66% ของ played games) โดย**ไม่มี source ของตัวเอง** — ดู docs/40

---

## 2. Played-game correction (STEP 6)

`parse_map` สร้าง `GameDraft` ต่อทุกช่อง `map1..mapN` ที่มีใน `{{Match}}` **รวมช่องที่ยังไม่แข่ง**
→ "parsed slot" ≠ "played game"

| นับ | ค่า |
|---|---|
| parsed slots (ทุก map slot) | **1,567** |
| **played games** (5+5 picks + winner ครบ) | **861** |
| unplayed / missing slots | **706 (45%)** |
| games ที่ side resolvable (มี team id ทั้งสองฝั่ง) | 1,511 |
| games ที่ side ambiguous (ขาด team id ≥1) | **56** (RPL 2026 Winter 28 · GCS 2026 Summer 28) |

- side_ambiguous 56 กระจุกอยู่ใน 2 รายการที่กำลังแข่ง (unplayed เยอะ: RPL 2026 Winter 295, GCS 2026 Summer 196)
- **best_of parse ไม่ได้ 249/305 ซีรีส์ (82%)** — Liquipedia เขียน bestof ไม่ครบ → ระบุ "เกมสุดท้าย"
  (สำหรับ reset_on_final_game) ไม่ได้ในหลายซีรีส์ · เป็น data gap สำคัญต่อ M2A.6B

### 2.1 แก้ไข denominator ใน docs/36

docs/36 §2 นับ "series ที่มี ≥2 games = 305" และ side-swap (197/100/8) **บนหน่วย parsed slot**
(รวม 706 unplayed) ไม่ใช่ played game · ตัวเลข **played game = 861 ถูกต้อง** (ใช้ที่อื่นอยู่แล้ว) ·
**ข้อสรุปเชิงคุณภาพของ M2A.5 ไม่เปลี่ยน** (identity คงที่ · side ต่อเกม · ไม่ใช่ odd/even —
ตัวอย่างใน fixture ใช้เฉพาะ played games) · docs/36 ได้เพิ่มหมายเหตุแก้ denominator แล้ว

---

## 3. ต่อไป

- **docs/40** — verify Global Ban-Pick rule ต่อ event + จำแนก 8 reuse cases + schema
- **docs/41** — เกม/turn ที่ eligible สำหรับ series-aware replay โดยไม่ต้องเดา
