# 06 — Draft Intelligence Engine

Draft Engine **ไม่พึ่งพา vision pipeline เลย** จึงพัฒนาขนานกันได้ตั้งแต่วันแรก
นี่คือข้อได้เปรียบสำคัญ: ระหว่างที่งาน CV ยังไม่ให้ผล Draft v1 ส่งมอบคุณค่าได้แล้ว

---

## 1. สองรุ่นที่ต้องแยกให้ชัด (G7)

| | Draft v1 · Attribute-based | Draft v2 · Empirical |
|---|---|---|
| ต้องมีข้อมูล | hero attribute ที่คนกรอก | 200+ แมตช์ต่อ patch |
| ตอบคำถามได้ | ทีมขาด role อะไร · damage เอียงไปทางเดียวไหม · มี engage/peel พอไหม · power curve เป็นอย่างไร | ฮีโร่ A ชนะฮีโร่ B จริงไหม · draft นี้มีโอกาสชนะเท่าไร |
| ความน่าเชื่อถือ | ขึ้นกับคุณภาพการกรอก attribute | ขึ้นกับ sample size |
| เริ่มได้เมื่อ | ทันที | **หลัง importer ดึงข้อมูลเสร็จ ไม่ต้องรอ vision** |

**อัปเดตสำคัญ:** เดิมเขียนว่า Draft v2 ต้องรอ Milestone 5 เพราะต้องรอ vision
ผลิตข้อมูลแมตช์ **ไม่จริง** Liquipedia API ให้ draft order (pick และ ban)
ของ RoV Pro League ย้อนหลังถึงปี 2021 จึงดึงมาใช้ได้เลย
ดู [08-game-reference.md](08-game-reference.md) §8 และข้อ 4.0 ด้านล่าง

สิ่งที่ยังต้องรอ vision จริง ๆ คือ **matchup แบบแยกเลน** (`context: LANE`)
เพราะต้องรู้ว่าใครยืนเลนไหน ส่วน `context: TEAM` ทำได้ทันที

ทำ v1 ให้ครบและดีก่อน อย่ารอข้อมูล
เมื่อมี v2 แล้วให้ **แสดงคะแนนทั้งสองแยกกัน** ไม่ใช่หลอมรวมเป็นเลขเดียว
ผู้ใช้ต้องรู้ว่าคำแนะนำมาจากตรรกะหรือจากสถิติ

---

## 2. Hero Attribute Schema

หัวใจของ v1 อยู่ที่ตารางนี้ ต้องกรอกด้วยมือให้ครบทุกฮีโร่
ประมาณ 15–20 นาทีต่อ 10 ฮีโร่ ถ้ามีคนที่เข้าใจเกม

`configs/draft/heroes.yaml`

```yaml
- id: nakroth
  name_en: Nakroth
  name_th: นาครอธ

  # แยกสองแนวคิดนี้ให้ชัด อย่าปนกัน
  hero_class: [assassin, warrior]  # class ตามเกม ตัวแรกคือหลัก
                                   # marksman|mage|assassin|tank|warrior|support
  lane_roles: [jungle, ds]         # เลนที่เล่นได้จริงในระดับ pro
                                   # ds|jungle|mid|dragon|support

  damage:
    type: physical                # physical | magical | true | hybrid
    profile: burst                # burst | sustained | poke
    target: single                # single | aoe

  range: melee                    # melee | short | long

  scaling:                        # ความแข็งแกร่งสัมพัทธ์ 0-100 ตามช่วงเกม
    early: 78
    mid:   85
    late:  62

  utility:
    engage:      80               # ความสามารถเปิดฟight
    disengage:   35
    peel:        20               # ปกป้องเพื่อน
    cc_hard:     40               # stun/knockup/suppress
    cc_soft:     30               # slow/silence
    mobility:    90
    poke:        20
    sustain:     25
    frontline:   30               # รับดาเมจแทนทีมได้แค่ไหน
    objective:   85               # ความสามารถตี objective เดี่ยว
    waveclear:   60
    splitpush:   75

  # ความสัมพันธ์เชิงคุณภาพที่คนกรอกได้โดยไม่ต้องมีสถิติ
  strong_against_traits: [squishy_backline, immobile]
  weak_against_traits:   [hard_cc, frontline_tank]

  notes: "ต้องการ setup จาก cc เพื่อเข้าถึง carry ได้แน่นอน"
```

### กฎการกรอก

