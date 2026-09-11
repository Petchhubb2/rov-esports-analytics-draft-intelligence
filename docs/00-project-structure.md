# 00 — โครงสร้างโปรเจค

อัปเดตล่าสุด 2026-09-11 · 282 เทสต์ผ่าน · ruff ผ่าน

โปรเจคนี้แบ่งเป็น **สองสาย** ที่เดินคนละความเร็ว ดู [[rov-project-stage]] และ
[docs/09-build-log.md](09-build-log.md) สำหรับรายละเอียดเชิงลึก

- **สาย Draft** — ใช้งานได้จริงแล้ว ข้อมูลจริง 861 เกมจาก Liquipedia
- **สาย Vision** — ยังติดที่ Phase 0 เพราะยังไม่มีคลิปแข่งจริง

```
RoV Esports Analytics & Draft Intelligence/
├── packages/core/rov/      ← ตรรกะหลักทั้งหมด (ไม่มี dependency กับ web/HTTP)
├── apps/                   ← หน้าเว็บ Draft Room + FastAPI (สาย Vision)
├── configs/                ← YAML config: กติกาดราฟต์, ฮีโร่, โซนแมพ
├── knowledge/              ← คลังความรู้มาโคร + ทรานสคริปต์ดิบ
├── docs/                   ← เอกสารออกแบบ 00–16
├── scripts/                ← เครื่องมือ CLI แบบ standalone
├── tests/                  ← 282 เทสต์ (unit + integration)
└── data/                   ← ข้อมูล/แคช/เอาต์พุต (ส่วนใหญ่ git-ignored)
```

---

## 1. `packages/core/rov/` — แกนหลัก (4,099 บรรทัดในสาย draft)

Python package เดียว ไม่ผูกกับ FastAPI หรือเว็บ เรียกได้ทั้งจาก CLI, scripts, และ API

| โมดูล | บรรทัด | สถานะ | ทำอะไร |
|---|---|---|---|
| `draft/` | 4,099 | ✅ ใช้งานได้ | ดราฟต์ทั้งหมด — ดูรายละเอียดหัวข้อ 1.1 |
| `cli/` | 1,263 | ✅ | Typer CLI — `rov <command>` ทุกคำสั่ง |
| `config/` | 654 | ✅ | โหลด/validate YAML: layout, zones, params (pydantic) |
| `ingest/` | 620 | ✅ | probe วิดีโอ, sampler ตาม PTS, ingest service + DB |
| `domain/` | 571 | ✅ | enums, geometry, types ที่ใช้ร่วมกันทั้งโปรเจค |
| `eval/` | 502 | ✅ | ตัวสร้างชุดสังเคราะห์ + วัดผล detector |
| `minimap/` | 480 | ✅ | background subtraction + hero icon detector |
| `store/` | 470 | ✅ | SQLAlchemy models, repo, db connection (System 01) |
| `macro/` | 208 | ✅ | โหลด/validate คลังความรู้มาโคร (`knowledge/macro/`) |
| `tracking/` | 0 | ❌ ว่าง | รอคลิปแข่งจริง |
| `pipeline/` | 0 | ❌ ว่าง | รอคลิปแข่งจริง |
| `mapping/` | 0 | ❌ ว่าง | รอคลิปแข่งจริง |
| `events/` | 0 | ❌ ว่าง | รอคลิปแข่งจริง |
| `broadcast/` | 0 | ❌ ว่าง | มีแค่สคีมา ROI ยังไม่มีตัวอ่าน HUD |

### 1.1 `draft/` แยกย่อย — หัวใจของโปรเจค

