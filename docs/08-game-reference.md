# 08 — Game Reference · ข้อมูลเกมที่ตรวจสอบแล้ว

ค้นเมื่อ **2026-09-06** ทุกข้อมีที่มากำกับ
ข้อมูลที่ยังไม่ยืนยันจะระบุว่า ⚠️ **ต้องยืนยัน**

> **คำเตือนสำคัญ:** แพตช์ 26 มิถุนายน 2026 มี "major jungle system changes"
> และ "battlefield adjustment" แต่เนื้อหาเต็มของแพตช์อ่านไม่ได้จากเว็บ Garena
> (หน้าเว็บ render ด้วย JavaScript) **ตัวเลขเวลาเกิดของ jungle ทั้งหมดในเอกสารนี้
> มาจากแหล่งก่อนหน้าแพตช์นั้น และต้องวัดซ้ำจากคลิปจริง**

---

## 1. เวอร์ชันและขนาดของเกม

| รายการ | ค่า | ที่มา |
|--------|-----|-------|
| แพตช์ปัจจุบัน | **1.63** | rovmeta.com (ก.ย. 2026) |
| จำนวนฮีโร่ทั้งหมด | **126** ตัว ล่าสุดคือ Dyadia | AoV Wiki |
| ฮีโร่ที่มีข้อมูลระดับ pro | **98** ตัว | rovmeta.com |
| แพตช์ล่าสุดที่มีผลต่อ macro | 26 มิ.ย. 2026 (jungle + battlefield) | Garena AOV |
| ฮีโร่ใหม่ปี 2026 | Flowborn (23 เม.ย.), Tamyn (26 มิ.ย.) | Garena AOV |

**ผลต่อการออกแบบ:** ตัวเลข 126 ฮีโร่กระทบแผนกรอก hero attribute ใน
[06-draft-engine.md](06-draft-engine.md) โดยตรง ดูข้อ 6 ด้านล่าง

---

## 2. แมพ Antaris Battlefield

โครงสร้างที่ยืนยันแล้ว

```
ฐานสองฝั่ง · 3 เลน · แม่น้ำผ่ากลาง · ป่า 4 ส่วนต่อฝั่ง
```

| องค์ประกอบ | รายละเอียด | ที่มา |
|-----------|-----------|-------|
| ชื่อแมพ 5v5 | Antaris Battlefield | AoV Wiki |
| จำนวนเลน | 3 | ยืนยัน |
| ชื่อเลน | **Dark Slayer Lane (DS)** · **Middle Lane** · **Abyssal Dragon Lane** | samurai-gamers, gamingonphone |
| ป่า | 4 ส่วนต่อฝั่งของเลนกลาง ทั้งสองครึ่งแมพ | samurai-gamers |
| แม่น้ำ | ผ่ากลางแมพ | samurai-gamers |
| Super minion | เกิดเมื่อทำลาย inner turret ครบทั้ง 3 | gamingonphone |

⚠️ **ต้องยืนยันจากคลิปจริง:** เลนใดอยู่ด้านบนของ minimap และเลนใดอยู่ด้านล่าง
ฐานน้ำเงินอยู่มุมใด minimap เป็นจัตุรัสตรงหรือถูกบิดมุม

เอกสารบนเว็บไม่ระบุเรขาคณิตของแมพในระดับที่ใช้วาด polygon ได้
**นี่เป็นเหตุผลที่ zone polygon ต้องมาจากการวัดบนภาพจริงเท่านั้น**
ตามที่ออกแบบไว้ใน Phase 0 ไม่ใช่จากเอกสาร

### ตำแหน่งสัมพัทธ์ของ objective

Dark Slayer และ Spirit Sentinel อยู่บนครึ่งเดียวกันของแม่น้ำ
ดังนั้น Abyssal Dragon จะอยู่ฝั่งที่มี large monster camp เพียงตัวเดียวเสมอ
(ที่มา: samurai-gamers)

ข้อนี้ใช้ตรวจสอบความถูกต้องของ zone config ได้: ถ้าวาด polygon แล้ว
SLAYER_PIT กับ SPIRIT_SENTINEL อยู่คนละครึ่งแม่น้ำ แสดงว่าวาดผิด

---

## 3. เวลาเกิดของ Objective และ Jungle

⚠️ **ทั้งตารางนี้มาจากแหล่งก่อนแพตช์ 26 มิ.ย. 2026 ต้องวัดซ้ำ**

โหมด Grand Battle (5v5 Antaris Battlefield)

