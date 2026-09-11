# เอกสารออกแบบระบบ — RoV Esports Analytics & Draft Intelligence

เอกสารชุดนี้แปลงแผนแนวคิดใน [`RoV_Esports_Analytics_แผนพัฒนาระบบ.md`](../RoV_Esports_Analytics_แผนพัฒนาระบบ.md)
ให้เป็น **แผนทางเทคนิคที่ลงมือทำได้** — มีสัญญาข้อมูล (data contract), อัลกอริทึม, สคีมา,
และเกณฑ์ผ่าน/ไม่ผ่านของแต่ละเฟส

เอกสารเดิม = "จะทำอะไร"  ·  เอกสารชุดนี้ = "จะทำอย่างไร และรู้ได้อย่างไรว่าทำสำเร็จ"

| # | เอกสาร | เนื้อหา |
|---|--------|---------|
| 00 | [project-structure.md](00-project-structure.md) | **แผนที่โฟลเดอร์/ไฟล์ทั้งโปรเจค** · อะไรอยู่ตรงไหน ทำอะไร สถานะเป็นยังไง |
| 01 | [assessment.md](01-assessment.md) | ประเมินแผนเดิม · ช่องว่าง 10 ข้อที่ต้องปิดก่อนเริ่มโค้ด |
| 02 | [architecture.md](02-architecture.md) | สถาปัตยกรรม · โครงสร้างโปรเจกต์ · การตัดสินใจด้าน stack |
| 03 | [data-contracts.md](03-data-contracts.md) | สคีมาทุก Layer · artifact ระหว่าง stage · DDL ฐานข้อมูล |
| 04 | [vision-pipeline.md](04-vision-pipeline.md) | Calibration · Detection · Identification · Tracking |
| 05 | [macro-events.md](05-macro-events.md) | Zone model · กติกาตรวจจับ event ทีละตัว |
| 06 | [draft-engine.md](06-draft-engine.md) | Hero attribute · Composition scoring · Matchup · Recommendation |
| 07 | [roadmap.md](07-roadmap.md) | เฟส · Acceptance gate · ประมาณการงาน |
| 08 | [game-reference.md](08-game-reference.md) | **ข้อมูลเกมที่ตรวจสอบแล้ว** · แพตช์ · แมพ · objective timing · กติกา draft · แหล่งข้อมูล |
| 09 | [build-log.md](09-build-log.md) | **สิ่งที่วัดได้จริงจากการลงมือทำ** · บั๊กที่เจอ · สมมติฐานที่ผิด · ตัวเลขล่าสุด |
| 10 | [blueprint-alignment.md](10-blueprint-alignment.md) | **เทียบ Blueprint กับโค้ดจริง** · แผนที่ 44 โมดูล · โครงสร้างโฟลเดอร์ · 5 Data Layer |
| 11 | [macro-planner.md](11-macro-planner.md) | Macro Knowledge Base · Rule Engine · Win Condition · Actual vs Recommended |
| 12 | [cross-league-meta.md](12-cross-league-meta.md) | **เมต้าข้ามลีก** ไทย RPL เทียบ ไต้หวัน GCS · 861 เกม · ตัวแก้ |
| 13 | [draft-simulator.md](13-draft-simulator.md) | **คู่มือใช้ Draft Simulator** · อ่านผลอย่างไร · ข้อจำกัด |
| 14 | [deployment.md](14-deployment.md) | **จากเครื่องตัวเองไปเซิร์ฟเวอร์จริง** · ลิขสิทธิ์ภาพ · สิ่งที่ยังขาด |
| 15 | [getting-footage.md](15-getting-footage.md) | **เอาคลิปแข่งเข้าระบบ** · หา VOD · ตัดเฟรม · ตอบคำถาม Phase 0 |
| 16 | [map-guide.md](16-map-guide.md) | คู่มือแผนที่ Antaris Battlefield · โซน · objective |
| 17 | [intelligence-audit.md](17-intelligence-audit.md) | **ตรวจความฉลาดของ Draft Engine** · scorecard 22/100 · 13 จุดอ่อน · quick/medium/large wins |
| 18 | [hero-data-coverage.md](18-hero-data-coverage.md) | **ฮีโร่ตัวไหนมีข้อมูลแล้ว** · 30/119 = 72.3% ของ pick+ban · ลำดับที่ควรกรอกต่อ |
| 19 | [python-js-parity.md](19-python-js-parity.md) | **ทุกจุดที่ตรรกะถูกเขียนซ้ำ** Python ↔ JS · 18 จุด · มีเทสต์คุม 11 ขาด 7 |
| 20 | [draft-intelligence-spec.md](20-draft-intelligence-spec.md) | **แบบที่จะสร้าง** · conceptual model · 11 factor · counter 5 ชั้น · benchmark plan |
| 21 | [phase-b-report.md](21-phase-b-report.md) | **ผลของ PHASE B** · เปิดใช้อะไรไปบ้าง · regression · benchmark · พร้อม PHASE M ไหม |
| 22 | [benchmark-foundation.md](22-benchmark-foundation.md) | **engine เทียบ baseline 3 แบบ** · top1/top3/MRR/mean rank · แยก ban/pick · leakage test |
| 23 | [ban-intelligence-audit.md](23-ban-intelligence-audit.md) | **ทำไมตาแบนถึงพัง** · trace ทั้งเส้น · แก้สาเหตุที่ docs/22 §4 เขียนผิด |
| 24 | [ban-intelligence-spec.md](24-ban-intelligence-spec.md) | **ban ≠ pick** · `BanPriority ≈ P × Harm` · ประกาศค่าก่อนวัด · กติกา holdout |
| 25 | [ban-benchmark.md](25-ban-benchmark.md) | **ผลหลังแก้ ban** · ban top-1 0.023 → 0.268 · pick identical · ความไม่แน่นอนที่เหลือ |
| 26 | [team-comp-page.md](26-team-comp-page.md) | **ทีมเล่นทรงไหน** · ทีมไม่เล่นชุดเดิมซ้ำ · ทรงจาก hero_class 92.9% · ทำไมไม่ใช้ Composition Engine |
| 27 | [counter-knowledge-audit.md](27-counter-knowledge-audit.md) | **counter ตอนนี้มาจากไหน** · ไม่มี mechanism ไม่มี condition · ข้อมูลเราค้านความรู้ 8/15 |
| 28 | [counter-knowledge-spec.md](28-counter-knowledge-spec.md) | **แบบของ CounterEvidence** · threat→mechanism→capability · pick ≠ ban · เขียนก่อนลงมือ |
| 29 | [counter-knowledge-report.md](29-counter-knowledge-report.md) | **ผล M1** · coverage 6.6% ของตาจริง · UNKNOWN 79.8% · ยังไม่เปิดน้ำหนักอะไร |
| 30 | [engine-version.md](30-engine-version.md) | **ล็อกเวอร์ชัน + หน้าต่างสะอาด** · fingerprint สามชั้น · clean window ยังว่าง 0 เกม |
| 31 | [hero-knowledge-coverage.md](31-hero-knowledge-coverage.md) | **รู้อะไรเกี่ยวกับฮีโร่บ้าง** · A 18 · B 18 · C 83 · คิวที่ควรกรอกก่อน |
| 32 | [synergy-audit.md](32-synergy-audit.md) | **synergy ก่อนแตะ** · co-occurrence ≠ synergy · 15.9% ของคู่เปลี่ยนเครื่องหมาย |