1. **ค่าเป็นเชิงสัมพัทธ์ ไม่ใช่ค่าสัมบูรณ์** — 80 แปลว่า "อยู่ในกลุ่มสูงเมื่อเทียบกับฮีโร่ทั้งหมด"
2. **กรอกทีละมิติทั่วทุกฮีโร่** ไม่ใช่กรอกทีละฮีโร่ครบทุกมิติ
   เพราะการเปรียบเทียบข้ามฮีโร่ในมิติเดียวกันแม่นกว่ามาก
3. **ให้สองคนกรอกอิสระแล้วเทียบกัน** ค่าที่ต่างกันเกิน 20 ให้คุยกัน
   บันทึกความไม่เห็นตรงกันไว้ มันบอกว่ามิติไหนคลุมเครือ
4. **ผูกกับ patch** เก็บ attribute แยกต่อ patch major ถ้ามีการปรับสมดุลใหญ่
   แพตช์ปัจจุบันคือ **1.63**

### ⚠️ ขอบเขตการกรอก — แก้จากข้อมูลที่ตรวจสอบแล้ว

AoV มีฮีโร่ **126 ตัว** (ล่าสุดคือ Dyadia) แต่มีเพียง **98 ตัว** ที่มีข้อมูลระดับ pro
การกรอกทุกตัวก่อนเริ่มใช้งานจึงช้าเกินไป กรอกตามลำดับความสำคัญแทน

| รอบ | ขอบเขต | จำนวน | เวลา |
|-----|--------|-------|------|
| 1 | ฮีโร่ที่มี pick + ban rate สูงสุดใน patch 1.63 | ~30 | 1 วัน |
| 2 | ฮีโร่ที่มีข้อมูล pro league | ~98 | 2–3 วัน |
| 3 | ที่เหลือ | 126 | ตามสะดวก |

ใช้ pick และ ban rate จาก importer เป็นตัวจัดลำดับ
ฮีโร่ที่ไม่เคยถูก pick หรือ ban ในระดับ pro แทบไม่มีผลต่อ draft engine
รอบที่ 1 ครอบคลุมกรณีใช้งานจริงส่วนใหญ่แล้ว

---

## 3. Draft v1 · Composition Analysis

### 3.1 มิติที่ประเมิน

```
1. Role Balance          ทีมมีตำแหน่งครบไหม
2. Damage Mix            physical/magical สมดุลไหม
3. Frontline             มีคนรับดาเมจไหม
4. Engage / Disengage    เปิดฟightได้ไหม ถอยได้ไหม
5. Crowd Control         มี hard CC พอไหม
6. Peel                  ป้องกัน carry ได้ไหม
7. Power Curve           แข็งช่วงไหน และตรงกับแผนไหม
8. Objective Power       ตี dragon/slayer ได้เร็วไหม
9. Waveclear             ตั้งรับได้ไหม
10. Split Potential      แยกกดดันได้ไหม
```

### 3.2 สูตร

แต่ละมิติคำนวณจาก attribute ของ 5 ตัวในทีม แล้ว map เป็น 0–100

```python
# ตัวอย่าง: Damage Mix — ลงโทษทีมที่ดาเมจเอียงไปทางเดียว
phys = sum(h.damage.type == 'physical' for h in team)
mag  = sum(h.damage.type == 'magical'  for h in team)
ratio = min(phys, mag) / max(phys, mag, 1)
damage_mix = 100 * ratio ** 0.6        # 3:2 ได้ ~79, 5:0 ได้ 0

# ตัวอย่าง: Frontline — ใช้ค่าสูงสุดสองอันดับแรก ไม่ใช่ค่าเฉลี่ย
# เพราะมี tank ดีหนึ่งตัวมีค่ากว่ามีคนกลาง ๆ ห้าตัว
front = sorted([h.utility.frontline for h in team], reverse=True)
frontline = min(100, front[0] * 0.7 + front[1] * 0.3)

# ตัวอย่าง: Hard CC — นับแบบอิ่มตัว (diminishing returns)
cc_total = sum(h.utility.cc_hard for h in team)
cc = 100 * (1 - exp(-cc_total / 180))
```

**หลักสำคัญ:** อย่าใช้ค่าเฉลี่ยธรรมดาสำหรับทุกมิติ
บางมิติเป็นแบบ "มีหนึ่งคนก็พอ" (engage, frontline) → ใช้ max หรือ top-2
บางมิติเป็นแบบ "สะสม" (CC, damage) → ใช้ผลรวมที่อิ่มตัว
บางมิติเป็นแบบ "จุดอ่อนที่สุดเป็นตัวกำหนด" (waveclear ในการตั้งรับ) → ใช้ min

