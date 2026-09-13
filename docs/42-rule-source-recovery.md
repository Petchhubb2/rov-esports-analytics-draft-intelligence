# 42 — Rule Source Recovery & Conflict Resolution

PHASE M2A.6A.1 · 2026-09-13 · **investigation only · ยังไม่แก้ code / parser / benchmark / weights**

ต่อจาก [docs/40](40-global-ban-pick-rule-audit.md) · ทุกข้อ trace จาก **cached raw wikitext** (offline)

---

## A. Source recovery — web-verified โดยผู้ใช้ (2026-09-13)

`WebFetch` โดน 403 (Cloudflare) และ Chrome MCP หลุดในเซสชัน agent · **ผู้ใช้เปิด Liquipedia
Format section เองผ่าน browser** แล้วส่ง source-backed facts กลับมา → อัปเดต 4 รายการ:

| event | best_of (stage) | GBP | status |
|---|---|---|---|
| RPL 2026 Summer | Group Bo5 / PO Bo7 | ทุกแมตช์ · Bo3/Bo5 no-reuse · Bo7 g1-6, g7 normal | **VERIFIED** |
| RPL 2026 Winter | Group Bo5 / PO Bo7 | ทุกแมตช์ · Bo7 g7 reset · side-selection documented | **VERIFIED** |
| RPL 2025 Winter | Group Bo5 / PO Bo7 | ทุกแมตช์ · Bo7 g7 reset | **VERIFIED** (GBP) |
| GCS 2026 Spring | Regular Bo5 / PO Bo7 | documented (ไม่ยืนยันคำว่า "ทุกแมตช์") | **SUPPORTED** |
| GCS 2026 Summer | — | ยังไม่ได้ main-event Format (ห้ามใช้ Seat Challenge แทน) | **UNKNOWN** |

B (godji/bac) และ C (best_of) ทำจาก cached wikitext · ตอนนี้ตีความใหม่ภายใต้กติกาที่ verified แล้ว

---

## B. godji vs bac — raw evidence + final classification

ในหน้า **RoV Pro League/2026/Summer/Group Stage** มี **สอง match** ระหว่างคู่นี้ (double round-robin):

| match | date | bestof (raw) | ผล | หมายเหตุ |
|---|---|---|---|---|
| #1 | Feb 12, 2026 | **5** | godji ชนะ 3-0 | ไม่มี reuse ในแมตช์ |
| #2 | Mar 12, 2026 | **(หายไป)** = Bo5 (map1-5, bac ชนะ 3-1) | **มี reuse** | คือ case ที่ M2A.5 จับได้ |

**Match #2 (raw t1h/t2h = picks):**
- `godji` **pick** `toro` ใน **map1** (blue) และ **map4** (blue) → reuse g1→g4
- `bac` **pick** `marja` ใน **map3** (blue) และ **map4** (red) → reuse g3→g4 (คนละ side · ผูก identity ถูก)

ตรวจครบทุกช่อง:
- team identity ถูก · game numbers ถูก (map index จาก raw) · **เป็น PICK ไม่ใช่ BAN** (อ่านจาก t1h/t2h) ·
  ไม่ใช่ alias (`toro`/`marja` เป็น id หลัก) · parser ไม่ได้ duplicate/shift (สอง match แยกกันจริง ตรงกับ raw) ·
  ทั้งคู่อยู่ **Group Stage** เดียวกัน · Match #2 เป็น Bo5 (map1-5) ไม่มี final-game reset ใน Bo5 ตามกติกา