```
draft/
├── heroes.py          Hero, HeroDB — attribute ฮีโร่ (engage/peel/scaling/...)
│                      ห้ามเดาค่า ต้องมี filled_kind (human/assistant/derived)
├── composition.py     Composition Engine — 10 มิติ + power curve จาก 5 ตัว
├── recommend.py       คำแนะนำ pick/ban ถ่วงด้วย meta/winrate/counter/synergy
├── state.py           DraftFormat, DraftState — state machine ของการดราฟต์
├── stats.py           HeroStat, DraftStats — pick/ban/winrate พร้อม shrinkage
├── lanes.py           อนุมานเลนจากช่อง roster (t1h1..t1h5) + matchup แยกเลน
├── meta.py            Region, PooledStats — รวมข้อมูลข้ามลีก/ฤดูกาล
├── scouting.py        โปรไฟล์ทีม + target_bans — ใช้ team1/team2/date จาก parser
├── seed.py            สร้าง/อัปเดต heroes.yaml จากข้อมูลจริง (ไม่เดา attribute)
└── importer/
    ├── liquipedia.py  HTTP client คุม rate limit (55/ชม., cache ทุก response)
    ├── ratelimit.py   ตัวจำกัดอัตรา แยกจาก client เพื่อเทสต์ได้อิสระ
    ├── cache.py       ResponseCache — เก็บ response เป็นไฟล์ .json.gz
    ├── parser.py      แกะ wikitext เป็น SeriesDraft/GameDraft + HERO_ALIASES
    ├── wikitext.py    ตัวแกะ template/section ทั่วไปของ MediaWiki
    ├── heroinfo.py    ดึงรายชื่อฮีโร่ + class จาก Portal:Heroes
    ├── herotraits.py  ดึงข้อเท็จจริงจากหน้าฮีโร่ (dmg, CC, skill effects)
    ├── crawl.py       วนดึงหลายหน้า พร้อม dry-run เป็นค่าเริ่มต้น
    └── assets.py      ดาวน์โหลดรูปฮีโร่ + zone map assets
```

**หลักการที่บังคับใช้ทั้งโมดูล:** ห้ามเดาค่าเชิงคุณภาพ, ทุก win rate ต้องผ่าน
shrinkage, ทุก rule ต้องมี source, ทุก hero attribute ต้องมี `filled_kind`
(ดู [[rov-data-provenance-rule]])

---

## 2. `apps/` — หน้าตาที่ผู้ใช้เห็น

```
apps/
├── api/                    FastAPI (สาย Vision — อัปโหลด/คิววิดีโอเท่านั้น)
│   ├── main.py              7 endpoints: /health, /videos/*, /matches/*, /jobs/*
│   └── schemas.py           Pydantic response models
└── web/                     Draft Room (สาย Draft — หน้าหลักที่ใช้จริง)
    ├── draft_board.tpl.html  template เดียว ~3,000 บรรทัด (HTML+CSS+JS ในไฟล์เดียว)
    └── README.md             วิธี build ใหม่เมื่อดึงข้อมูลรายการเพิ่ม
```

**Draft Room** เป็นไฟล์ static เดียวที่ฝังข้อมูล JSON ไว้ข้างใน (`__DATA__`)
เปิดในเบราว์เซอร์ได้ทันทีโดยไม่ต้องมี server — เลือกแบบนี้เพราะ (1) ห้องซ้อม/
หลังเวทีเน็ตไม่นิ่ง (2) ดราฟต์มีเวลาจำกัดต่อตา latency เป็นศูนย์สำคัญกว่า
(3) ลิขสิทธิ์ภาพฮีโร่ยังไม่เคลียร์ให้ deploy public ได้

ผลข้างเคียง: สูตรคำนวณบางส่วน (weights, composition, sequence กติกา) ต้อง
**เขียนซ้ำเป็น JavaScript** เพราะเบราว์เซอร์เรียก Python ไม่ได้ —
`tests/unit/test_web_board.py` คอยจับไม่ให้สองชุดเพี้ยนจากกัน

4 แท็บบนกระดาน: **Draft Room** (ดราฟต์ + แผนคอมพ์ + สแกนคู่แข่ง) ·
**ตัวแก้/แพ้ทาง** · **แมพ** (zone map + minimap จริง) · **มาโคร/แผน** (คลังความรู้)

---

## 3. `configs/` — การตั้งค่าที่แก้ได้โดยไม่ต้องแตะโค้ด

