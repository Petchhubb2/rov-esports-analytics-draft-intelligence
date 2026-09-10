# RoV Esports Analytics & Draft Intelligence

ระบบวิเคราะห์ macro จากคลิปแข่ง RoV (Broadcast / Spectator View) และ Draft Simulator

## สถานะ

โครงการแบ่งเป็นสองสายที่เดินคนละความเร็ว

**สาย Draft — ใช้งานได้จริงแล้ว**

- ✅ ข้อมูลจริง 861 เกม · 5 รายการ · 119 ฮีโร่ จาก Liquipedia
- ✅ คำแนะนำ pick/ban ที่ขยับตามตัวที่เปิดมาแล้ว และตามตำแหน่งที่ยังว่าง
- ✅ matchup แยกเลน (context=LANE) · synergy · Global Ban-Pick ระดับซีรีส์
- ✅ Composition Engine — 10 มิติ พร้อม power curve (30 ตัว = 72% ของ pick+ban จริง)
- ✅ Scouting ต่อทีม — hero pool แต่ละเลน และตัวที่ควรแบนใส่ทีมนั้น
- ✅ กระดานเว็บ Draft Room ไฟล์เดียว เปิดออฟไลน์ได้
- ✅ คลังความรู้มาโคร 42 rule ทุกข้อมีที่มากำกับ

**สาย Vision — ติดอยู่ที่ Phase 0**

- ✅ Detector ตรวจ hero icon บน minimap ผ่านเกณฑ์บนชุดสังเคราะห์ 3 จาก 4 seed
- ✅ Zone map พร้อม raster lookup แบบ O(1) สอบเทียบกับ minimap จริงแล้ว
- ❌ tracking / events / pipeline ยังไม่มีโค้ด — **ติดที่ยังไม่มีคลิปแข่งจริง**

สองสายนี้ไม่ขึ้นต่อกัน สาย Draft เดินต่อได้โดยไม่ต้องรอคลิป
รายละเอียดและตัวเลขทั้งหมดอยู่ใน [docs/09-build-log.md](docs/09-build-log.md)

## เริ่มใช้งาน

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"      # Windows
# .venv/bin/pip install -e ".[dev]"        # Linux / macOS

rov doctor        # ตรวจว่าเครื่องพร้อม
rov status        # โครงการเดินมาถึงไหน
pytest -q
```

ต้องมี Python 3.12 ขึ้นไป ยืนยันแล้วว่าใช้กับ 3.14.6 ได้

## คำสั่ง

| คำสั่ง | ทำอะไร |
|--------|--------|
| `rov doctor` | ตรวจไลบรารีและโปรแกรมภายนอก |
| `rov status` | สถานะของแต่ละเฟสเทียบ roadmap |
| `rov probe <video>` | metadata ของคลิป (เตือนถ้าเป็น variable frame rate) |
| `rov zones [file] --out img.png` | ตรวจ zone map และวาดภาพออกมา |
| `rov layout-check <layout.yaml> --video <v>` | วาดกรอบ ROI ทับเฟรมจริง เพื่อยืนยัน Phase 0 |
| `rov eval-synthetic --seeds 4` | วัด detector บน minimap สังเคราะห์ |

### สาย Draft

| คำสั่ง | ทำอะไร |
|--------|--------|
| `rov draft pool` | สถิติรวมทุกลีกที่ดึงมาแล้ว |
| `rov draft sim` | Draft Simulator แบบโต้ตอบ คิดเรื่องตำแหน่งที่ยังว่างด้วย |
| `rov draft scout <ทีม> --since 2026-05-01` | hero pool แต่ละเลนของทีมนั้น และควรแบนอะไรใส่ |
| `rov draft comp <5 ตัวคั่นด้วยจุลภาค>` | วิเคราะห์ composition ของทีม |
| `rov draft counters <ฮีโร่>` | คู่ที่ได้เปรียบและเสียเปรียบ |
| `rov draft meta --a TH --b TW` | เทียบเมต้าระหว่างภูมิภาค |
| `rov draft todo` | ฮีโร่ที่ยังต้องกรอก attribute |
| `rov web --open` | สร้างกระดาน Draft Room เป็นไฟล์เดียว |

### สร้างข้อมูลใหม่

```bash
rov draft heroes-init                           # อัปเดตรายชื่อฮีโร่จากทุกรายการใน cache
python scripts/fetch_hero_traits.py --top 30    # ดึงข้อเท็จจริงของฮีโร่ (ใส่ --live ถ้ายังไม่มีใน cache)
python scripts/apply_hero_assessment.py --write # รวมค่าที่ประเมินไว้เข้า heroes.yaml
python scripts/export_draft_data.py             # ส่งออก JSON สำหรับหน้าเว็บ
python scripts/build_draft_page.py              # สร้างหน้าเว็บไฟล์เดียว
```

## โครงสร้าง

```
packages/core/rov/     ตรรกะทั้งหมด ไม่มี dependency กับ web หรือ HTTP
  domain/              types, enums, geometry
  config/              layout, zones, params (pydantic + YAML)
  ingest/              probe, sampler ตาม PTS
  minimap/             background, detect
  eval/                synthetic generator, detection metrics
  cli/                 typer
  draft/               stats, lanes, matchup, recommend, composition, scouting
  draft/importer/      Liquipedia client (rate limit + cache), parser, hero traits
  macro/               คลังความรู้มาโคร + validator ที่มา
apps/web/              template กระดาน Draft Room
configs/draft/         format (กติกา), heroes (attribute), hero_assessment (ค่าที่ประเมิน)
configs/               zone map, layout, params
docs/                  เอกสารออกแบบ 01-16
knowledge/macro/       rule มาโคร ทุกข้อมี source
tests/                 280 การทดสอบ
scripts/               export/build หน้าเว็บ, fetch_hero_traits, eval_synthetic
```

## เอกสาร

เริ่มที่ [docs/README.md](docs/README.md)

สองไฟล์ที่ควรอ่านก่อน

- [docs/01-assessment.md](docs/01-assessment.md) — ช่องว่าง 10 ข้อที่ต้องปิด
- [docs/09-build-log.md](docs/09-build-log.md) — สิ่งที่วัดได้จริง รวมถึงบั๊กที่เจอและสมมติฐานที่ผิด

## สิ่งที่ต้องทำต่อ

**ทุกอย่างในสาย vision ติดอยู่ที่ข้อเดียว: ยังไม่มีคลิปแข่งจริง**

```bash
rov vods --region TH              # หาคลิป — มี 552 เกมพร้อมลิงก์และเวลาที่เกมเริ่ม
# ดาวน์โหลดแล้ววางที่ data/videos/
rov scan data/videos/<ไฟล์>.mp4    # สแกนหา minimap แล้วเขียนภาพให้ตรวจ
```

ดูวิธีเต็มใน [docs/15-getting-footage.md](docs/15-getting-footage.md)

ขอแค่คลิปเดียวก็ตอบคำถาม Phase 0 ได้ครบ 12 ข้อ
โดยเฉพาะข้อที่บล็อกอยู่คือ **minimap มี fog of war หรือไม่**
ซึ่งค้นเว็บแล้วไม่มีคำตอบ ต้องดูภาพจริงเท่านั้น