**สรุปสำคัญ:** reuse เกิดจริงใน Bo5 กลุ่ม ซึ่ง **ขัดกับกติกา verified** ("Bo3/Bo5 ห้ามใช้ champion
ที่เคยใช้ใน previous rounds") · แต่ Match #1 (Bo5 คู่เดียวกัน) กลับไม่มี reuse

> **classification (revised · web-verified): `observation_conflicts_with_documented_rule`**
>
> Liquipedia Format ยืนยันแล้วว่า **RPL 2026 Summer ใช้ GBP ทุกแมตช์ · Group Stage = Bo5 · Bo3/Bo5
> ห้ามใช้ตัวที่เคยใช้ในซีรีส์** → **ยกเลิก hypothesis "playoff-only"** (stage scope ไม่ใช่ UNKNOWN · กติกา
> ครอบ group stage แน่นอน) · godji/bac Match #2 เป็น group-stage Bo5 ที่ **reuse จริง ขัดกติกาที่เอกสารระบุ**
>
> **คำถามที่เหลือ (ปลายเปิด · ไม่เดาคำตอบ):** ทำไม raw match data ถึงขัดกับกติกา all-match ที่ documented?
> ความเป็นไปได้ที่ยังเปิดอยู่: source page error · match data anomaly · undocumented exception ·
> competition administration exception · other unresolved source conflict · **ยังไม่แก้กติกา · ยังไม่สรุป**
> (บริบท: reuse rate รวมทั้ง dataset แค่ 0.9% = 8/861 → เป็นข้อยกเว้นที่หายาก ไม่ใช่พฤติกรรมทั่วไป)

**ไม่ใช่:** parser_or_data_bug · picks-vs-bans · alias · rule_exception_verified (ยืนยันไม่ได้)

---

## C. best_of — root cause

`parse_match` อ่าน `tpl.get("bestof")` ต่อ {{Match}} · ตรวจ raw ทั้ง 5 รายการ:

| root cause | จำนวน match |
|---|---|
| 1. bestof มีใน raw แต่ parser พลาด | **0** — parser อ่านครบ 56/56 ที่มี |
| 2. bestof อยู่ระดับ stage/bracket (parser น่าจะอ่านได้) | **0** — **ทุก `bestof=` อยู่ใน {{Match}}** (nearest-enclosing = Match 12/12) ไม่มี bracket/group ตั้ง bestof |
| 3. source ไม่มี bestof ต่อ match | **249** (RPL Summer 64 · RPL Winter 64 · RPL 2025W 48 · GCS Spring 37 · GCS Summer 36) |
| 4. malformed/ambiguous | 0 |

- **ไม่มี parser bug** · แก้ parser ก็ได้ `bestof` per-match เพิ่มไม่ได้ (source ไม่มี) · **ตัด map-slot
  heuristic ทิ้ง** — โจทย์ห้ามอนุมาน Bo จากจำนวน map slot (และจากเกมที่เล่นจริง)

### C.1 best_of provenance model (2 แหล่งอิสระ · revised web-verified)

```
best_of:
  value: 5
  provenance: {type: explicit_match | verified_stage_rule, source: ...}
  status: VERIFIED (explicit_match) | SUPPORTED (verified_stage_rule)
```

- **A. explicit_match** — `bestof=` ใน {{Match}} → **VERIFIED**
- **B. verified_stage_rule** — Group/Regular = Bo5 · Playoffs = Bo7 (Liquipedia Format, web-verified) →
  **SUPPORTED** (assign ตาม stage ที่ match อยู่ · จับจากชื่อหน้า Group Stage / Regular Season / Playoffs)

**recount (per match · 305 series):**

| provenance | count | status |
|---|---|---|
| explicit_match | **56** | VERIFIED |
| verified_stage_rule (RPL×3 + GCS Spring) | **213** | SUPPORTED |
| still_unknown (GCS Summer เท่านั้น) | **36** | UNKNOWN |

→ **รู้ best_of 269/305 (88.2%)** (เดิม M2A.6A รายงาน 18.4% เพราะยังไม่มี stage rule verified)

---

## D. 8 reuse cases — verified against raw

`global_ban_pick_check` ใช้ **picks เท่านั้น** (g.blue_picks/red_picks) → **picks-vs-bans confusion เป็นไปไม่ได้ทั้ง 8 ข้อ** โดยโครงสร้าง · game numbers = map index · id เป็น canonical (ไม่มี alias)

| # msgs | event | series | Bo (stage) | ตำแหน่ง reuse | classification (revised) |
|---|---|---|---|---|---|
| 2 | RPL 2026 Summer | godji/bac (Match#2, group) | **Bo5** | mid-series (g1,g4 / g3,g4) | **observation_conflicts_with_documented_rule** (GBP ทุกแมตช์ VERIFIED) |
| 3 | RPL 2025 Winter | hd/bac (group) | **Bo5** | mid-series (g1,g3,g5) | **observation_conflicts_with_documented_rule** (upgraded) |
| 2 | RPL 2025 Winter | bac/bru (playoff) | **Bo7** | **ทั้งหมดในเกม 7** | **explained_by_documented_reset** (Bo7 g7 กลับ normal · VERIFIED) |
| 1 | GCS 2026 Summer | bmg/one | rule UNKNOWN | mid-series (g1,g4) | **unresolved** (GCS Summer rule ยังไม่ verified) |

รวม (revised): observation_conflicts_with_documented_rule **5 (2 series)** · explained_by_documented_reset 2 (1 series) ·
unresolved 1 (GCS Summer) · parser_or_data / picks-vs-bans / alias / wrong-game-assignment **0**

---

## E. Benchmark gate (นิยาม · ยังไม่รัน)

เกมจะ **VERIFIED-replay-eligible** ก็ต่อเมื่อรู้ครบทุกฟิลด์ที่ตัดสิน legal pool:
1. team identity ที่เป็นเจ้าของ prior history ✅ (M2A.5)
2. GBP ใช้กับ event/stage นี้ไหม — ✅ **VERIFIED 3× RPL (ทุกแมตช์)** · SUPPORTED GCS Spring · UNKNOWN GCS Summer
3. prior selection ไหนสร้าง lock ✅
4. เกมนี้ reset lock ไหม — ต้องรู้ Bo · ✅ **รู้แล้ว 88% (269/305)** จาก stage rule (Bo7 g7 reset ระบุได้) · เหลือ GCS Summer
5. current side assignment ✅ (M2A.5)

→ **VERIFIED subset (3× RPL, 616 เกม / 71.5%) ผ่าน gate** ยกเว้น **2 conflict series** (godji/bac, hd/bac)
ที่ data ขัด rule (§B, §D) ต้อง flag/exclude ก่อน · GCS Spring = SUPPORTED · GCS Summer = UNKNOWN (ห้าม replay)
· รายละเอียด eligibility ใน [docs/41](41-series-benchmark-eligibility.md)

---

## F. ไฟล์ที่ต้องแก้ **ถ้า** ตัดสินใจแก้ (ยังไม่แก้)

| ถ้าจะทำ | ไฟล์ | หมายเหตุ |
|---|---|---|
| per-competition/stage rule config (best_of ต่อ stage + GBP + reset + side + status/source) | ใหม่: `configs/draft/competitions.yaml` + `packages/core/rov/draft/competition.py` | schema docs/40 §4 + best_of provenance docs/42 §C.1 · **M2A.6B** |
| assign best_of ต่อ match จาก stage rule (ไม่ใช่ parser · ไม่ใช่ map-slot) | จุดที่ build `SeriesState` จากข้อมูลจริง (บริบท benchmark M2A.6B) | explicit_match ชนะ stage_rule เมื่อมีทั้งคู่ |
| wire rule เข้า lock | `packages/core/rov/draft/series.py` (`locked_heroes_for` เคารพ status) | M2A.6B · UNKNOWN → ไม่ lock |

`parse_match` **ไม่ต้องแก้** (อ่าน explicit `bestof` ถูกอยู่แล้ว)

**M2A.6A.1 เอง: docs อย่างเดียว ไม่แตะ code**
