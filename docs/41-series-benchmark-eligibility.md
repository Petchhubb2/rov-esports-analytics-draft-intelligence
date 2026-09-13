# 41 — Series-Aware Benchmark Eligibility

PHASE M2A.6A · STEP 7 · 2026-09-12 · **revised M2A.6A.1 2026-09-13 (web-verified rules)**

audit: [docs/40](40-global-ban-pick-rule-audit.md) · recovery: [docs/42](42-rule-source-recovery.md) · inventory: [docs/39](39-competition-rule-inventory.md)

series-aware replay "ปลอดภัยโดยไม่เดา" เมื่อรู้ครบ: (1) team identity เจ้าของ history ✅ (M2A.5) ·
(2) GBP ใช้กับ event/stage นี้ไหม · (3) prior picks สร้าง lock · (4) เกมนี้ reset ไหม (ต้องรู้ Bo) ·
(5) side assignment ✅ (M2A.5)

> **แก้ใหญ่จาก M2A.6A:** เดิมมี source แค่ RPL 2026 Summer → eligibility ≤34% · หลัง web-verify
> (2026-09-13) กติกา 3 รายการ RPL เป็น **VERIFIED** และ best_of รู้ 88% (ตาม stage) → eligibility พุ่งขึ้นมาก

---

## 1. Eligibility table (played games = 861)

| event | played games | rule status | best_of | benchmark-safe? |
|---|---|---|---|---|
| RPL 2026 Summer | 291 (33.8%) | **VERIFIED** (GBP ทุกแมตช์) | Group Bo5 / PO Bo7 | ✅ (ยกเว้น 1 conflict series) |
| RPL 2026 Winter | 93 (10.8%) | **VERIFIED** | Group Bo5 / PO Bo7 | ✅ |
| RPL 2025 Winter | 232 (26.9%) | **VERIFIED** | Group Bo5 / PO Bo7 | ✅ (ยกเว้น 1 conflict series) |
| GCS 2026 Spring | 196 (22.8%) | **SUPPORTED** (GBP documented · scope wording ไม่ยืนยัน "ทุกแมตช์") | Regular Bo5 / PO Bo7 | ⚠️ ได้แบบ SUPPORTED |
| GCS 2026 Summer | 49 (5.7%) | **UNKNOWN** (ไม่ได้ main-event Format) | UNKNOWN | ❌ |

| สรุป | games | % |
|---|---|---|
| **VERIFIED** (3× RPL) | **616** | **71.5%** |
| SUPPORTED (GCS Spring) | 196 | 22.8% |
| UNKNOWN (GCS Summer) | 49 | 5.7% |

→ **VERIFIED ~71.5% · รวม SUPPORTED ~94.3% · เหลือ UNKNOWN แค่ 5.7%**

---

## 2. เงื่อนไขค้าง (เล็กลงมาก)

1. **2 conflict series** ใน VERIFIED events (godji/bac RPL 2026 Summer · hd/bac RPL 2025 Winter) —
   reuse จริงขัดกติกาที่เอกสารระบุว่าใช้ทุกแมตช์ ([docs/40 §3](40-global-ban-pick-rule-audit.md)) ·
   ~9 เกม · ต้อง **flag/exclude หรือสอบ** ก่อน ไม่งั้น replay จะ lock ตัวที่ทีมใช้จริง (data ขัด rule)
2. **best_of ไม่ block VERIFIED events อีกต่อไป** — รู้ Bo แล้ว 269/305 (88%) จาก stage rule →
   ระบุ Bo7 g7 reset ได้ · เหลือ 36 ที่ยังไม่รู้ = **GCS Summer เท่านั้น** (ซึ่ง UNKNOWN อยู่แล้ว)
3. GCS Spring = SUPPORTED (GBP documented แต่ยังไม่ยืนยันคำว่า "ทุกแมตช์" + ไม่ยืนยัน g7 reset/side)

---

## 3. ตอบ STEP 8 — M2A.6B เดินได้ไหมโดยไม่เดา

**ได้แล้วในวงกว้าง (ต่างจาก M2A.6A):**

- **VERIFIED subset (3× RPL, 616 เกม / 71.5%)** — เดินได้ โดย **exclude/flag 2 conflict series** ก่อน
- **+ GCS Spring (SUPPORTED, +196)** — รวม 94.3% ถ้ายอมรับระดับ SUPPORTED (report แยกจาก VERIFIED)
- **GCS 2026 Summer (49 / 5.7%) — UNKNOWN → ห้าม replay** จนกว่าได้ main-event Format (ห้ามใช้ Seat Challenge แทน)

**เงื่อนไขก่อนเริ่ม M2A.6B:**
1. per-competition/stage rule config ([docs/40 §4](40-global-ban-pick-rule-audit.md)) — engine อ่าน rule ต่อ event/stage ·
   UNKNOWN → fall back เกมเดี่ยว
2. best_of provenance (explicit / verified_stage_rule) — **ห้ามอนุมานจากเกมที่เล่นหรือ map slot**
3. ตัดสินใจเรื่อง 2 conflict series (exclude / investigate)
4. benchmark series-aware รายงาน headline **แยก** จากเดิม (ไม่เขียนทับ)

---

## 4. ยังต้องหา source เพิ่ม

- GCS 2026 Summer main-event Format (GBP + best_of + reset + side)
- คำอธิบาย 2 conflict series (RPL Summer godji/bac · RPL 2025 Winter hd/bac) — ยังปลายเปิด
- draft sequence (ทุก event) · GCS Spring: ยืนยันคำว่า "ทุกแมตช์" + g7 reset + side-selection