| สิ่ง | เกิดครั้งแรก | เกิดใหม่ทุก |
|------|-------------|-------------|
| Minion | 0:10 | 33–35 วินาที |
| Siege minion | 5:00 | ตามรอบ |
| Jungle ตัวเล็ก | 0:28 | 1:10 |
| Might / Sage Golem | 0:30 | 1:30 |
| Seagle | 0:30 | 1:00 |
| **Spirit Sentinel** | **1:50** | **2:00** |
| **Abyssal Dragon** | **2:00** | **2:00** |
| **Enraged Abyssal Dragon** | **10:00** | **5:00** |
| **Dark Slayer** | **8:00** | **5:00** |
| Health pack (หลังป้อมชั้น 1) | 0:50 | 1:15 หลังใช้ · หายเมื่อป้อมพัง |

ที่มา: samurai-gamers "All Minion, Monster, and Item Timings"

### ผลต่อการออกแบบ Event Detection

ตัวเลขเหล่านี้ทำให้ `objective_timer` ใน [05-macro-events.md](05-macro-events.md)
คำนวณจากตารางได้เลย โดยไม่ต้องพึ่ง OCR

```python
def next_dragon_spawn(clock, last_killed):
    if clock < 10*60:
        base, interval = 120, 120        # Abyssal Dragon
    else:
        base, interval = 600, 300        # Enraged
    ...

def next_slayer_spawn(clock, last_killed):
    base, interval = 480, 300            # 8:00 แล้วทุก 5 นาที
```

แต่ต้องมีการยืนยันจากภาพด้วย เพราะ objective ที่ยังไม่ถูกฆ่าจะไม่เกิดใหม่
ดูข้อ 4 ที่ให้วิธียืนยันจาก minimap โดยตรง

### ค่าพารามิเตอร์ที่ตั้งได้จากตารางนี้

| พารามิเตอร์ | ค่าที่ควรใช้ | เหตุผล |
|-------------|-------------|--------|
| `setup_lead_sec` | 45 | Dragon เกิดใหม่ทุก 120 วินาที การรวมตัวก่อน 45 วินาทีจึงสมเหตุสมผล |
| `slayer_setup_lead_sec` | 60 | Slayer รอบยาวกว่า (300 วินาที) และเป็น objective ที่วางแผนล่วงหน้ามากกว่า |
| ช่วงสุ่มเฟรมถี่ | รอบเวลา 2:00, 8:00, 10:00 และทุก 5 นาทีหลังจากนั้น | ช่วงที่เกิด objective fight |

---

## 4. Minimap · ข้อมูลที่อ่านได้เพิ่มจากที่วางแผนไว้

พบข้อมูลที่แผนเดิมและเอกสารออกแบบชุดแรกยังไม่ได้ใช้

| สิ่งที่ minimap แสดง | รายละเอียด | ที่มา |
|---------------------|-----------|-------|
| **สถานะป้อม** | icon ป้อม "ค่อย ๆ จางสีลงตามความเสียหาย และหายไปเมื่อถูกทำลาย" | samurai-gamers |
| **สถานะ Dragon** | mark **สีเหลือง** เมื่อมีชีวิต · **สีเทา** เมื่อเพิ่งถูกฆ่า | samurai-gamers |
| ตำแหน่ง minion | แสดงในเลน | samurai-gamers |
| สถานะเลน | "Lane status can now be seen clearly on the Mini-Map" | AoV official |
| หลอดเลือด/เวลาเกิดของเพื่อนร่วมทีม | แสดงบน minimap | samurai-gamers |

### ผลกระทบสามข้อ

**1. objective_timer อ่านได้จาก minimap โดยตรง** 🟢 ข่าวดี

สี mark ของ Dragon (เหลือง/เทา) บอกว่า objective ยังอยู่หรือถูกฆ่าไปแล้ว
เป็น ROI คงที่ตำแหน่งเดียว อ่านง่ายกว่า OCR มาก
ทำให้ `OBJECTIVE_TAKEN` event ตรวจได้แม่นโดยไม่ต้องแตะ main view เลย

เพิ่มเข้า pipeline: `minimap/objective_state.py` อ่านสีที่พิกัดคงที่ 2 จุด
งานครึ่งวัน ได้ event ที่มีค่าสูงมาก

**2. Background model ต้องรับมือกับป้อมที่จางลงและหายไป** 🟠 ข้อควรระวัง

ยืนยันความกังวลที่เขียนไว้ใน [04-vision-pipeline.md](04-vision-pipeline.md) §4.1
ป้อมเปลี่ยนสีตลอดเกม ไม่ใช่แค่หายตอนถูกทำลาย