การเลือกฟังก์ชันรวมผิดคือสาเหตุหลักที่ระบบให้คะแนน draft ผิด

### 3.3 Power Curve

```python
curve = {
  'early': weighted_mean([h.scaling.early for h in team]),
  'mid':   weighted_mean([h.scaling.mid   for h in team]),
  'late':  weighted_mean([h.scaling.late  for h in team]),
}
```

แสดงเป็นกราฟเทียบกับทีมตรงข้าม นี่คือ output ที่มีประโยชน์ที่สุดของ v1
เพราะมันบอกทันทีว่า "ต้องจบเกมก่อนนาที 15" หรือ "ต้องยื้อไปให้ถึง late"

### 3.4 Trait-based Counter (ไม่ต้องมีข้อมูล)

จาก `strong_against_traits` / `weak_against_traits` คำนวณ counter เชิงคุณภาพได้

```python
def trait_counter(hero, enemy_team):
    score = 0
    for enemy in enemy_team:
        traits = derive_traits(enemy)     # เช่น squishy_backline, immobile, hard_cc
        score += len(set(hero.strong_against_traits) & traits)
        score -= len(set(hero.weak_against_traits)  & traits)
    return normalize(score)
```

`derive_traits` คำนวณจาก attribute เชิงตัวเลข เช่น
`mobility < 40 → immobile`, `frontline < 30 and range == long → squishy_backline`

วิธีนี้ให้ counter ที่อธิบายได้ตั้งแต่วันแรกโดยไม่ต้องมีแมตช์แม้แต่แมตช์เดียว

---

## 4. Draft v2 · Empirical

### 4.0 แหล่งข้อมูล — Liquipedia Importer 🟢

Liquipedia API ให้ draft order (pick และ ban) ต่อแมตช์ พร้อมผลแพ้ชนะ ทีม และผู้เล่น
ครอบคลุม RoV Pro League ย้อนหลังถึงปี 2021

**ข้อจำกัดที่ต้องเคารพอย่างเคร่งครัด**

| ข้อจำกัด | ค่า |
|----------|-----|
| Request ต่อชั่วโมง | 60 |
| Request ทั่วไป | ไม่เกิน 1 ครั้ง / 2 วินาที |
| `action=parse` | ไม่เกิน 1 ครั้ง / 30 วินาที |
| บทลงโทษ | แบน IP ชั่วคราว · ทำซ้ำอาจถาวร |

**ข้อกำหนดในการเขียน importer**

```
1. cache ทุก response ลงดิสก์ก่อนแปลงข้อมูล  ← สำคัญที่สุด
2. resume ได้ เก็บ cursor ว่าดึงถึงไหนแล้ว
3. rate limiter ที่บังคับหน่วงจริง ไม่ใช่แค่ sleep แบบหวังผล
4. ห้ามยิงซ้ำสิ่งที่ cache ไว้แล้ว แม้ในการทดสอบ
5. ระบุ User-Agent ที่บอกได้ว่าเป็นใคร ตามที่ Terms of Use กำหนด
```

ที่ 60 requests/ชั่วโมง การดึงหลายร้อยแมตช์ใช้เวลาเป็นวัน
ให้รันเป็น background job ข้ามคืน ไม่ใช่รันสด

ใช้ `liquipediapy` จาก PyPI เป็นจุดเริ่ม แต่ต้องตรวจว่ามัน rate limit ให้จริงหรือไม่
ถ้าไม่ ให้ห่อด้วย limiter ของเราเอง

**การตรวจสอบความถูกต้อง:** เทียบ pick/ban/win rate ที่คำนวณได้
กับตัวเลขบน rovmeta.com ซึ่งดึงจาก Liquipedia เหมือนกัน
ถ้าต่างกันมาก แปลว่า importer แปลงข้อมูลผิด

---

### 4.1 Matchup พร้อม Shrinkage (G8)

```python
def matchup_rate(hero, enemy, patch, context, k=30):
    row = db.matchup(hero, enemy, patch, context)
    prior = hero_winrate(hero, patch)      # prior คือ win rate ของฮีโร่นั้นเอง
    if row.games == 0:
        return prior, 0.0                  # ไม่มีข้อมูล → คืน prior + confidence 0
    adj = (row.wins + k * prior) / (row.games + k)
    conf = row.games / (row.games + k)     # 0..1
    return adj, conf
```

