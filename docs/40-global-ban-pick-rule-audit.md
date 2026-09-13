# 40 — Global Ban-Pick Rule Audit

PHASE M2A.6A · STEP 2-5 · 2026-09-12 · **verify rule scope · ไม่ infer กติกาจาก picks · ไม่แก้ engine**

inventory: [docs/39](39-competition-rule-inventory.md) · eligibility: [docs/41](41-series-benchmark-eligibility.md)

---

> **M2A.6A.1 update (2026-09-13 · web-verified · [docs/42](42-rule-source-recovery.md)):**
> ผู้ใช้ยืนยัน Liquipedia Format ผ่าน browser แล้ว → **RPL 2026 Summer: Group Stage = Bo5 · Playoffs = Bo7 ·
> Global Ban-Pick ใช้กับ _ทุกแมตช์_ · Bo3/Bo5 ห้ามใช้ตัวที่เคยใช้ในซีรีส์ · Bo7 เกม 1-6 บังคับ เกม 7 กลับ normal**
> → **ยกเลิก hypothesis "playoff-only" · stage scope ไม่ใช่ UNKNOWN อีกต่อไป (VERIFIED ว่าใช้ทุกแมตช์)**
> · godji/bac (group-stage Bo5, reuse จริง) จึงเป็น **`observation_conflicts_with_documented_rule`**
> · คำถามที่เหลือเปลี่ยนเป็น: **ทำไม raw match data ถึงขัดกับกติกาที่เอกสารระบุว่าใช้ทุกแมตช์**
> (source page error / match data anomaly / undocumented exception / admin exception / อื่น ๆ — **ไม่เดาคำตอบ**)
> · §2 ด้านล่างแก้เป็น VERIFIED สำหรับ 3 รายการ RPL แล้ว

## 1. แหล่งข้อมูลที่พยายามใช้

| ประเภท source (ที่โจทย์อนุญาต) | สถานะในเซสชันนี้ |
|---|---|
| 1. rulebook ทางการ | ไม่มีในมือ |
| 2. ประกาศ league/organizer | ไม่มีในมือ |
| 3. คำอธิบายบนบรอดแคสต์ | ไม่มีในมือ |
| 4. Liquipedia Format section (coach/reference มี provenance) | **RPL 2026 Summer มีใน repo** (quote ใน format.yaml) · อีก 4 รายการ **ดึงไม่ได้** — `WebFetch` โดน **HTTP 403 (Cloudflare)** |
| 5. match data | ใช้เป็น **observation เท่านั้น** ไม่ใช่หลักฐานกติกา |

> ดึง Liquipedia Format section ของอีก 4 รายการอัตโนมัติไม่ได้ (403) · ต้องเปิดด้วย
> browser/มือ (มี option ใช้ Chrome automation ในเซสชันนี้ถ้าต้องการ) — **ยังไม่ทำ เพราะ review-gate**

---

## 2. สถานะกติกาต่อ event (STEP 2 + 3)

สถานะ: **VERIFIED** (มี source ทางการ) · **SUPPORTED** (source รอง) · **OBSERVED_ONLY** (มีแต่ข้อมูลแมตช์) · **UNKNOWN**

### 2.1 RPL 2026 Summer — มี source

quote จาก Liquipedia "RoV Pro League/2026/Summer" Format (อยู่ใน `format.yaml` แล้ว):
> *"In a Bo3 or Bo5, each team is not allowed to choose the Champions they used in the
> previous rounds (If selecting the opponent's champions in the previous game, it is not
> affected by this rule). In a Bo7 match, this rule will apply for the first 6 games.
> The 7th game will be returned to the Normal Ban-Pick."*

| field | value | status |
|---|---|---|
| global_ban_pick | true | **VERIFIED** |
| scope | own_team_only | **VERIFIED** ("the Champions **they** used") |
| applies_to_bans | false | **VERIFIED** ("choose/used" = pick) |
| reset_on_final_game | true (Bo7 g7) | **VERIFIED** |
| side_selection | home g1 · previous_loser later | **VERIFIED** (Format · Side Selection Privilege) |
| draft sequence (ban/pick order) | standard 4-ban/5-pick | **UNKNOWN** (`verified: false` · Liquipedia ไม่เก็บลำดับรวม) |

### 2.2 อีก 4 รายการ — web-verified 2026-09-13 (Liquipedia Format section, ผ่าน browser)

| event | best_of (stage) | GBP enabled | GBP scope | Bo7 g7 reset | side selection | สถานะรวม |
|---|---|---|---|---|---|---|
| RPL 2026 Winter | Group Bo5 / PO Bo7 | true | ทุกแมตช์ | true | documented | **VERIFIED** |
| RPL 2025 Winter | Group Bo5 / PO Bo7 | true | ทุกแมตช์ | true | ไม่ได้ระบุ → UNKNOWN | **VERIFIED** (GBP) |
| GCS 2026 Spring | Regular Bo5 / PO Bo7 | true (documented) | **SUPPORTED** — ไม่ยืนยันคำว่า "ทุกแมตช์" | ไม่ได้ระบุ → UNKNOWN | ไม่ได้ระบุ → UNKNOWN | **SUPPORTED** |
| GCS 2026 Summer | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | **UNKNOWN** |

