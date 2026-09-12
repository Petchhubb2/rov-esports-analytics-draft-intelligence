# 40 — Global Ban-Pick Rule Audit

PHASE M2A.6A · STEP 2-5 · 2026-09-12 · **verify rule scope · ไม่ infer กติกาจาก picks · ไม่แก้ engine**

inventory: [docs/39](39-competition-rule-inventory.md) · eligibility: [docs/41](41-series-benchmark-eligibility.md)

---

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

### 2.2 อีก 4 รายการ — ไม่มี source ของตัวเอง

| event | global_ban_pick | reset_on_final | side_selection | sequence | หมายเหตุจาก **observation** (ไม่ใช่หลักฐานกติกา) |
|---|---|---|---|---|---|
| RPL 2026 Winter | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | ไม่พบ reuse ในข้อมูลที่แข่งแล้ว (93 เกม) — **ไม่ใช่ข้อพิสูจน์** |
| RPL 2025 Winter | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | ⚠️ **observation ขัดกับ own-team GBP** — hd reuse billow/hayate/teemee กลางซีรีส์ (§3) |
| GCS 2026 Spring | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | ไม่พบ reuse (196 เกม) — ไม่ใช่ข้อพิสูจน์ |
| GCS 2026 Summer | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | observation: 1 reuse กลางซีรีส์ (bmg/one) |

> **ห้ามเติม UNKNOWN จาก RPL 2026 Summer** (โจทย์ห้าม) · โดยเฉพาะ **RPL 2025 Winter ที่ข้อมูล
> _ค้าน_ การใช้ own-team GBP** — เป็นสัญญาณว่ากติกาอาจต่างกันตามฤดูกาล (fearless อาจเพิ่งมาปี 2026)

---

## 3. จำแนก 8 reuse cases (STEP 4)

จาก M2A.5 · map เข้า tournament แล้ว (ไม่มีข้อสรุปรวมจนจำแนกครบ)

| # | event | series | reuse | เกม | จำแนก |
|---|---|---|---|---|---|
| 1-2 | **RPL 2026 Summer** | godji check vs bac (BoNone, 4 played) | godji `toro` g1→g4 · bac `marja` g3→g4 | กลางซีรีส์ | **observation_conflicts_with_documented_rule** — กติกา verified ห้าม reuse แต่เกิด reuse · ต้องสอบระดับ match (เป็น Bo5 จริงไหม / data / bracket reset) — **ยังไม่แก้กติกา** |
| 3-5 | **RPL 2025 Winter** | hd vs bac (BoNone, 5 played) | hd `billow/hayate/teemee` g1→g3 · `rouie` g3→g5 · bac `annette` g1→g3 | กลางซีรีส์ | **unresolved (event rule not source-verified)** — reuse หนักกลางซีรีส์ ชี้ว่า own-team GBP อาจไม่บังคับใน RPL 2025 Winter |
| 6-7 | **RPL 2025 Winter** | bac vs bru (**Bo7**, 7 played) | reuse ทั้งหมด**ในเกม 7** (= best_of) | เกมตัดสิน | **explained_by_reset** — เข้ากับ reset_on_final_game (RPL rule) · หมายเหตุ: RPL 2025 Winter rule ยังไม่ verified แยก แต่ reuse อยู่เฉพาะเกมตัดสินตามรูปแบบ reset |
| 8 | **GCS 2026 Summer** | bmg vs one (BoNone, 4 played) | one `zephys` g1→g4 | กลางซีรีส์ | **unresolved (event rule not source-verified)** |

**สรุปการจำแนก:** explained_by_reset 2 (1 series) · observation_conflicts_with_documented_rule 2 (1 series) ·
unresolved 4 (2 series) · parser_or_data_issue 0 (แต่ #1-2 ต้องสอบว่าเป็น data หรือไม่) ·
likely_unplayed_slot_artifact 0

> **ไม่มี** case ไหนเกิดจากบั๊ก side/identity (M2A.5 แก้ไปแล้ว · identity pairing อ่านถูกทุก case)
> **ไม่แก้ `reset_on_final_game`** เพื่อลบ violation (โจทย์ห้าม)

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