`counter_score` ที่แสดงบน UI คือ `(adj - prior) * 100 * conf`
คือ "ดีกว่าปกติแค่ไหน ถ่วงด้วยความมั่นใจ"
วิธีนี้ทำให้คู่ที่ไม่มีข้อมูลได้ 0 โดยอัตโนมัติ แทนที่จะได้ค่าสุดโต่ง

### 4.2 แยก context ของ Counter

แผนเดิม §36 ระบุไว้ถูกแล้วว่าต้องแยก ทำเป็นสองระดับก็พอในทางปฏิบัติ

| context | นิยาม | ที่มาของข้อมูล |
|---------|-------|----------------|
| `LANE` | สองฮีโร่อยู่เลนเดียวกัน | ต้องรู้ role assignment จาก match_players |
| `TEAM` | สองฮีโร่อยู่คนละทีม ไม่ว่าเลนไหน | ได้จาก draft ล้วน |

`TEAM` เก็บได้ทันทีจาก draft data `LANE` ต้องรอ role assignment
ซึ่ง vision pipeline จะให้มา (ผ่าน LANE_SWAP detector ใน 05)

### 4.3 Synergy

เก็บแบบเดียวกับ matchup แต่เป็นคู่ในทีมเดียวกัน และบังคับ `hero_a < hero_b`
เพื่อไม่ให้เก็บซ้ำสองทิศทาง

ปัญหาที่ต้องระวัง: synergy ที่วัดได้จะปนเปื้อนด้วย "ทีมเก่งเล่นคู่นี้บ่อย"
ทางแก้เบื้องต้นคือคำนวณ synergy แบบเทียบกับที่คาดหวัง

```
expected = wr(a) * wr(b) / baseline
synergy  = observed_wr(a,b) - expected
```

ยังไม่สมบูรณ์ แต่ดีกว่าใช้ win rate ดิบมาก
วิธีที่ถูกต้องจริงคือ logistic regression ที่มี team strength เป็น covariate
เก็บไว้ทำตอน Phase 9

---

## 5. Draft State Machine

`configs/draft/format.yaml` — ลำดับ ban/pick ต้องตั้งค่าได้
เพราะแต่ละรายการแข่งใช้ format ต่างกัน และ format เปลี่ยนตามฤดูกาล

```yaml
id: pro_standard
sequence:
  - { phase: 1, order: 1,  team: blue, action: BAN }
  - { phase: 1, order: 2,  team: red,  action: BAN }
  # ... ตามรูปแบบจริงของรายการ
  - { phase: 1, order: 5,  team: blue, action: PICK }
  - { phase: 1, order: 6,  team: red,  action: PICK }
  # ...
```

**ต้องยืนยันลำดับจริงกับกติกาของรายการที่จะวิเคราะห์**
อย่า hardcode ลำดับใดลงในโค้ด เพราะจะผิดเมื่อเปลี่ยนรายการ

### Global Ban-Pick — กติกาจริงของ RPL 2026

ค้นแล้วได้กติกาที่แน่นอน (ที่มา: Liquipedia RoV Pro League 2026 Summer)

```
Bo3 / Bo5
  แต่ละทีมห้ามเลือกฮีโร่ที่ "ตัวเอง" ใช้ไปแล้วในเกมก่อนหน้า
  การเลือกฮีโร่ที่ "ฝ่ายตรงข้าม" เคยใช้ ไม่ถูกจำกัด

Bo7
  ใช้กับเกมที่ 1-6 · เกมที่ 7 กลับเป็น Normal Ban-Pick ฮีโร่กลับมาครบ

เลือกฝั่ง
  ทีมฝั่งซ้ายของตารางแข่ง (ทีม "เหย้า") เลือกฝั่งในเกมแรก
```

นี่คือ **soft fearless** ไม่ใช่ full fearless เอกสารรุ่นแรกเขียนกว้างเกินไป

```yaml
# configs/draft/format.yaml
id: rpl_2026
global_ban_pick:
  enabled: true
  scope: own_team_only        # own_team_only | both_teams
  reset_on_final_game: true   # Bo7 เกมที่ 7 รีเซ็ต
  applies_to_bans: false      # จำกัดเฉพาะ pick ไม่รวม ban
```

### กติกาที่ engine ต้องบังคับ

```
1. ฮีโร่ที่ถูก ban ในเกมนี้ pick ไม่ได้
2. ฮีโร่ที่ถูก pick ในเกมนี้แล้ว อีกฝ่าย pick ไม่ได้
3. หนึ่งทีม pick ได้ 5 ตัว
4. Global Ban-Pick: ตัดฮีโร่ที่ "ทีมตัวเอง" ใช้ไปแล้วในเกมก่อนหน้าของซีรีส์
   (ไม่ตัดของฝ่ายตรงข้าม)
5. ถ้าเป็นเกมสุดท้ายของ Bo7 ข้ามข้อ 4
```

