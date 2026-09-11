# 17 — Intelligence Audit

ตรวจเมื่อ 2026-09-11 · ก่อนแก้โค้ดแม้แต่บรรทัดเดียว
สถานะตั้งต้น: **282 เทสต์ผ่าน · ruff ผ่าน · ไม่มีการแก้ไขใด ๆ ในรอบ audit นี้**

> **ข้อสรุปหลักของ audit นี้**
> ระบบเดิม *ไม่ได้* ออกแบบมาผิด — [docs/06-draft-engine.md §3.4 และ §7](06-draft-engine.md)
> ออกแบบ trait-based counter และ output contract (`fills_gaps` / `creates_gaps` /
> per-component confidence / `data_basis`) ไว้แล้วตั้งแต่ต้น และตรงกับสิ่งที่
> `external_knowledge/rov-claude-kit/specs/` ขอแทบทุกข้อ
>
> **ช่องว่างคือการลงมือทำ ไม่ใช่การออกแบบ** ดังนั้นงานที่ควรทำคือ
> "เติมสิ่งที่ออกแบบไว้แล้วแต่ยังไม่ได้เขียน" ไม่ใช่ "ออกแบบใหม่"

---

## 0. แหล่งข้อมูลใหม่ที่เข้ามารอบนี้

`external_knowledge/rov-claude-kit/` (353KB) — ชุดความรู้ที่สกัดจาก NotebookLM

| ไฟล์ | ขนาด | เนื้อหาที่ใช้ได้ทันที |
|---|---|---|
| `knowledge/counter.md` | 22KB | 5 direct counter (CTR-001..005) · role counter 3 กลุ่ม · composition counter 2 case · problem-based 4 ข้อ · counter rule 4 ข้อ · tag system |
| `knowledge/synergy.md` | 31KB | 8 hero pair · role synergy 5 คู่ · composition synergy 4 แบบ · synergy rule 5 ข้อ · JSON schema พร้อม score_bonus |
| `knowledge/hero.md` | 37KB | โปรไฟล์เต็ม 13 ตัว — role, tags, power spike, CC/engage/peel/burst/scaling, required conditions, win condition, counters, countered_by, synergies, macro requirements |
| `knowledge/draft.md` | 25KB | 6 หลักการ · 7 decision rule · workflow 4 เฟส · 8 evaluation factor · lookahead 3 สถานการณ์ · composition problem 4 แบบ |
| `knowledge/macro.md` | 26KB | หลักการ · IF/THEN/BECAUSE rule · timeline · role interaction · objective macro |
| `specs/*.md` | 10KB | ข้อเสนอเชิงสถาปัตยกรรม 6 ไฟล์ |

**คุณภาพ:** ทุกข้อมี label `[FACT / OBSERVATION / INFERENCE / OPINION]` + เลขอ้างอิง
+ ชื่อคลิปต้นทาง ซึ่ง**เข้ากับระบบ provenance ของโปรเจคนี้ได้ทันที**

**ข้อควรระวังที่ต้องเขียนไว้ให้ชัด**

1. `specs/` เป็น **ข้อเสนอ ไม่ใช่ข้อเท็จจริงของเกม** — `README.md` ของ kit เขียนไว้เอง
2. ต้นทางของ kit คือคลิป YouTube/TikTok **ชุดเดียวกับที่อยู่ใน `knowledge/raw/` อยู่แล้ว**
   (Draft 101, BAC-BRU RPL winter 2026, Rouie basic macro ฯลฯ) จึงไม่ใช่แหล่งอิสระ
   ที่จะเอามายืนยันกันเองได้ — ต้องถือเป็น `coach_input` ชั้นเดียว
3. ตัวเลข score bonus ใน kit (`+30%`, `-20%`, `+15%`) เป็นข้อเสนอจากผู้สกัด
   **ไม่ใช่ค่าที่วัดจากแมตช์** ต้องเก็บเป็น config และต้อง fit กับข้อมูล 861 เกมก่อนใช้

**จุดที่ kit ยืนยันของเดิมได้ 1 ข้อ** — `knowledge/draft.md §3` ระบุ workflow เป็น
`Ban1 → Pick 1-3 → Ban2 → Pick 4-5` ซึ่ง**ตรงกับโครงสร้าง 3+2 ใน `configs/draft/format.yaml`**
(phase 1 ได้ทีมละ 3 pick, phase 2 ได้ทีมละ 2) ยังไม่ยืนยันลำดับสลับภายในเฟส
แต่ยืนยันโครงสร้างได้ — เดิมทั้งก้อนเป็นการเดา ตอนนี้เหลือเฉพาะลำดับสลับที่ยังเดา

---

## 1. Current Architecture

```
                    configs/draft/*.yaml          knowledge/macro/*.yaml
                    (กติกา + attribute)            (42 rule + source)
                            │                              │
        data/cache/liquipedia ──> importer/ ──> stats/lanes/meta ──┐
        (861 เกม · 305 ซีรีส์)                                      │
                            │                                      ▼
                            └──────────────> recommend.py <── composition.py
                                                   │                │
                                    ┌──────────────┴────────┐       │
                                    ▼                       ▼       ▼
                              cli/main.py            export_draft_data.py
                              (rov draft sim)                 │
                                                              ▼
                                                   draft_board.tpl.html
                                                   (สูตรถูกเขียนซ้ำเป็น JS)
```

