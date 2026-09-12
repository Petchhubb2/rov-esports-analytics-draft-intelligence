# 41 — Series-Aware Benchmark Eligibility

PHASE M2A.6A · STEP 7 · 2026-09-12 · **ยังไม่รัน benchmark ใหม่ · ประเมิน eligibility เท่านั้น**

audit: [docs/40](40-global-ban-pick-rule-audit.md) · inventory: [docs/39](39-competition-rule-inventory.md)

series-aware replay จะ "ปลอดภัยโดยไม่เดา" ก็ต่อเมื่อ **กติกา GBP ของ event นั้น VERIFIED**
(เกมเดี่ยว game 1 ไม่ต้องใช้ lock อยู่แล้ว · lock มีผลเฉพาะ game N>1)

---

## 1. Eligibility table (ตาม played games = 861)

| event | played games | GBP rule status | benchmark-safe? |
|---|---|---|---|
| **RPL 2026 Summer** | **291** (33.8%) | **VERIFIED** | ✅ **ได้** — แต่มีเงื่อนไข §2 |
| RPL 2026 Winter | 93 (10.8%) | UNKNOWN | ❌ ไม่ (ไม่มี source) |
| RPL 2025 Winter | 232 (26.9%) | UNKNOWN + **observation ค้าน** | ❌ **ไม่** (ข้อมูลชี้ว่าอาจไม่ใช้ own-team GBP) |
| GCS 2026 Spring | 196 (22.8%) | UNKNOWN | ❌ ไม่ |
| GCS 2026 Summer | 49 (5.7%) | UNKNOWN | ❌ ไม่ |

| สรุป | games | % |
|---|---|---|
| VERIFIED (eligible) | **291** | **33.8%** |
| UNKNOWN (ไม่ eligible) | 570 | 66.2% |

% ของ historical turns ≈ ตามสัดส่วน games → **~34% eligible · ~66% ต้องเดาถ้าจะ replay**

---

## 2. แม้แต่ 291 เกมของ RPL 2026 Summer ก็ยังมีเงื่อนไขค้าง

1. **godji/bac conflict** — 1 ซีรีส์ (~4 เกม) มี reuse กลางซีรีส์ที่ขัดกติกา verified
   ([docs/40 §3](40-global-ban-pick-rule-audit.md)) → ต้องสอบ match page ก่อน ไม่งั้น lock อาจผิด
2. **best_of หายใน 82% ของซีรีส์** → ซีรีส์ Bo7 ที่ best_of=None จะระบุ "เกม 7 (reset)" ไม่ได้ →
   series-aware lock อาจ lock เกมตัดสินผิด · ต้องเติม best_of หรือมีวิธีระบุ Bo7 ที่ไม่ใช่การเดา

→ **fully-clean eligibility < 33.8%** จนกว่าจะเคลียร์ 2 ข้อนี้

---

## 3. ตอบ STEP 8 — M2A.6B เดินได้ไหมโดยไม่เดา

**ไม่ได้ในระดับทั้ง dataset** — 66% เป็น UNKNOWN และ RPL 2025 Winter ข้อมูล**ค้าน**การใช้กติกา
· ถ้าฝืน apply กติกา RPL 2026 Summer กับทุก event = การเดา (โจทย์ห้าม)

**เดินได้แบบจำกัดขอบเขต** เฉพาะ **RPL 2026 Summer** (≤34%) **หลังจาก**:
- สอบ godji/bac conflict (data artifact หรือ rule exception)
- แก้ best_of ของซีรีส์ Bo7 ใน Summer (ไม่งั้น reset ระบุไม่ได้)

**ทางเลือกเพื่อขยาย eligibility** (ก่อน M2A.6B):
- เปิด Liquipedia Format section ของอีก 4 รายการ (fetch อัตโนมัติโดน 403 · ใช้ browser/มือ/Chrome automation) → upgrade UNKNOWN→VERIFIED เท่าที่ source รองรับ
- ถ้า RPL 2025 Winter ยืนยันว่า**ไม่**ใช้ own-team GBP → mark rule ต่อ season ให้ถูก แล้ว replay แบบ per-competition rule

---

## 4. ข้อเสนอ (รอ review)

1. M2A.6B ทำ **per-competition rule config** (docs/40 §4) ก่อน — engine อ่าน rule ต่อ event ·
   UNKNOWN → fall back เกมเดี่ยว (ไม่ lock)
2. benchmark series-aware รันเฉพาะ subset ที่ VERIFIED · รายงาน headline **แยก** จาก headline เดิม
   (ไม่เขียนทับ) จนกว่าจะครอบคลุมพอ
3. งานเก็บ source: verify 4 รายการ + best_of + godji/bac — เป็น data/verification ไม่ใช่ tuning
