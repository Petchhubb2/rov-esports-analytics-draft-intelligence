# RoV Esports Analytics & Draft Intelligence

ระบบวิเคราะห์ macro จากคลิปแข่ง RoV (Broadcast / Spectator View) และ Draft Simulator

## สถานะ

อยู่ระหว่าง **Phase 1** ยังไม่มีคลิปแข่งจริงเข้าระบบ

- ✅ ฐานราก: domain types, config (layout / zones / params), CLI, ชุดทดสอบ
- ✅ Detector ตรวจ hero icon บน minimap + ชุดประเมินผล
- ✅ Zone map พร้อม raster lookup แบบ O(1)
- ⏳ Phase 0 กับคลิปจริง · HUD reader · tracking · event detection · draft engine

ผลล่าสุดของ detector บนชุดสังเคราะห์: ผ่านเกณฑ์ Milestone 1 ใน 3 จาก 4 seed
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

## โครงสร้าง

```
packages/core/rov/     ตรรกะทั้งหมด ไม่มี dependency กับ web หรือ HTTP
  domain/              types, enums, geometry
  config/              layout, zones, params (pydantic + YAML)
  ingest/              probe, sampler ตาม PTS
  minimap/             background, detect
  eval/                synthetic generator, detection metrics
  cli/                 typer
configs/               zone map, layout, params
docs/                  เอกสารออกแบบ 01-09
tests/unit/            34 การทดสอบ
scripts/               eval_synthetic, diagnose_detect
```

## เอกสาร

เริ่มที่ [docs/README.md](docs/README.md)

สองไฟล์ที่ควรอ่านก่อน

- [docs/01-assessment.md](docs/01-assessment.md) — ช่องว่าง 10 ข้อที่ต้องปิด
- [docs/09-build-log.md](docs/09-build-log.md) — สิ่งที่วัดได้จริง รวมถึงบั๊กที่เจอและสมมติฐานที่ผิด

## สิ่งที่ต้องทำต่อ

1. **หาคลิปแข่งจริง 3 คลิป จาก 2 รายการขึ้นไป** — ทุกอย่างในสาย vision ติดอยู่ตรงนี้
2. ตอบคำถาม Phase 0 ทั้ง 12 ข้อ โดยเฉพาะ **minimap มี fog of war หรือไม่**
   ซึ่งค้นเว็บแล้วไม่มีคำตอบ ต้องเปิดคลิปนับ icon เอง
3. เขียน Liquipedia importer แล้วสั่งรันดึงข้ามคืน (ติด rate limit 60 requests/ชั่วโมง
   จึงควรเริ่มเร็วที่สุด และทำขนานกับงาน vision ได้)