> ลำดับความน่าเชื่อถือเมื่อเอกสารขัดแย้งกัน: **09/21/22/25/26/29/30/31/32 > 10 > 17–19, 23, 27 > 08 > 01–07, 20, 24, 28**
> (เลขกลุ่มแรกคือผลจากการรันจริง · กลุ่มสองคือการตรวจโค้ด · กลุ่มสามคือแผนที่ยังไม่ได้ทำ)
>
> ⚠️ [docs/22 §4](22-benchmark-foundation.md) ระบุสาเหตุของปัญหาตาแบนไว้ผิด — ใช้ [docs/23](23-ban-intelligence-audit.md) แทน
> 01–07 เขียนจากแผนแนวคิดแรก · 08 ข้อเท็จจริงจากการค้น · 09 ผลจากการรันจริง
> 10 การเทียบกับ Blueprint ฉบับใหม่ · 11 ออกแบบส่วนที่ Blueprint เพิ่มเข้ามา

## สามเสาหลัก (Blueprint §3)

```
Video Analysis  ·  Draft System  ·  Scouting
                        ↓
                  Macro Planner  →  Intelligence  →  Dashboard
```

รวม 44 โมดูล · สถานะปัจจุบัน ✅ 13 · 🟡 13 · ⬜ 19
ดูแผนที่เต็มใน [10-blueprint-alignment.md](10-blueprint-alignment.md)

## สรุปสั้นที่สุด

โครงการนี้จะสำเร็จหรือล้มเหลวที่ **Milestone 1 เท่านั้น**:
แปลง broadcast video เป็นตาราง `(game_time, player, x, y, confidence, source)`
ที่วัดความแม่นได้ และไม่มี identity switch

ทุกอย่างที่เหลือ — Macro, Profile, Draft, Dashboard, ML — เป็นการต่อยอดจากตารางนั้น
และเป็นงานที่ความเสี่ยงต่ำกว่ามาก

ดังนั้นลำดับความสำคัญของเวลาคือ:

```
Vision + Data Quality   ████████████████████  70%
Macro Engine            █████                 15%
Draft Engine            ███                   10%
Dashboard               ██                     5%
```

## ข้อเท็จจริงที่ตรวจสอบแล้ว (2026-09-06)

| รายการ | ค่า |
|--------|-----|
| แพตช์ปัจจุบัน | 1.63 |
| ฮีโร่ทั้งหมด / ที่มีข้อมูล pro | 126 / 98 |
| แมพ | Antaris Battlefield · 3 เลน · ป่า 4 ส่วนต่อฝั่ง · ผังโซนสร้างจากกฎแล้ว **ยังไม่ยืนยันกับ minimap จริง** |
| Objective | Abyssal Dragon (2:00 ทุก 2 นาที) · Dark Slayer (8:00 ทุก 5 นาที) |
| กติกา draft | Global Ban-Pick = soft fearless (ห้ามใช้ตัวของตัวเองซ้ำในซีรีส์) |
| แหล่งข้อมูล draft | Liquipedia API · ดึงแล้ว 861 เกม จาก RPL ไทย และ GCS ไต้หวัน |
| ภาพประกอบ | hero icon 132 ภาพ (ลิขสิทธิ์ Garena/TiMi ดู [14](14-deployment.md) §2.1) |
| คำถามที่ยังไม่มีคำตอบ | spectator minimap มี fog หรือไม่ · ลำดับ ban/pick · ทิศทางแมพ |

รายละเอียดและแหล่งอ้างอิงอยู่ใน [08-game-reference.md](08-game-reference.md)