**สิ่งที่ดีและต้องรักษาไว้**

- `packages/core/rov/` ไม่มี dependency กับ web/HTTP — เรียกได้จากทุกที่
- ทุกตัวเลขสถิติผ่าน shrinkage (`SHRINKAGE_K = 30`) ไม่มี win rate ดิบหลุดออกมา
- `Hero.u()` โยน exception แทนคืนค่ากลาง — ระบบยอม "ไม่รู้" ดีกว่าเดา
- `MacroRule` มี validator บังคับ `assumption` ห้าม confidence HIGH
- มีเทสต์คุม Python↔JS parity อยู่แล้ว 6 ตัว

---

## 2. Current Recommendation Flow

`packages/core/rov/draft/recommend.py` (357 บรรทัด)

```
recommend(state, pooled, lane_usage, lanes)
  │
  ├─ turn = state.current                       ตาไหน ทีมไหน ban หรือ pick
  ├─ subject = turn.team หรือ opponent          ★ ตอนแบนมองจากมุมศัตรู
  ├─ legal = state.legal_moves() - locked       ★ Global Ban-Pick ตัดตัวที่ใช้ไม่ได้
  ├─ need = needed_lanes(ours, lane_usage)      เลนที่ยังไม่มีตัวหลัก
  ├─ w = weights_for(n_enemy, n_ally)           ★ น้ำหนักไหลตามข้อมูลที่เปิดมา
  │
  └─ สำหรับทุก candidate ที่ picks >= min_games:
        meta     = presence_rate      scale(p_lo, p_hi)
        winrate  = adjusted_win_rate  scale(0.42, 0.58)
        counter  = mean counter_score vs enemy picks   scale(-3, +3)
        synergy  = mean counter_score with ally picks  scale(-3, +3)
        base     = Σ w[k] * scaled[k]
        total    = base * (ROLE_FLOOR + (1-ROLE_FLOOR) * role_fit)
```

★ = จุดแข็งที่ออกแบบดีแล้ว ห้ามรื้อ

**ปัญหาเชิง intelligence ของ flow นี้**

| # | ปัญหา | ผลที่เกิด |
|---|---|---|
| R1 | มีแค่ **4 factor** | ตอบคำถาม 10 ข้อใน PRIMARY GOAL ได้ 2 ข้อ (ข้อ 1 บางส่วน, ข้อ 9 บางส่วน) |
| R2 | **ไม่รู้จัก composition เลย** | `recommend.py` ไม่ import `composition.py` แม้แต่บรรทัดเดียว — แนะนำ pick โดยไม่รู้ว่าทีมขาด frontline |
| R3 | **ไม่มี lookahead** | ตอบไม่ได้ว่า "ศัตรูน่าจะตอบอย่างไร" |
| R4 | `reasons` เป็น `list[str]` แบนราบ | อธิบายได้แต่ trace ไม่ได้ว่าเหตุผลข้อไหนมาจาก factor ไหน |
| R5 | **ไม่มี `confidence` ต่อคำแนะนำ** | มีแค่ `reliable` (bool, games>=15) ซึ่งหยาบเกินไป |
| R6 | **ไม่มี `creates_gaps`** | บอกได้ว่า pick นี้ดี แต่บอกไม่ได้ว่ามันสร้างจุดอ่อนอะไรใหม่ |
| R7 | ใช้ `pooled.matchups` (context=TEAM) | `lane_matchups` 680 คู่ถูกคำนวณและ export แล้ว แต่ `recommend()` ไม่เคยเรียก |
| R8 | **ไม่เชื่อมกับ macro knowledge** | 42 rule มีอยู่ แต่ `recommend.py` ไม่รู้จัก |

---

## 3. Current Composition Scoring

`packages/core/rov/draft/composition.py` (300 บรรทัด) — ทำงานได้ตั้งแต่ 2026-09-10

**สิ่งที่ทำถูกและต้องรักษา:** ไม่ใช้ค่าเฉลี่ยกับทุกมิติ

| ฟังก์ชันรวม | ใช้กับ | เหตุผล |
|---|---|---|
| `_top_weighted(0.7, 0.3)` | frontline, engage, disengage, peel, objective | มีคนเก่งหนึ่งคนก็พอ |
| `_top_weighted(0.8, 0.2)` | splitpush | ยิ่งพึ่งคนเดียวกว่าเดิม |
| `_saturating_sum(180)` | cc_hard | สะสมได้แต่ผลตอบแทนลดลง |
| `0.45*min + 0.55*mean` | waveclear | จุดอ่อนที่สุดเป็นตัวกำหนด |
| `_max_lane_matching` (Kuhn) | role_balance | ★ ต้องเป็น maximum matching จริง ไม่ใช่ไล่จัดตามลำดับ |
| `mean` | power curve | |

**10 มิติที่มี:** role_balance, damage_mix, frontline, engage, disengage,
crowd_control, peel, objective, waveclear, split_push + power curve (early/mid/late)

### เทียบกับ 18 มิติที่ STEP 3 ขอ