แนวทางที่ควรใช้: **rolling median แบบหน้าต่างเลื่อน** ไม่ใช่ median ครั้งเดียวทั้งเกม
หน้าต่างแนะนำ 60–90 วินาที ยาวพอจะลบ hero icon ออก
แต่สั้นพอจะตามการเปลี่ยนสีของป้อมทัน

**3. minion บนเลนคือแหล่ง false positive หลัก** 🟠

minion แสดงบน minimap และเคลื่อนที่ จึงรอดจาก background subtraction
ต้องพึ่งการกรองด้วย area, saturation และ circularity เป็นหลัก
และควรใส่ "lane corridor mask" เพื่อลดน้ำหนักของ detection ที่อยู่กลางเลนพอดี
และมีขนาดเล็ก

---

## 5. Fog of War — คำถาม G1 ยังไม่มีคำตอบจากเว็บ

สิ่งที่ยืนยันได้

| ข้อ | สถานะ |
|-----|-------|
| minimap ของ **ผู้เล่น** มี fog of war ซ่อนศัตรูที่ไม่มี vision | ✅ ยืนยันแล้ว (samurai-gamers) |
| fog เปิด/ปิดได้ในการตั้งค่า custom match | ✅ ยืนยันแล้ว (AoV official) |
| minimap ของ **spectator/broadcast** มี fog หรือไม่ | ❌ **หาไม่พบ** |

ค้นหลายรอบด้วยคำค้นต่างกันแล้ว ไม่มีเอกสารสาธารณะที่ระบุพฤติกรรมของ
observer mode ใน AoV

**ข้อสรุป: G1 ยังคงเป็นคำถามที่ต้องตอบด้วยการเปิดคลิปจริงเท่านั้น**
การค้นเว็บยืนยันว่าไม่มีทางลัด และการที่ fog ตั้งค่าได้ในระดับ custom match
ยิ่งทำให้ต้องตรวจ **ต่อรายการแข่ง** ไม่ใช่ตรวจครั้งเดียวแล้วใช้กับทุกคลิป

เพิ่มฟิลด์นี้เข้า `configs/layouts/*.yaml` ตามที่ออกแบบไว้แล้ว ถูกต้อง

---

## 6. ตำแหน่งผู้เล่น 5 ตำแหน่ง

| ตำแหน่ง | ชื่อไทย | หน้าที่ |
|---------|---------|---------|
| Dark Slayer Lane | ออฟเลน / DS | ยืนเดี่ยว ดวล 1v1 ดันเลน เข้าฟightช่วงหลัง |
| Jungle | ป่า | ฟาร์มเร็ว คุม objective แกงค์ |
| Middle Lane | มิด / เมจ | เคลียร์มินเนี่ยนเร็ว โรมช่วยเลนอื่น คุมพื้นที่ |
| Abyssal Dragon Lane | แครี่ / ADC | ดาเมจหลักช่วงท้าย ต้องฟาร์ม |
| Support | ซัพพอร์ต | เปิด vision คุมพื้นที่ กันแกงค์ ปกป้องแครี่ |

ที่มา: sanook.com, pantip, id2u.co

### Hero class (ต่างจากตำแหน่งเลน)

`marksman · mage · assassin · tank · warrior · support`
ฮีโร่บางตัวมี 2 class โดยตัวแรกเป็น class หลัก (ที่มา: AoV Wiki)

**ผลต่อ schema:** ใน `configs/draft/heroes.yaml` ต้องแยกสองแนวคิดนี้ให้ชัด

```yaml
hero_class: [assassin, warrior]   # class ตามเกม ตัวแรกคือหลัก
lane_roles: [jungle, ds]          # เลนที่เล่นได้จริงในระดับ pro
```

เอกสารออกแบบเดิมใช้ `primary_role` และ `roles` ปนกันอยู่ ต้องแก้

---

## 7. รูปแบบ Draft ของ RoV Pro League

### Global Ban-Pick — ชื่อทางการของกติกา fearless แบบอ่อน

กติกาที่ใช้จริงใน RPL 2026 (ที่มา: Liquipedia RoV Pro League 2026 Summer)