```
configs/
├── draft/
│   ├── format.yaml            กติกา ban/pick, Global Ban-Pick, side selection,
│   │                          turn clock — แต่ละข้อมีธง verified แยกกัน
│   ├── heroes.yaml             attribute ของฮีโร่ 119 ตัว (เครื่องสร้าง/อัปเดตได้)
│   └── hero_assessment.yaml    ค่าที่ประเมินไว้ 30 ตัว (คนเขียน ห้ามเครื่องทับ)
└── zones/
    └── rov_map_v1.yaml         โซนแมพ Antaris Battlefield สอบเทียบกับ minimap จริง
```

`heroes.yaml` กับ `hero_assessment.yaml` แยกไฟล์เพราะมีเจ้าของต่างกัน —
สะพานเชื่อมทางเดียวคือ `scripts/apply_hero_assessment.py`

---

## 4. `knowledge/` — คลังความรู้มาโคร

```
knowledge/
├── macro/                      42 rule แบ่งตามหมวด — ทุกข้อมี source กำกับ
│   ├── draft/                    ban_pick_principles, advanced_traps
│   ├── hero/                     rouie, carry_tempo
│   ├── jungle/, objective/, opening/, tempo/, wave/
└── raw/                         ทรานสคริปต์คลิปสอนดิบ (1.4MB รวม)
    ├── rov_transcripts_complete.md   730KB — ต้นทางหลัก
    └── bac_vs_bru, carrybru, darf, marco_ru, pro101
```

Rule ทุกข้อมี `source.type` เป็นหนึ่งใน `game_client` (ตัวเกมบอกเอง) /
`derived_from_data` (คำนวณจากแมตช์จริง) / `coach_input` / `literature` /
`assumption` — ข้อที่เป็น `assumption` ห้ามมี confidence สูง (บังคับด้วย validator)

---

## 5. `docs/` — เอกสารออกแบบ (00–16)

| กลุ่ม | ไฟล์ | เนื้อหา |
|---|---|---|
| ภาพรวม | 00 (ไฟล์นี้), README | จุดเริ่มอ่าน |
| ประเมิน/สถาปัตยกรรม | 01–03 | ช่องว่างที่ต้องปิด, สถาปัตยกรรม, data contracts |
| สาย Vision | 04–05, 16 | vision pipeline, macro events, map guide |
| Roadmap/deploy | 07, 14–15 | เฟส + gate, deployment, การหาคลิปแข่ง |
| อ้างอิงเกม | 08 | patch, กติกา, ข้อเท็จจริงที่ยืนยันแล้ว |
| **build log** | **09** | **บันทึกทุกรอบที่ทำจริง รวมบั๊กที่เจอ — น้ำหนักสูงสุดเวลาเอกสารขัดกัน** |
| สาย Draft | 06, 10–13 | draft engine, blueprint alignment, cross-league meta, simulator |

**ลำดับความน่าเชื่อถือเมื่อเอกสารขัดกัน:** 09 > 08 > อื่น ๆ ทั้งหมด
(เพราะ 09 คือสิ่งที่วัดได้จริง ส่วนที่เหลือคือแผนตอนเริ่มต้น)

---

## 6. `scripts/` — เครื่องมือ standalone

```
scripts/
├── export_draft_data.py       รวมข้อมูล draft ทั้งหมดเป็น draft_data.json
├── build_draft_page.py        ฝัง JSON ลง template → draft_board.html
├── fetch_hero_traits.py       ดึงข้อเท็จจริงฮีโร่จาก Liquipedia → hero_traits.json
├── apply_hero_assessment.py   รวม hero_assessment.yaml เข้า heroes.yaml
├── build_minimap.py           ประกอบ minimap จากภาพต้นทาง
├── gen_zone_map.py            สร้าง zone map raster จาก config
├── rectify_map.py             แก้ perspective ของภาพแผนที่
├── eval_synthetic.py          รัน eval บนชุด minimap สังเคราะห์
├── diagnose_detect.py         debug detector บนเฟรมจริง
└── pg-start.ps1               สตาร์ท PostgreSQL local (Windows)
```