| มิติที่ขอ | มีแล้ว? | หมายเหตุ |
|---|---|---|
| Role coverage | ✅ | `role_balance` ใช้ Kuhn matching |
| Frontline | ✅ | |
| Engage | ✅ | |
| Disengage | ✅ | |
| Peel | ✅ | |
| Wave Clear | ✅ | |
| Objective Control | ✅ | |
| Scaling | ✅ | power curve |
| **Flexibility** | ❌ | มีข้อมูล `lane_usage` ครบ 120 ตัวแล้ว แต่ไม่มีมิติ — **และตอนนี้ยัง *ลงโทษ* flex ด้วย** (ดู §10 W3) |
| **Burst** | ⚠️ | `damage.profile` มีค่าใน 30 ตัวแล้ว แต่ไม่มีมิติที่ใช้ |
| **Sustained DPS** | ⚠️ | เช่นเดียวกัน |
| **Poke** | ⚠️ | `utility.poke` กรอกแล้ว 30 ตัว แต่ `analyze()` ไม่ได้ใช้ |
| **Power Spike** | ⚠️ | มี power curve แต่ไม่มีการหา "ช่วงที่พีคที่สุด" หรือเทียบกับศัตรู |
| **Team Fight Pattern** | ❌ | kit ระบุ 4 แบบ: Front-to-Back / Dive / Poke-Siege / Split Push |
| **Backline Access** | ❌ | kit เรียก Dive — ต้องใช้ mobility + range + engage |
| **Backline Protection** | ❌ | ต่างจาก peel: peel = ช่วยได้, protection = ศัตรูเข้าไม่ถึง |
| **Lane Safety** | ❌ | ต้องใช้ `lane_matchups` ที่มีอยู่แล้ว 680 คู่ |
| **Macro Dependency** | ❌ | kit เรียก `required_conditions` — มีใน hero.md 13 ตัว |

**สรุป: มี 8/18 · มีข้อมูลพร้อมแต่ยังไม่มีมิติ 4/18 · ยังไม่มีทั้งข้อมูลและมิติ 6/18**

`utility` ที่กรอกครบ 12 ช่องแต่ `analyze()` ใช้แค่ 8 ช่อง —
**`poke`, `sustain`, `mobility`, `cc_soft` กรอกแล้วแต่ไม่มีใครอ่าน**

---

## 4. Current Counter Logic

```python
# recommend.py:_counter_against
for e in enemies:
    m = pooled.matchups.get((hero, e))      # context=TEAM
    if m is None or m.games < MIN_PAIR_GAMES: continue
    total += m.counter_score(prior)
total /= len(enemies)                        # หารด้วยจำนวนศัตรูทั้งหมด
```

`counter_score = (adjusted_win_rate - prior) * 100 * confidence`
โดย `confidence = games / (games + 30)`

**คุณสมบัติที่ดี:** คู่ที่ไม่มีข้อมูลได้ 0 อัตโนมัติ ไม่ใช่ค่าสุดโต่ง ·
ถ่วงด้วยขนาดตัวอย่างในตัวเอง

### เทียบกับ 5 ชั้นที่ STEP 6 ขอ

| ชั้น | สถานะ | รายละเอียด |
|---|---|---|
| 1. Hero Counter | ⚠️ มีแบบ empirical เท่านั้น | รู้ว่า A ชนะ B กี่ % แต่**ไม่รู้ว่าทำไม** · kit มีกลไก 5 ข้อพร้อม mechanism/condition/risk |
| 2. Role Counter | ❌ ไม่มี | kit มี 3 กลุ่ม (Assassin / Tank-CC / Poke-Siege) |
| 3. Composition Counter | ❌ ไม่มี | kit มี 2 case พร้อม threat→problem→response→candidate |
| 4. Problem-Based Counter | ❌ ไม่มี | kit มี 4 คำถาม — นี่คือสิ่งที่โค้ชคิดจริง |
| 5. Win-Condition Counter | ❌ ไม่มี | ยังไม่มีแนวคิด win condition ในระบบเลย |

**ช่องว่างที่ใหญ่ที่สุด:** ตอนนี้ counter เป็น *ตัวเลข* ล้วน
ถามว่า "ทำไม Billow ถึงกด Rouie" ระบบตอบได้แค่ "win rate สูงกว่า X%"
ทั้งที่ kit บอกกลไกไว้ชัด: *Burst ฆ่าก่อนวงวาร์ปทำงาน / ผลักออกจากวง*

`docs/06 §3.4` ออกแบบ `trait_counter()` ไว้แล้ว — **ยังไม่ได้เขียน**
`strong_against_traits` / `weak_against_traits` มีใน model, มีครบ 119 ตัวใน YAML,
**ว่างทั้ง 119 ตัว และไม่มีโค้ดบรรทัดไหนอ่านมันเลย**

---

## 5. Current Synergy Logic

```python
# recommend.py:_synergy_with — โครงสร้างเหมือน counter ทุกประการ
key = (hero, a) if hero < a else (a, hero)
total += syn[key].counter_score(prior)
```

`compute_synergies()` นับคู่ในทีมเดียวกัน เก็บทิศทางเดียว

**ปัญหาที่โค้ดเองยอมรับไว้ใน docstring:**
> "ค่านี้ปนเปื้อนด้วย 'ทีมเก่งเล่นคู่นี้บ่อย' ยังไม่ได้หักออก"