```
Bo3 / Bo5
  แต่ละทีมห้ามเลือกฮีโร่ที่ "ตัวเอง" ใช้ไปแล้วในเกมก่อนหน้า
  การเลือกฮีโร่ที่ "ฝ่ายตรงข้าม" เคยใช้ ไม่ถูกจำกัด

Bo7
  กติกาข้างต้นใช้กับเกมที่ 1–6
  เกมที่ 7 กลับเป็น Normal Ban-Pick ฮีโร่ทั้งหมดกลับมาเลือกได้

การเลือกฝั่ง
  ทีมที่อยู่ฝั่งซ้ายของตารางแข่ง (ทีม "เหย้า") ได้สิทธิ์เลือกฝั่งในเกมแรก
```

นี่คือ **soft fearless** ไม่ใช่ full fearless
ต่างจากที่ League of Legends ใช้อยู่ ซึ่งมีทั้งสองแบบ

### ผลต่อการออกแบบ

เอกสารเดิมใน [06-draft-engine.md](06-draft-engine.md) เขียนว่า
"ถ้า format เป็น fearless draft ให้ตัดฮีโร่ที่ใช้ในเกมก่อนหน้าของซีรีส์ออก"
ซึ่งกว้างเกินไป ต้องแก้เป็น

```yaml
# configs/draft/format.yaml
id: rpl_2026
global_ban_pick:
  enabled: true
  scope: own_team_only      # own_team_only | both_teams
  reset_on_final_game: true # Bo7 เกมที่ 7 รีเซ็ต
  applies_to_bans: false    # จำกัดเฉพาะ pick ไม่รวม ban
```

`scope: own_team_only` เปลี่ยน draft engine อย่างมีนัยสำคัญ
เพราะการ "เผา" ฮีโร่ของตัวเองในเกมแรกมีต้นทุนเชิงกลยุทธ์
ที่ระบบต้องคำนวณได้: pick ฮีโร่แข็งเกมแรกแปลว่าเกมต่อไปไม่มีตัวนั้น

นี่เป็นมิติที่แผนเดิมไม่ได้พูดถึงเลย และเป็นสิ่งที่โค้ชต้องการจริง
**ข้อเสนอ:** เพิ่ม `series_value` เข้า draft recommendation
คือคะแนนที่หักลบมูลค่าของการเสียฮีโร่นั้นไปตลอดซีรีส์

⚠️ **ต้องยืนยัน:** ลำดับ ban/pick ที่แน่นอน (ban กี่ตัว เรียงอย่างไร)
หาจากเว็บไม่พบ ต้องดูจากคลิปแข่งจริงหรือ rulebook ทางการ
การออกแบบให้ลำดับอยู่ใน config จึงเป็นการตัดสินใจที่ถูกต้อง

---

## 8. แหล่งข้อมูล Draft — แก้ปัญหา Cold Start ได้จริง 🟢

นี่คือสิ่งที่มีค่าที่สุดที่ได้จากการค้นครั้งนี้

### Liquipedia API

| รายการ | รายละเอียด |
|--------|-----------|
| ข้อมูลที่มี | **Draft Order (picks & bans)** ต่อแมตช์ ผลแพ้ชนะ ทีม ผู้เล่น รายการแข่ง |
| ครอบคลุม | RoV Pro League ย้อนหลังถึงปี 2021 |
| Rate limit | 60 requests/ชั่วโมง · ทั่วไป 1 request/2 วินาที · `action=parse` 1 request/30 วินาที |
| ข้อกำหนด | ต้องยอมรับ API Terms of Use · ละเมิดแล้วโดนแบน IP |
| ไลบรารี | `liquipediapy` บน PyPI |

### rovmeta.com

สถิติ win / pick / ban rate ระดับ pro league เฉลี่ยหลายแพตช์ (ปัจจุบัน 1.63)
ครอบคลุม 98 ฮีโร่ ไม่มี API และเป็นเว็บแฟนไซต์ที่ดึงข้อมูลจาก Liquipedia อีกที
ใช้เป็นตัว **ตรวจสอบความถูกต้อง** ของข้อมูลที่เราดึงมาเอง ไม่ใช่แหล่งหลัก

### แผนใหม่สำหรับ D8

เดิมเขียนไว้ว่า "กรอก draft data ด้วยมือ 200 แมตช์ ใช้เวลา 7 ชั่วโมง"
**แก้เป็น:** เขียน importer ดึงจาก Liquipedia API

```
D8a  เขียน importer + เคารพ rate limit + cache ลงดิสก์     2 วัน
D8b  map ชื่อฮีโร่ Liquipedia → hero_id ของเรา              0.5 วัน
D8c  ดึงย้อนหลัง RPL 2024–2026                              รันข้ามคืน
```

