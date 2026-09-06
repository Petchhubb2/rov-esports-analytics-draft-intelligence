# เอกสารออกแบบระบบ — RoV Esports Analytics & Draft Intelligence

เอกสารชุดนี้แปลงแผนแนวคิดใน [`RoV_Esports_Analytics_แผนพัฒนาระบบ.md`](../RoV_Esports_Analytics_แผนพัฒนาระบบ.md)
ให้เป็น **แผนทางเทคนิคที่ลงมือทำได้** — มีสัญญาข้อมูล (data contract), อัลกอริทึม, สคีมา,
และเกณฑ์ผ่าน/ไม่ผ่านของแต่ละเฟส

เอกสารเดิม = "จะทำอะไร"  ·  เอกสารชุดนี้ = "จะทำอย่างไร และรู้ได้อย่างไรว่าทำสำเร็จ"

| # | เอกสาร | เนื้อหา |
|---|--------|---------|
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

> ลำดับความน่าเชื่อถือเมื่อเอกสารขัดแย้งกัน: **09/10 > 08 > 01–07**
> 01–07 เขียนจากแผนแนวคิดแรก · 08 ข้อเท็จจริงจากการค้น · 09 ผลจากการรันจริง
> 10 การเทียบกับ Blueprint ฉบับใหม่ · 11 ออกแบบส่วนที่ Blueprint เพิ่มเข้ามา

## สามเสาหลัก (Blueprint §3)

```
Video Analysis  ·  Draft System  ·  Scouting
                        ↓
                  Macro Planner  →  Intelligence  →  Dashboard
```

รวม 44 โมดูล · สถานะปัจจุบัน ✅ 7 · 🟡 11 · ⬜ 27
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
| แมพ | Antaris Battlefield · 3 เลน · ป่า 4 ส่วนต่อฝั่ง |
| Objective | Abyssal Dragon (2:00 ทุก 2 นาที) · Dark Slayer (8:00 ทุก 5 นาที) |
| กติกา draft | Global Ban-Pick = soft fearless (ห้ามใช้ตัวของตัวเองซ้ำในซีรีส์) |
| แหล่งข้อมูล draft | Liquipedia API · ดึงแล้ว 861 เกม จาก RPL ไทย และ GCS ไต้หวัน |
| คำถามที่ยังไม่มีคำตอบ | spectator minimap มี fog หรือไม่ · ลำดับ ban/pick ที่แน่นอน |

รายละเอียดและแหล่งอ้างอิงอยู่ใน [08-game-reference.md](08-game-reference.md)