ลำดับรันเมื่อดึงข้อมูล draft รายการใหม่:
```bash
rov draft import "ชื่อรายการ" --live
rov draft heroes-init                           # อัปเดตรายชื่อฮีโร่
python scripts/fetch_hero_traits.py --top 30    # ดึงข้อเท็จจริง (ถ้ายังไม่มี)
python scripts/apply_hero_assessment.py --write # รวมค่าประเมินเข้า heroes.yaml
python scripts/export_draft_data.py             # → draft_data.json
python scripts/build_draft_page.py              # → draft_board.html
```

---

## 7. `tests/` — 282 เทสต์

```
tests/
├── unit/                       เทสต์แยกโมดูล ไม่แตะเครือข่าย/ดิสก์จริง
│   ├── test_draft_engine.py      recommend, weights, normalize_hero_id
│   ├── test_draft_parser.py      แกะ wikitext → SeriesDraft
│   ├── test_draft_state.py       state machine, Global Ban-Pick
│   ├── test_hero_traits.py       herotraits.py + ความสอดคล้องของ assessment
│   ├── test_lanes.py             อนุมานเลนจากช่อง roster
│   ├── test_meta.py              รวมข้อมูลข้ามลีก
│   ├── test_scouting.py          โปรไฟล์ทีม, target_bans
│   ├── test_web_board.py         คุม JS ↔ Python ไม่ให้เพี้ยนจากกัน
│   ├── test_config.py            layout/zones/params validation
│   ├── test_detect.py            minimap hero icon detector
│   ├── test_assets.py            asset manifest, zone map verification
│   ├── test_importer.py          Liquipedia client, rate limiter, cache
│   └── test_macro_plays.py       macro knowledge base + validator
├── integration/
│   └── test_ingestion.py         FastAPI endpoints แบบ end-to-end
└── fixtures/
    └── liquipedia_rpl_sample.wikitext   ตัวอย่าง wikitext จริงสำหรับเทสต์ parser
```

รัน `pytest -q` จาก root — pythonpath ตั้งไว้ใน `pyproject.toml` แล้ว

---

## 8. `data/` — ข้อมูล (ส่วนใหญ่ git-ignored)

| โฟลเดอร์ | ขนาด | เก็บใน git? | เนื้อหา |
|---|---|---|---|
| `hero_traits.json` | 12KB | ✅ | ข้อเท็จจริงฮีโร่ที่ดึงมาแล้ว (input ของ hero_assessment) |
| `assets/` | 6.3MB | ❌ | รูปฮีโร่ + แผนที่ (ลิขสิทธิ์ยังไม่เคลียร์) |
| `cache/liquipedia/` | 315KB | ❌ | response cache ของ Liquipedia API (.json.gz) |
| `exports/` | 77MB | ❌ | draft_data.json, draft_board.html, ภาพขั้นตอนทำแผนที่ |
| `videos/` | 62MB | ❌ | คลิปทดสอบ (ยังไม่มีคลิปแข่งจริง) |
| `groundtruth/` | 0 | ✅ (โครง) | รอ label จริงจาก Phase 0 |

---

## 9. ไฟล์ระดับ root

| ไฟล์ | คืออะไร |
|---|---|
| `README.md` | จุดเริ่มต้น — สถานะ, คำสั่ง, quick start |
| `pyproject.toml` | dependencies, ruff config, pytest config |
| `RoV_Esports_Analytics_FINAL_Blueprint_and_Prompt.md` | เอกสารตั้งต้นโปรเจค (Blueprint ที่ docs อ้างอิงเป็น §เลข) |
| `RoV_Esports_Analytics_แผนพัฒนาระบบ.md` | แผนพัฒนาฉบับภาษาไทย |

---

## สรุปเชิงสถิติ

- **282 เทสต์** ผ่านทั้งหมด, ruff clean
- **4,099 บรรทัด** ในสาย draft (ใช้งานได้แล้ว) เทียบกับ **0 บรรทัด** ใน 5 โมดูลของสาย vision
- **861 เกมจริง** จาก 5 รายการ (RPL 2025/2026, GCS 2026), **119 ฮีโร่**
- **30/119 ฮีโร่** มี attribute ครบ = **72% ของ pick+ban จริง** ในข้อมูล
- **42 rule** ในคลังความรู้มาโคร ทุกข้อมี source