⚠️ **ยังหาไม่พบ:** ลำดับ ban/pick ที่แน่นอน (ban กี่ตัวต่อเฟส เรียงอย่างไร)
ไม่มีในแหล่งสาธารณะ ต้องดูจากคลิปแข่งจริงหรือ rulebook ทางการ
การออกแบบให้ลำดับอยู่ใน config จึงเป็นการตัดสินใจที่ถูกต้อง

### Series Value — มิติใหม่ที่ Global Ban-Pick สร้างขึ้น

`scope: own_team_only` เปลี่ยนโจทย์ของ draft engine อย่างมีนัยสำคัญ
การ pick ฮีโร่แข็งในเกมแรกมี **ต้นทุน** เพราะเกมต่อไปจะไม่มีตัวนั้นให้ใช้อีก

แผนเดิมและเอกสารรุ่นแรกไม่ได้คิดถึงมิตินี้เลย แต่เป็นสิ่งที่โค้ชคิดจริง

```python
def series_adjusted_score(hero, game_idx, series_len, base_score):
    games_left = series_len - game_idx
    # ยิ่งเหลือหลายเกม การเผาฮีโร่แข็งยิ่งมีต้นทุนสูง
    scarcity = hero_strength_percentile(hero) * games_left / series_len
    return base_score - w_series * scarcity
```

แสดงแยกบน UI เป็นสองคะแนน

```
Game Score    92.1   ดีที่สุดสำหรับเกมนี้
Series Score  84.7   หลังหักต้นทุนของการเสียตัวนี้ไปทั้งซีรีส์
```

ฟีเจอร์นี้ไม่มีในเครื่องมือ draft ทั่วไป และเป็นจุดต่างที่ชัดเจนของระบบ

---

## 6. Draft Score

แผนเดิม §37 เสนอน้ำหนักไว้แล้ว เก็บใน `configs/draft/weights.yaml`

```yaml
version: 1
weights:
  counter:      0.30
  synergy:      0.25
  role_balance: 0.15
  early_game:   0.10
  late_game:    0.10
  objective:    0.10

# แต่ละองค์ประกอบมาจากไหน
sources:
  counter:      { v1: trait_counter, v2: empirical_matchup, blend: separate }
  synergy:      { v1: trait_synergy, v2: empirical_synergy, blend: separate }
```

`blend: separate` หมายถึงแสดงแยก ไม่หลอมรวม ตามที่กล่าวในข้อ 1

### ข้อควรระวังเรื่องน้ำหนัก

น้ำหนักชุดนี้เป็นการเดาที่สมเหตุสมผล แต่ยังเป็นการเดาอยู่ดี
เมื่อมีข้อมูลผลแพ้ชนะ 200+ แมตช์แล้ว ให้ fit น้ำหนักด้วย logistic regression
โดยใช้องค์ประกอบทั้ง 6 เป็น feature และผลแพ้ชนะเป็น target
แล้วเทียบว่าน้ำหนักที่ fit ได้ต่างจากที่เดาไว้แค่ไหน

จนกว่าจะถึงตอนนั้น ให้ระบุบน UI ว่าน้ำหนักยังไม่ผ่านการ validate

---

## 7. Recommendation Output

ต้องตอบโจทย์ §41 ที่ว่า "แสดงเหตุผลในรูปของ Metrics ไม่ใช่เพียงข้อความ"

```json
{
  "recommendations": [
    {
      "hero_id": "aya",
      "rank": 1,
      "total": 87.5,
      "components": {
        "counter":      { "value": 86, "source": "v1_trait", "confidence": "MED" },
        "synergy":      { "value": 91, "source": "v1_trait", "confidence": "MED" },
        "role_balance": { "value": 90, "source": "rule",     "confidence": "HIGH" },
        "early_game":   { "value": 78, "source": "attribute","confidence": "HIGH" },
        "late_game":    { "value": 88, "source": "attribute","confidence": "HIGH" },
        "objective":    { "value": 92, "source": "attribute","confidence": "HIGH" }
      },
      "fills_gaps":  ["peel", "magical_damage"],
      "creates_gaps": [],
      "reasons": [
        { "type": "role_gap",   "detail": "ทีมยังขาด support ที่มี peel" },
        { "type": "damage_mix", "detail": "ทีมมี physical 3 ตัว การเพิ่ม magical ทำให้ 3:2" },
        { "type": "trait_counter", "detail": "hard CC ตอบโต้ Nakroth ฝั่งตรงข้ามที่ mobility สูง" }
      ],
      "data_basis": { "matches_used": 0, "note": "คำแนะนำจาก attribute ล้วน ยังไม่มีข้อมูลสถิติ" }
    }
  ]
}
```