`stats.py` มี `expected_synergy()` อ้างถึงใน comment แต่ `recommend.py` ไม่ได้เรียก

### เทียบกับ 7 ชนิดที่ STEP 7 ขอ

| ชนิด | สถานะ |
|---|---|
| Ability Synergy | ❌ — kit มี 7 tag: Global_Warp / Gold_Boost / AoE_Pull_Burst / Double_Ult / Poke_Siege / Front_to_Back / Tag_Farm |
| Role Synergy | ❌ — kit มี 5 คู่ (Jungle+Mid, Roam+Mid, Roam+Jungle, Exp+Jungle, Support+Carry) |
| Tempo Synergy | ⚠️ — มี power curve แต่ไม่ได้เทียบกันระหว่างคู่ |
| Objective Synergy | ❌ |
| Teamfight Synergy | ❌ |
| Macro Synergy | ❌ |
| Win-condition Synergy | ❌ |
| **(ที่มี) Empirical pair** | ✅ — 730 คู่ที่ ≥8 เกม |

**ที่ขาดที่สุด:** `condition` — kit บอกว่า Rouie+Capheny ดี **โดยมีเงื่อนไข**
ว่าต้องมีเลนข้างที่ประคองตัวเองได้ เพราะ Rouie ต้นเกมอ่อน
ระบบเดิมเก็บได้แค่ "คู่นี้ชนะ X%"

---

## 6. Current Meta / Winrate Logic

| ส่วน | สูตร | ประเมิน |
|---|---|---|
| meta | `presence_rate = (picks+bans)/total_games` scale ตาม min/max ของ candidate | ✅ ถูกต้อง · แต่ **ไม่แยกตามแพตช์หรือช่วงเวลา** |
| winrate | `(wins + 30*0.5)/(picks + 30)` scale(0.42, 0.58) | ✅ shrinkage ถูกหลัก |
| weights | `counter = 0.08 + 0.40*e`, `synergy = 0.05 + 0.25*a` โดย `e = n/(n+1.2)` | ✅ ไหลตามข้อมูลที่เปิดมา — ออกแบบดี |

**ปัญหา M1:** ข้อมูล 861 เกมกินเวลา 2025-08-23 ถึง 2026-09-06 (หนึ่งปีเต็ม)
ข้ามหลายแพตช์ แต่ `meta` กับ `winrate` รวมทั้งหมดเป็นก้อนเดียว
`scouting.py` มี `filter_since()` แล้วแต่ `recommend()` ไม่ได้ใช้

**ปัญหา M2:** `weights_for()` เขียนใน docstring ว่า
> "ยังไม่ผ่านการ validate ด้วยผลแพ้ชนะ ต้อง fit ด้วย logistic regression เมื่อมีข้อมูลพอ"

ตอนนี้มี 861 เกมแล้ว — **พอที่จะ fit ได้ แต่ยังไม่ได้ทำ**

---

## 7. Current Hero Data Coverage

| กลุ่ม | จำนวน | ครอบคลุม pick+ban |
|---|---|---|
| กรอกครบ (`assistant`) | 30 | **72.3%** |
| กรอกบางส่วน | 0 | 0% |
| ว่างทั้งหมด | 89 | 27.7% |

ทุกตัวที่กรอกแล้วเป็น `filled_kind: assistant` — **ยังไม่มีตัวไหนเป็น `human`**

รายละเอียดเต็มและลำดับที่ควรกรอกอยู่ใน [docs/18-hero-data-coverage.md](18-hero-data-coverage.md)

---

## 8. Current Provenance System

**นี่คือส่วนที่แข็งแรงที่สุดของโปรเจค**

| กลไก | ที่อยู่ | บังคับด้วย |
|---|---|---|
| `Hero.filled_kind` (human/assistant/derived) | `heroes.py:108` | เทสต์ `test_filled_heroes_all_declare_where_the_numbers_came_from` |
| `Hero.u()` โยน exception เมื่อยังไม่กรอก | `heroes.py` | เทสต์ `test_reading_unfilled_attribute_raises_not_guesses` |
| `IncompleteDataError` พร้อมบอกช่องที่ขาด | `composition.py` | เทสต์ `test_error_names_the_missing_hero_and_fields` |
| คำเตือน assistant บนทั้ง CLI และเว็บ | `composition.py` + template | เทสต์ |
| `MacroRule.source` บังคับมี | `plays.py` | pydantic |
| `assumption` ห้าม confidence HIGH | `plays.py` validator | เทสต์ |
| `disagrees` ห้าม confidence HIGH | `plays.py` validator | เทสต์ |
| `derived_from_data` ต้องมีตัวเลข | `plays.py` validator | เทสต์ |
| ตัวเลขทุกตัวบนเว็บมี n กำกับ | template | — |

### ช่องว่างของ provenance