- source (ยกเว้น UNKNOWN) = Liquipedia Format section ของแต่ละหน้า (ผู้ใช้ยืนยันผ่าน browser 2026-09-13)
- `draft sequence` ทุกรายการยัง **UNKNOWN** · **GCS 2026 Summer:** ยังไม่ได้ main-event Format · **ห้ามใช้ Seat Challenge แทน**

> **แก้จาก M2A.6A:** เดิม 4 รายการนี้ UNKNOWN ทั้งหมด → ตอนนี้ 3 RPL **VERIFIED** (GBP ทุกแมตช์ +
> best_of ตาม stage) · GCS Spring **SUPPORTED** · **RPL 2025 Winter ที่ข้อมูลเคยดู "ค้าน" กติกา —
> ตอนนี้กติกา VERIFIED แล้ว → hd/bac กลายเป็น observation_conflicts_with_documented_rule (§3)**

---

## 3. จำแนก 8 reuse cases (STEP 4)

จาก M2A.5 · map เข้า tournament แล้ว (ไม่มีข้อสรุปรวมจนจำแนกครบ)

**revised หลัง web-verify (2026-09-13)** — best_of มาจาก stage rule (Group Bo5 / Playoff Bo7):

| # msgs | event | series | Bo (stage) | เกม | จำแนก (revised) |
|---|---|---|---|---|---|
| 2 | **RPL 2026 Summer** | godji/bac (Match#2, group) | Bo5 | g1,g4 / g3,g4 | **observation_conflicts_with_documented_rule** — GBP ทุกแมตช์ VERIFIED · reuse ขัด |
| 3 | **RPL 2025 Winter** | hd/bac (group) | Bo5 | g1,g3,g5 | **observation_conflicts_with_documented_rule** (upgraded — GBP ทุกแมตช์ VERIFIED แล้ว) |
| 2 | **RPL 2025 Winter** | bac/bru (playoff) | Bo7 | ทั้งหมด g7 | **explained_by_documented_reset** — Bo7 g7 กลับ normal (VERIFIED) |
| 1 | **GCS 2026 Summer** | bmg/one | rule UNKNOWN | g1,g4 | **unresolved** — GCS Summer rule ยังไม่ verified |

**สรุป (revised):** observation_conflicts_with_documented_rule **5 msgs / 2 series** ·
explained_by_documented_reset 2 / 1 series · unresolved 1 (GCS Summer) · parser/alias/picks-vs-bans **0**
(picks-only check + canonical ids + raw-confirmed map index — ตัดทิ้งทั้งหมด · ดู [docs/42 §B,D](42-rule-source-recovery.md))

> ⚠️ **2 series RPL (godji/bac, hd/bac) reuse ขัดกับกติกาที่เอกสารระบุว่าใช้ _ทุกแมตช์_** — คำถามปลายเปิด:
> source page error / match data anomaly / undocumented exception / competition admin exception / อื่น ๆ ·
> **ไม่เดาคำตอบ · ไม่แก้กติกา** · ไม่มี case ใดเกิดจากบั๊ก side/identity (M2A.5 แก้แล้ว)

---

## 4. Rule config model (STEP 5 — schema design, ยังไม่ wire เข้า engine)

reuse สถาปัตยกรรม `format.yaml` (per-field value + status + source) · เสนอ `configs/draft/competitions.yaml`
1 entry ต่อ event map → `format` + rule status:

```yaml
# schema (pydantic — M2A.6B จะ implement · เฟสนี้ define เฉย ๆ)
CompetitionDraftRules:
  competition_id: str            # เช่น rpl_2026_summer
  liquipedia_page: str           # source id
  format_ref: str                # ชี้ format.yaml ที่ใช้
  rules:
    global_ban_pick: {value: bool|null, status: Status, source: str|null}
    global_ban_scope: {value: own_team_only|both_teams|null, status, source}
    applies_to_bans:  {value: bool|null, status, source}
    starts_at_game:   {value: int|null, status, source}      # ปกติ 2
    reset_condition:  {value: str|null, status, source}      # เช่น "final_game_of_bo7"
    side_selection:   {value: str|null, status, source}
    draft_sequence:   {value: str|null, status, source}
  # Status = VERIFIED | SUPPORTED | OBSERVED_ONLY | UNKNOWN
```

หลักการ: **ไม่ hardcode ชื่อทัวร์นาเมนต์ในโค้ด engine** — engine อ่าน rule จาก config ต่อ competition ·
เกมที่ competition มี rule = UNKNOWN → **series-aware lock ห้ามทำงาน** (fall back เป็นเกมเดี่ยว)

M2A.6B: implement pydantic model + config นี้ + wire `SeriesState.locked_heroes_for` ให้เคารพ status
(VERIFIED เท่านั้นจึง lock) · เฟสนี้ **ไม่ implement behavior**

---

## 5. UNKNOWN ที่ยังเหลือ

1. GBP rule ของ 4 รายการ (RPL 2026 Winter · RPL 2025 Winter · GCS Spring · GCS Summer) — ต้องเปิด Liquipedia Format section (403 ต่อ automated fetch)
2. RPL 2026 Summer: godji/bac conflict — ต้องสอบ match page ว่าเป็น Bo5 จริง/data/rule exception
3. draft sequence (ทุก event) ยัง UNKNOWN
4. best_of หายไป 82% → ระบุเกม Bo7 (ที่ต้อง reset) ไม่ได้ในหลายซีรีส์