ฟิลด์ `data_basis` บังคับให้ระบบซื่อสัตย์เรื่องที่มาของคำแนะนำเสมอ
และฟิลด์ `creates_gaps` สำคัญพอกับ `fills_gaps` เพราะการ pick ที่ดีในมิติหนึ่ง
มักสร้างจุดอ่อนในอีกมิติ ระบบต้องบอกทั้งสองด้าน

---

## 8. Player-Specific Draft (Phase 8)

ตาม §42 ของแผนเดิม ต้องรอให้มี player profile จาก vision ก่อน

```sql
CREATE TABLE player_hero_stats (
  player_id TEXT REFERENCES players(id),
  hero_id   TEXT REFERENCES heroes(id),
  patch_id  INT  REFERENCES patches(id),
  games     INT NOT NULL DEFAULT 0,
  wins      INT NOT NULL DEFAULT 0,
  PRIMARY KEY (player_id, hero_id, patch_id)
);
```

การแนะนำ ban เฉพาะตัวผู้เล่น ต้องแยกให้ชัดจาก meta ban

```
Meta Ban        : ฮีโร่แข็งใน patch นี้โดยทั่วไป
Player Ban      : ฮีโร่ที่ผู้เล่นคนนี้เล่นได้ดีกว่าค่าเฉลี่ยอย่างมีนัยสำคัญ
Matchup Ban     : ฮีโร่ที่ counter draft ที่เรากำลังจะทำ
```

สำหรับ Player Ban ต้องใช้ shrinkage เช่นกัน และต้องมี `games ≥ 8`
จึงจะแสดง มิฉะนั้นจะแนะนำให้ ban ฮีโร่ที่ผู้เล่นบังเอิญเล่นชนะ 2 จาก 2

---

## 9. ลำดับการพัฒนา Draft Engine

แก้ลำดับใหม่หลังพบว่า Liquipedia API ใช้ได้ **เริ่มจาก importer ก่อน**

```
D0. Liquipedia importer + rate limiter + cache             2 วัน
D0b. map ชื่อฮีโร่ Liquipedia → hero_id ของเรา              0.5 วัน
D0c. รันดึง RPL 2024-2026 ข้ามคืน                          รันเบื้องหลัง
──────────────────────────────────────────────────────────
D1. hero attribute schema                                  0.5 วัน
D2. กรอก 30 ฮีโร่ที่ pick/ban สูงสุด (จัดลำดับจาก D0c)      1 วัน
D3. draft state machine + Global Ban-Pick                  1.5 วัน
D4. composition analysis 10 มิติ                            2-3 วัน
D5. trait-based counter/synergy                            1-2 วัน
D6. recommendation + reasons + series value                 2.5 วัน
D7. CLI: rov draft simulate/recommend/import                1 วัน
──────────────────────────────────────────────────────────
    Draft v1 ใช้งานได้                                      ~12 วัน
D8. empirical matchup/synergy (context TEAM) + shrinkage     2 วัน
D9. กรอก attribute ให้ครบ 98 ตัวที่มีข้อมูล pro              ต่อเนื่อง
D10. matchup แยกเลน (context LANE)                          รอ vision
D11. fit น้ำหนักด้วย logistic regression                    หลังมี 400 แมตช์
```

**เหตุผลที่ D0 มาก่อน:** ข้อมูลที่ดึงได้เป็นตัวจัดลำดับว่าจะกรอก attribute
ฮีโร่ตัวไหนก่อน ถ้ากรอกก่อนดึง จะเดาว่าตัวไหนสำคัญ ซึ่งอาจผิด
และเพราะการดึงใช้เวลาเป็นวัน ยิ่งเริ่มเร็วยิ่งดี รันเบื้องหลังไปพร้อมกับงานอื่น

D8 ขยับขึ้นมาเร็วมากจากเดิม เพราะไม่ต้องรอ vision pipeline
`context: TEAM` คำนวณจาก draft data ล้วน ส่วน `context: LANE`
ยังต้องรอ role assignment จาก vision ตามเดิม