| # | ช่องว่าง |
|---|---|
| P1 | **ไม่มี label FACT/OBSERVATION/INFERENCE/OPINION/UNKNOWN** — kit ใช้ 5 ระดับนี้ ระบบเรามีแค่ 3 (`human`/`assistant`/`derived`) ซึ่งตอบ "ใครให้ค่า" แต่ไม่ตอบ "ค่านี้เป็นข้อเท็จจริงหรือความเห็น" |
| P2 | `Hero` ไม่มีช่อง `sources[]` — มีแค่ `notes` เป็นข้อความอิสระ |
| P3 | `MatchupStat` / `SynergyStat` ไม่มี provenance เลย (เป็น derived ล้วนโดยปริยาย แต่ไม่ได้ประกาศ) |
| P4 | `Suggestion` ที่ออกจาก `recommend()` **ไม่มี field `confidence` และ `sources`** |
| P5 | `UNKNOWN` ยังไม่ใช่ค่าที่ระบบพูดออกมาได้ — `None` ถูกใช้แทน แต่ไม่มีการแยก "ไม่มีข้อมูล" ออกจาก "มีข้อมูลแต่แปลว่าศูนย์" |

---

## 9. Python / JS Duplication

สรุปที่นี่ · รายละเอียดเต็มใน [docs/19-python-js-parity.md](19-python-js-parity.md)

| # | ตรรกะ | Python | JS | มีเทสต์คุม? |
|---|---|---|---|---|
| 1 | ลำดับ ban/pick | `format.yaml` | `SEQ` | ✅ |
| 2 | จำนวน ban/pick | `format.yaml` | `BANS`/`PICKS` | ✅ |
| 3 | Global Ban-Pick | `format.yaml` | `GBP` | ✅ |
| 4 | Turn clock | `format.yaml` | `CLOCK` | ✅ |
| 5 | สูตรน้ำหนัก | `weights_for()` | `weightsFor()` | ✅ |
| 6 | สเกล counter/synergy | `_scale(-3,3)` | `scale()` | ✅ |
| 7 | role fit | `ROLE_FLOOR`/`LANE_OWN_SHARE` | เหมือนกัน | ✅ |
| 8 | composition | `composition.py` | `COMP_DIMS` | ✅ |
| 9 | **counter_score** | `MatchupStat.counter_score` | `cscore()` | ❌ **ไม่มีเทสต์** |
| 10 | **shrinkage k / prior** | `SHRINKAGE_K=30` | `D.shrinkage_k` (ส่งผ่าน data) | ⚠️ ส่งผ่านข้อมูล ไม่ใช่ hardcode — ปลอดภัยกว่า |
| 11 | **main lane / flex** | `lanes.main_lane()` | `mainLaneOf()` | ❌ **ไม่มีเทสต์** |
| 12 | **tempo → win condition** | ไม่มีใน Python | `winCondition()` เกณฑ์ ±0.12 | ❌ **มีแต่ใน JS เท่านั้น** |

**ข้อ 12 อันตรายที่สุด** — เกณฑ์ตัดสิน "คอมพ์สายต้นเกม/ท้ายเกม" มีอยู่เฉพาะใน
JavaScript ไม่มีใน Python เลย แปลว่า CLI กับเว็บให้ข้อสรุปคนละแบบ
และไม่มีอะไรคอยจับเพราะไม่มีของฝั่ง Python ให้เทียบ

---

## 10. Known Weaknesses

เรียงตามผลกระทบต่อคุณภาพคำแนะนำ

| # | จุดอ่อน | หลักฐาน | ผล |
|---|---|---|---|
| **W1** | **recommend ไม่รู้จัก composition** | `recommend.py` ไม่มี `import composition` | แนะนำ pick ที่ 3 ได้โดยไม่รู้ว่าทีมไม่มีแท็งก์ — ตอบ PRIMARY GOAL ข้อ 3, 4 ไม่ได้เลย |
| **W2** | **counter/synergy เป็นตัวเลขล้วน ไม่มีกลไก** | `counter_score` คืน float เดียว | ตอบ "pick นี้แก้ปัญหาอะไร" ไม่ได้ |
| **W3** | **flex ถูกลงโทษ ไม่ใช่ให้รางวัล** | `LANE_OWN_SHARE=0.5` ทำให้ตัว 50/50 ไม่ปิดเลนทั้งคู่ → `needed_lanes` เหลือเยอะ → `role_fit` ของตัวอื่นสูงขึ้น | ขัดกับหลักการที่ kit ยืนยัน (Flex Pick Strategy, FACT, HIGH) |
| **W4** | **ไม่มี lookahead** | ไม่มีโค้ด | ตอบ PRIMARY GOAL ข้อ 5, 6 ไม่ได้ |
| **W5** | **ไม่มี win condition** | ไม่มีแนวคิดนี้ในโค้ด (มีแต่ `winCondition()` ใน JS ที่ดูแค่ tempo) | ตอบข้อ 7, 8 ไม่ได้ |
| **W6** | **lane_matchups 680 คู่ถูกคำนวณแล้วไม่ถูกใช้** | `recommend.py` ใช้ `pooled.matchups` เท่านั้น | counter หยาบกว่าที่ควร |
| **W7** | **4 ช่อง utility กรอกแล้วไม่มีใครอ่าน** | `analyze()` ใช้ 8/12 ช่อง | poke/sustain/mobility/cc_soft เสียเปล่า |
| **W8** | **trait counter ออกแบบแล้วไม่ได้เขียน** | `strong_against_traits` ว่าง 119/119 ตัว, อ่าน 0 ที่ | ต้องรอข้อมูลแมตช์ถึงจะ counter ได้ ทั้งที่ออกแบบให้ไม่ต้องรอ |
| **W9** | **meta/winrate ไม่แยกแพตช์** | รวม 2025-08 ถึง 2026-09 | ตัวที่โดนนerfไปแล้วยังดูดีอยู่ |
| **W10** | **ไม่มี confidence ต่อคำแนะนำ** | `Suggestion.reliable` เป็น bool | ตอบข้อ 10 ได้หยาบมาก |
| **W11** | **macro 42 rule ไม่เชื่อมกับ recommend** | เชื่อมเฉพาะบนเว็บ (แสดง rule ของตัวที่ดราฟต์) ไม่มีใน engine | ตอบข้อ 8 ได้แค่บนหน้าเว็บ |
| **W12** | **weights ไม่เคย fit กับข้อมูล** | docstring ยอมรับเอง | น้ำหนักทั้งหมดเป็นการเดาที่มีเหตุผล แต่ยังเป็นการเดา |
| **W13** | **`expected_synergy()` มีอยู่แต่ไม่ถูกเรียก** | `stats.py:257` · `recommend.py` ใช้ `counter_score` ดิบแทน | synergy ยังปนเปื้อนด้วย "ทีมเก่งเล่นคู่นี้บ่อย" ทั้งที่มีเครื่องมือหักออกแล้ว |

