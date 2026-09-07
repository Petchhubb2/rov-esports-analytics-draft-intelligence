# apps/web — หน้าเว็บ Draft Room

หน้าดราฟต์แบบคลิกได้ ใช้ข้อมูลจริงจาก Liquipedia

## ไฟล์

| ไฟล์ | คืออะไร |
|------|---------|
| `draft_board.tpl.html` | template · มี `__DATA__` เป็นที่วางข้อมูล |

## สร้างใหม่เมื่อดึงข้อมูลรายการเพิ่ม

```bash
# 1. ดึงข้อมูลรายการใหม่
rov draft import "ชื่อรายการ" --live
# แล้วเพิ่มรายการนั้นใน KNOWN_TOURNAMENTS ที่ rov/cli/main.py

# 2. ส่งออกข้อมูลเป็น JSON
python scripts/export_draft_data.py

# 3. ฝังข้อมูลลง template
python scripts/build_draft_page.py
```

ได้ไฟล์ `data/exports/draft_board.html` ที่เปิดในเบราว์เซอร์ได้เลย

## ลำดับ ban/pick

ค่าคงที่ `SEQ` ใน JavaScript **ต้องตรงกับ** `configs/draft/format.yaml`
ถ้าแก้ที่ไฟล์ config ต้องแก้ที่นี่ด้วย