ที่ 60 requests/ชั่วโมง การดึงหลายร้อยแมตช์ต้องใช้เวลาเป็นวัน
ให้รันเป็น background job ที่ resume ได้ และ cache ทุก response ลงดิสก์
**ห้ามยิงซ้ำ** เพราะจะโดนแบน IP

ผลลัพธ์: ได้ข้อมูล draft หลักร้อยถึงหลักพันแมตช์โดยไม่ต้องกรอกมือ
และไม่ต้องรอ vision pipeline เลย **Draft v2 จึงเริ่มได้เร็วกว่าที่วางแผนไว้มาก**

---

## 9. แก้แผนกรอก Hero Attribute

ตัวเลข 126 ฮีโร่ทำให้แผนเดิม (กรอกทุกตัว) ใช้เวลานานเกินไป

**แผนใหม่ — กรอกตามลำดับความสำคัญ**

| รอบ | ขอบเขต | จำนวน | เวลา |
|-----|--------|-------|------|
| 1 | ฮีโร่ที่มี pick rate สูงสุดใน patch ปัจจุบัน | ~30 | 1 วัน |
| 2 | ฮีโร่ที่มีข้อมูล pro league | ~98 | 2–3 วัน |
| 3 | ที่เหลือ | 126 | ตามสะดวก |

ใช้ pick + ban rate จาก Liquipedia เป็นตัวจัดลำดับ
ฮีโร่ที่ไม่เคยถูก pick หรือ ban ในระดับ pro แทบไม่มีผลต่อ draft engine
รอบที่ 1 ครอบคลุมกรณีใช้งานจริงส่วนใหญ่แล้ว

---

## 10. สรุปสิ่งที่ต้องแก้ในเอกสารชุดเดิม

| เอกสาร | แก้อะไร | สถานะ |
|--------|---------|-------|
| 01-assessment | G1 ระบุว่าค้นเว็บแล้วไม่มีคำตอบ · G7 เปลี่ยนเป็นดึง API | ✅ แก้แล้ว |
| 04-vision-pipeline | background เป็น rolling median · เพิ่มการอ่านสถานะ objective จากสี icon | ✅ แก้แล้ว |
| 05-macro-events | ใส่เวลาเกิด objective จริง · เพิ่ม OBJECTIVE_TAKEN | ✅ แก้แล้ว |
| 06-draft-engine | Global Ban-Pick · แยก hero_class จาก lane_roles · series value | ✅ แก้แล้ว |
| 07-roadmap | D8 เปลี่ยนจากกรอกมือเป็น importer | ✅ แก้แล้ว |

---

## แหล่งข้อมูล

- [Patch Notes 26 June 2026 — Garena AOV](https://main.aov.garena.co.id/post/patch-notes26jun26-en)
- [Patch Notes 21 May 2026 — Garena AOV](https://main.aov.garena.co.id/post/patch-notes21may26-en)
- [Patch Notes 5 February 2026 — Garena AOV](https://main.aov.garena.co.id/post/patch-notes5feb26-en)
- [ROV META — pro league win/pick/ban stats, patch 1.63](https://rovmeta.com/stats)
- [All Minion, Monster, and Item Timings — Samurai Gamers](https://samurai-gamers.com/arena-of-valor/all-minion-monster-and-item-timings/)
- [Using the Mini-map — Samurai Gamers](https://samurai-gamers.com/arena-of-valor/mini-map/)
- [Abyssal Dragon: Strategy and Benefits — Samurai Gamers](https://samurai-gamers.com/arena-of-valor/abyssal-dragon-strategy-and-benefits/)
- [Antaris Battlefield Redesign — Samurai Gamers](https://samurai-gamers.com/arena-of-valor/antaris-battlefield-redesign/)
- [The Dark Slayer — Arena of Valor Wiki](https://arenaofvalor.fandom.com/wiki/The_Dark_Slayer)
- [Heroes — Arena of Valor Wiki](https://arenaofvalor.fandom.com/wiki/Heroes)
- [How to play the Map in Arena of Valor — GamingonPhone](https://gamingonphone.com/guides/how-to-play-the-map-in-arena-of-valor/)
- [RoV Pro League 2026 Summer — Liquipedia](https://liquipedia.net/honorofkings/RoV_Pro_League/2026/Summer)
- [Liquipedia API](https://liquipedia.net/api)
- [Liquipedia API Terms of Use](https://liquipedia.net/api-terms-of-use)
- [liquipediapy — PyPI](https://pypi.org/project/liquipediapy/)
- [เกม RoV มีตำแหน่งอะไรบ้าง — Sanook](https://www.sanook.com/game/1186442/)