---

## 11. Risks

| # | ความเสี่ยง | ระดับ | การป้องกันที่ต้องทำ |
|---|---|---|---|
| **K1** | **เอา score bonus จาก kit มาใช้ตรง ๆ** (+30%/-20%/+15%) | 🔴 สูง | ตัวเลขเหล่านี้ไม่ได้วัดจากแมตช์ ต้องเก็บเป็น config + fit กับ 861 เกมก่อน |
| **K2** | **นับ kit เป็นแหล่งอิสระ** | 🔴 สูง | ต้นทางเป็นคลิปชุดเดียวกับ `knowledge/raw/` — ถ้านับซ้ำจะดู "ยืนยันสองแหล่ง" ทั้งที่เป็นแหล่งเดียว |
| **K3** | **ปน INFERENCE เป็น FACT** | 🔴 สูง | kit แยก label ไว้แล้ว ต้องขนมาทั้ง label ห้ามทิ้ง |
| **K4** | **เพิ่ม factor แล้วคำแนะนำเปลี่ยนโดยไม่มีใครรู้** | 🟡 กลาง | ต้องมี benchmark ก่อน/หลัง (ดู §14) และ factor ใหม่ต้องเริ่มที่น้ำหนัก 0 แล้วค่อยเปิด |
| **K5** | **Python/JS เพี้ยนกันเพิ่มขึ้น** | 🟡 กลาง | ทุก factor ใหม่ต้องมีเทสต์ parity ก่อนขึ้นเว็บ |
| **K6** | **13 ตัวใน kit มี bias** | 🟡 กลาง | kit ครอบคลุมแค่ 13/119 ตัว และเป็นตัวที่คลิปพูดถึง ไม่ใช่ตัวที่สำคัญที่สุดตามข้อมูล (เช่น Chaugnar presence แค่ 4.1%) |
| **K7** | **โครงสร้าง rule ใหญ่ขึ้นจนเทสต์ตามไม่ทัน** | 🟡 กลาง | ทุก rule ใหม่ต้องมีเทสต์ที่อ้าง rule_id ตรง ๆ |
| **K8** | **แตะ `_max_lane_matching` แล้วพัง** | 🟢 ต่ำ-สูงผลกระทบ | Kuhn algorithm มีเทสต์คุมอยู่ 1 ตัว ควรเพิ่มก่อนแตะ |

---

## 12. Quick Wins

ทำได้เร็ว ความเสี่ยงต่ำ ผลชัด

| # | งาน | แรง | ผล |
|---|---|---|---|
| **Q1** | นำเข้า Mina, Chaugnar, Violet จาก `knowledge/hero.md` | 2 ชม. | +2.6% ครอบคลุม · **และเป็น 3 ตัวแรกที่จะมี `filled_kind` ที่อ้าง source คลิปได้** |
| **Q2** | **ตรวจ 10 ตัวที่ทั้ง kit และเรามี แล้วอัปเกรด provenance** | 3 ชม. | 10 ตัวจาก assistant → source-backed · ครอบคลุม ~47% ของ pick+ban |
| **Q3** | เติม `strong_against_traits`/`weak_against_traits` จาก kit tag system | 2 ชม. | ปลดล็อก trait counter ที่ออกแบบไว้ใน docs/06 §3.4 |
| **Q4** | เพิ่มมิติ `flex_value` จาก `lane_usage` ที่มีอยู่แล้ว | 2 ชม. | แก้ W3 — เลิกลงโทษ flex |
| **Q5** | เพิ่มมิติ poke/sustain/mobility/burst จาก utility ที่กรอกแล้ว | 3 ชม. | แก้ W7 — ใช้ข้อมูลที่มีให้ครบ |
| **Q6** | เพิ่มเทสต์ parity ให้ `cscore` และ `mainLaneOf` | 1 ชม. | ปิดช่องว่าง §9 ข้อ 9, 11 |
| **Q7** | ย้าย `winCondition()` จาก JS มา Python + เทสต์ parity | 2 ชม. | ปิดช่องว่าง §9 ข้อ 12 ที่อันตรายที่สุด |
| **Q8** | ให้ `_synergy_with()` เรียก `expected_synergy()` แทนค่าดิบ | 1 ชม. | แก้ W13 — หัก "ทีมเก่งเล่นคู่นี้บ่อย" ออกจาก synergy · **ต้องมี benchmark ก่อน เพราะเปลี่ยนอันดับแน่** |

รวม Q1–Q8 ≈ **2 วัน** ไม่แตะ architecture เลย
(Q8 เป็นข้อเดียวที่เปลี่ยนพฤติกรรม จึงต้องรอ PHASE I ตามกฎข้อ 4 ที่ห้ามเปลี่ยน weight เงียบ ๆ)

---

## 13. Medium Changes

| # | งาน | แรง | ต้องมีก่อน |
|---|---|---|---|
| **M1** | `CounterKnowledge` — โมเดล counter เชิงกลไกจาก kit (5 direct + 3 role + 2 comp + 4 problem) | 3 วัน | Q3 |
| **M2** | `SynergyKnowledge` — 8 pair + 5 role + 7 tag พร้อม `condition`/`expected_result`/`weakness` | 3 วัน | Q1, Q2 |
| **M3** | `composition.analyze()` เพิ่ม 6 มิติที่ขาด + `CompositionProfile` ที่ macro เรียกใช้ได้ | 3 วัน | Q5 |
| **M4** | `recommend()` รับ `composition_fit` เป็น factor ที่ 5 (เริ่มที่น้ำหนัก 0) | 2 วัน | M3 |
| **M5** | `Suggestion` เพิ่ม `confidence` / `sources` / `fills_gaps` / `creates_gaps` ตาม docs/06 §7 | 2 วัน | M3, M4 |
| **M6** | ใช้ `lane_matchups` ใน counter เมื่อรู้เลนของทั้งสองฝั่ง | 2 วัน | — |
| **M7** | แยก meta/winrate ตามช่วงเวลา (ใช้ `filter_since` ที่มีอยู่) | 1 วัน | — |
| **M8** | Benchmark harness บน 861 เกม (ดู §14) | 3 วัน | — |

---

## 14. Large Changes

| # | งาน | แรง | หมายเหตุ |
|---|---|---|---|
| **L1** | **Lookahead / Response Simulation** — deterministic 1-ply ก่อน | 1-2 สัปดาห์ | ต้องมี M1, M2, M5 ก่อน · เริ่มจาก 1 ply เท่านั้น |
| **L2** | **Explanation Engine** — ประกอบเหตุผลจาก factor + rule + source | 1 สัปดาห์ | ต้องมี M5 · นี่คือสิ่งที่ทำให้ตอบ PRIMARY GOAL ครบ 10 ข้อ |
| **L3** | **Win Condition Engine** — จำแนกคอมพ์เป็น 4 แบบตาม kit แล้วผูกกับ macro | 1 สัปดาห์ | ต้องมี M3 |
| **L4** | **fit `weights_for()` ด้วย logistic regression** บน holdout | 1 สัปดาห์ | ต้องมี M8 · ต้องแยก train/eval เข้มงวด |
| **L5** | ย้ายมิติ composition ทั้งหมดไป spec ที่ export เป็น JSON ให้ JS อ่าน แทนการเขียนซ้ำ | 1 สัปดาห์ | ปิดปัญหา duplication ที่ต้นเหตุ |

---

## 15. Intelligence Scorecard

ให้คะแนนตามความสามารถในการตอบ 10 คำถามใน PRIMARY GOAL

| # | คำถาม | คะแนน | เหตุผล |
|---|---|---|---|
| 1 | Pick นี้ดีเพราะอะไร | **6/10** | บอกได้ว่า factor ไหนสูง + n เท่าไร แต่ไม่บอกกลไก |
| 2 | Pick นี้แก้ปัญหาอะไร | **1/10** | ไม่มีแนวคิด "ปัญหา" ในระบบเลย |
| 3 | ทำให้ composition ดีขึ้นด้านไหน | **0/10** | recommend ไม่รู้จัก composition |
| 4 | สร้าง weakness ใหม่อะไร | **0/10** | ไม่มี `creates_gaps` |
| 5 | ศัตรูน่าจะตอบอย่างไร | **0/10** | ไม่มี lookahead |
| 6 | ถ้าศัตรูตอบแบบนั้น เรามี response ไหม | **0/10** | เช่นเดียวกัน |
| 7 | Final composition มี win condition แบบใด | **2/10** | มีแต่ใน JS จาก tempo อย่างเดียว |
| 8 | ต้องใช้ macro แบบใด | **3/10** | มี 42 rule แสดงบนเว็บ แต่ไม่ผูกกับ composition |
| 9 | หลักฐานจาก data/knowledge อะไร | **7/10** | แข็งที่สุด — มี n, มี source, มี filled_kind · ขาด label FACT/INFERENCE |
| 10 | ความมั่นใจระดับไหน | **3/10** | มีแค่ `reliable` bool |
| | **รวม** | **22/100** | |

**อ่านคะแนนนี้อย่างไร:** 22/100 ไม่ได้แปลว่าระบบแย่ —
ระบบทำสิ่งที่ตัวเองอ้างว่าทำได้ดีมาก (คำแนะนำจากสถิติที่ซื่อสัตย์)
แต่ PRIMARY GOAL ตั้งเป้าไว้สูงกว่านั้นมาก คือ "ระบบช่วยตัดสินใจเชิงบริบท"
คะแนนนี้วัดระยะห่างจากเป้าใหม่ ไม่ได้วัดคุณภาพของสิ่งที่มีอยู่

---

## 16. 5 จุดอ่อนที่ใหญ่ที่สุด

1. **`recommend.py` กับ `composition.py` ไม่คุยกันเลย** (W1)
   เป็นสองระบบที่อยู่ในโฟลเดอร์เดียวกันแต่ไม่เคยเรียกหากัน
   นี่คือสาเหตุเดียวที่ทำให้คำถามข้อ 3 และ 4 ได้ 0 คะแนน

2. **counter/synergy ไม่มีกลไก มีแต่ตัวเลข** (W2)
   ตอบ "ใช่" ได้ แต่ตอบ "ทำไม" ไม่ได้ · kit มีคำตอบอยู่แล้ว

3. **ไม่มี lookahead** (W4)
   คำถามข้อ 5 และ 6 เป็นหัวใจของการดราฟต์ระดับสูง และตอนนี้ได้ 0

4. **flex ถูกลงโทษแทนที่จะได้รางวัล** (W3)
   ขัดกับหลักการที่ทั้ง kit และเมตาจริงยืนยัน และข้อมูลที่ต้องใช้มีอยู่แล้วครบ

5. **มีของที่สร้างแล้วไม่ได้ใช้อยู่ 3 ก้อน** (W6, W7, W8)
   `lane_matchups` 680 คู่ · 4 ช่อง utility · `strong/weak_against_traits` 119 ตัว
   — ของพวกนี้ต้นทุนการเปิดใช้ต่ำมากเทียบกับผลที่ได้

---

## 17. ลำดับที่แนะนำ

ตาม PHASE A–J ที่กำหนดมา แต่ปรับให้เริ่มจากของที่มีอยู่แล้ว

```
PHASE A  ✅ audit  (เอกสารนี้ + 18 + 19 + 20)
PHASE B  Q1, Q2, Q3       เติมข้อมูล + ยกระดับ provenance จาก kit
PHASE C  Q4, Q5, M3       composition intelligence
PHASE D  M4, M5           context-aware recommendation
PHASE E  M1, M2, M6       counter + synergy เชิงกลไก
PHASE F  L1               lookahead 1 ply
PHASE G  L3               macro linkage ผ่าน win condition
PHASE H  L2               explanation engine
PHASE I  M8, L4           benchmark + fit weights
PHASE J  L5 + web         UI integration
```

**เกณฑ์ผ่านของแต่ละ PHASE:** เทสต์เดิมทั้งหมดยังผ่าน + เทสต์ใหม่ของ PHASE นั้นผ่าน
+ benchmark ไม่ถอยหลัง (หลัง PHASE I เป็นต้นไป)

---

## 18. สิ่งที่ยังไม่แน่ใจ — รายงานแทนการเดา

ตาม IMPORTANT ENGINEERING RULE ข้อ 14

1. **ลำดับสลับ ban/pick ภายในเฟส** — kit ยืนยันโครงสร้าง 3+2 แต่ไม่ได้บอกลำดับสลับ
   ยังต้องดูคลิปแข่ง
2. **เวลาต่อตา** — ยังไม่มีหลักฐานจากที่ไหนเลย
3. **น้ำหนักที่ควรใช้กับ factor ใหม่** — ยังไม่มีวิธีตัดสินจนกว่าจะมี benchmark
   จึงเสนอให้ factor ใหม่ทุกตัว**เริ่มที่น้ำหนัก 0** แล้วเปิดทีละตัวพร้อมวัดผล
4. **Chaugnar** — kit ให้ความสำคัญสูงมาก (cleanse counter) แต่ข้อมูลเรามี presence แค่ 4.1%
   ยังไม่รู้ว่าเป็นเพราะเมตาไทย/ไต้หวันต่างจากที่คลิปพูดถึง หรือเพราะคลิปเก่ากว่าข้อมูล
   **ห้ามตัดสินแทน** ต้องแสดงทั้งสองด้าน
5. ~~**`expected_synergy()`** — ยังไม่ได้ยืนยันว่ามีอยู่จริง~~
   **ตรวจแล้ว: มีอยู่จริงที่ `stats.py:257`** และคำนวณถูกหลัก (รวม odds ไม่ใช่คูณ
   win rate ตรง ๆ เพราะทุกเกมมีผู้ชนะเสมอ) docstring ยอมรับเองว่ายังไม่หัก
   ความแข็งของทีมออก **แต่ `recommend.py` ไม่เคยเรียกมันเลย** —
   ใช้ `counter_score` ดิบแทน จึงต้องเพิ่มเป็นจุดอ่อน **W13** และเป็นของที่
   "สร้างแล้วไม่ได้ใช้" ก้อนที่ 4 ต่อจาก W6/W7/W8 · แก้ได้ใน Q-level (~1 ชม.)
