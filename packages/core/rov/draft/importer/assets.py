"""ดาวน์โหลดภาพ hero icon จาก Liquipedia Commons

ใช้สองอย่าง
    1. แสดงในหน้าเว็บ draft
    2. **สร้าง template สำหรับ hero identification** (docs/04-vision-pipeline.md §5.2)
       ซึ่งเป็นงานของ System 04 ที่ยังไม่ได้เริ่ม
       ภาพ 100x100 ย่อลงเป็น 16x16 ใช้เทียบกับ icon บน minimap ได้

## เรื่องลิขสิทธิ์ที่ต้องรู้ก่อนขึ้นเซิร์ฟเวอร์จริง

เนื้อหา *ข้อความ* ของ Liquipedia เป็น CC-BY-SA 3.0 ต้องให้เครดิต
แต่ **ภาพฮีโร่เป็นงานศิลป์ของ Garena/TiMi** ไม่ใช่ของ Liquipedia
Liquipedia โฮสต์ไว้ในฐานะสื่อประกอบ ไม่ได้เป็นเจ้าของลิขสิทธิ์

    ใช้ในเครื่อง / ในทีม        เป็นแนวปฏิบัติปกติของเครื่องมือวิเคราะห์
    ทำ CV template             เป็นการประมวลผลภายใน ไม่ใช่การเผยแพร่ซ้ำ
    เผยแพร่บนเว็บสาธารณะ        ต้องพิจารณาเรื่องลิขสิทธิ์ก่อน

ดังนั้นไฟล์ที่ดาวน์โหลดจึงถูก gitignore ไว้ และไม่ควรฝังลงหน้าเว็บที่เผยแพร่
โดยไม่ได้ตรวจสอบเรื่องนี้ก่อน
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from rov.draft.importer.liquipedia import LiquipediaClient
from rov.draft.importer.parser import normalize_hero_id

PORTAL_PAGE = "Portal:Heroes/Arena of Valor"
# API ยอมให้ส่งได้ 50 titles ต่อครั้ง จึงลดจาก 133 requests เหลือ 3
TITLES_PER_QUERY = 50
# ดาวน์โหลดไฟล์ตรง ไม่ผ่าน API แต่ยังต้องเคารพกติกา 1 ครั้ง/2 วินาที
FILE_DELAY_SEC = 2.1

_GALLERY_ROW = re.compile(r"(File:[^|\n]+?)\s*\|\s*link=([^|\]\n]+)")


@dataclass
class AssetResult:
    resolved: dict[str, str] = field(default_factory=dict)  # hero_id -> url
    downloaded: list[str] = field(default_factory=list)
    cached: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)

    def report(self) -> str:
        lines = [
            f"หา URL ได้        {len(self.resolved)}",
            f"ดาวน์โหลดใหม่      {len(self.downloaded)}",
            f"มีอยู่แล้ว          {len(self.cached)}",
        ]
        if self.unresolved:
            lines.append(f"หา URL ไม่ได้      {len(self.unresolved)}: "
                         + ", ".join(self.unresolved[:10]))
        if self.failed:
            lines.append(f"ดาวน์โหลดพลาด      {len(self.failed)}")
            for name, err in self.failed[:5]:
                lines.append(f"    {name}: {err}")
        return "\n".join(lines)


def safe_filename(hero_id: str) -> str:
    """ชื่อไฟล์ที่ปลอดภัย

    hero_id บางตัวมาจากลิงก์หน้าย่อยของ Liquipedia เช่น "Flowborn/Mage"
    ถ้าเอาไปตั้งชื่อไฟล์ตรง ๆ เครื่องหมาย / จะกลายเป็นตัวแบ่งโฟลเดอร์
    แล้วเขียนไฟล์ไม่ได้ (เกิดขึ้นจริงตอนดาวน์โหลดรอบแรก)
    """
    out = []
    for ch in hero_id:
        out.append(ch if (ch.isalnum() or ch in "_-") else "_")
    return "".join(out).strip("_") or "unknown"


def hero_image_titles(client: LiquipediaClient) -> dict[str, str]:
    """hero_id -> ชื่อไฟล์ภาพ จากหน้า Portal (ใช้ cache ได้)

    ลิงก์แบบ "Flowborn/Mage" คือหน้าย่อยของร่างหรือสกิน
    ตัวฮีโร่คือส่วนก่อนเครื่องหมาย / จึงตัดส่วนหลังทิ้ง
    """
    text = client.page_wikitext(PORTAL_PAGE)
    out: dict[str, str] = {}
    for file_name, hero in _GALLERY_ROW.findall(text):
        hid = normalize_hero_id(hero.split("/")[0])
        if not hid:
            continue
        # แต่ละฮีโร่โผล่หลาย gallery เก็บอันแรกพอ
        out.setdefault(hid, file_name.strip())
    return out


def resolve_urls(client: LiquipediaClient, titles: list[str]) -> dict[str, str]:
    """ชื่อไฟล์ -> URL จริง โดยส่งทีละ 50 ชื่อเพื่อประหยัดโควตา"""
    urls: dict[str, str] = {}
    for i in range(0, len(titles), TITLES_PER_QUERY):
        batch = titles[i : i + TITLES_PER_QUERY]
        raw = client._get(
            {
                "action": "query",
                "titles": "|".join(batch),
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
                "format": "json",
                "formatversion": "2",
            }
        )
        for page in json.loads(raw).get("query", {}).get("pages", []):
            info = page.get("imageinfo") or []
            if info and info[0].get("url"):
                urls[page["title"]] = info[0]["url"]
    return urls


def download_hero_icons(
    client: LiquipediaClient,
    out_dir: str | Path = "data/assets/heroes",
    only: set[str] | None = None,
    delay: float = FILE_DELAY_SEC,
    sleep=time.sleep,
) -> AssetResult:
    """ดาวน์โหลดภาพฮีโร่ ข้ามไฟล์ที่มีอยู่แล้ว

    only  จำกัดเฉพาะ hero_id ที่ระบุ (เช่นเฉพาะตัวที่อยู่ในเมตา)
    """
    res = AssetResult()
    dest = Path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    # เขียนที่มาก่อนเริ่มโหลด เผื่อถูกขัดจังหวะกลางทาง
    # ไฟล์ภาพที่ไม่มีที่มากำกับคือปัญหาที่รอวันเกิด
    _write_attribution(dest)

    by_hero = hero_image_titles(client)
    if only is not None:
        by_hero = {h: f for h, f in by_hero.items() if h in only}

    urls = resolve_urls(client, sorted(set(by_hero.values())))

    headers = {"User-Agent": client.user_agent}
    manifest_path = dest / "_manifest.json"
    manifest: dict[str, dict] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}

    with httpx.Client(timeout=30.0, follow_redirects=True) as http:
        for hero_id, title in sorted(by_hero.items()):
            url = urls.get(title)
            if not url:
                res.unresolved.append(hero_id)
                continue
            res.resolved[hero_id] = url

            ext = Path(url).suffix.lower() or ".jpg"
            target = dest / f"{safe_filename(hero_id)}{ext}"
            if target.exists() and target.stat().st_size > 0:
                res.cached.append(hero_id)
                continue

            sleep(delay)  # เคารพกติกา 1 request/2 วินาที
            try:
                r = http.get(url, headers=headers)
                r.raise_for_status()
                target.write_bytes(r.content)
            except httpx.HTTPError as exc:
                res.failed.append((hero_id, str(exc)))
                continue

            res.downloaded.append(hero_id)
            manifest[hero_id] = {
                "file": target.name,
                "source": url,
                "title": title,
                "bytes": len(r.content),
            }

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return res


def _write_attribution(dest: Path) -> None:
    """บันทึกที่มาไว้คู่กับไฟล์เสมอ — ทั้งเพื่อให้เครดิตและเพื่อเตือนตัวเอง"""
    (dest / "ATTRIBUTION.md").write_text(
        "# ที่มาของภาพ\n\n"
        "ภาพในโฟลเดอร์นี้ดึงมาจาก Liquipedia Commons\n"
        "<https://liquipedia.net/honorofkings/Portal:Heroes/Arena_of_Valor>\n\n"
        "## ลิขสิทธิ์\n\n"
        "- ข้อความและข้อมูลของ Liquipedia อยู่ภายใต้ CC-BY-SA 3.0 ต้องให้เครดิต\n"
        "- **ภาพฮีโร่เป็นงานศิลป์ของ Garena / TiMi Studios** ไม่ใช่ของ Liquipedia\n"
        "  Liquipedia โฮสต์ไว้ในฐานะสื่อประกอบเท่านั้น\n\n"
        "## ใช้ได้แค่ไหน\n\n"
        "| การใช้งาน | สถานะ |\n"
        "|-----------|-------|\n"
        "| ในเครื่อง / ในทีม | แนวปฏิบัติปกติของเครื่องมือวิเคราะห์ |\n"
        "| ทำ template ให้ CV | เป็นการประมวลผลภายใน ไม่ใช่การเผยแพร่ซ้ำ |\n"
        "| เผยแพร่บนเว็บสาธารณะ | **ต้องตรวจสอบเรื่องลิขสิทธิ์ก่อน** |\n\n"
        "ไฟล์เหล่านี้ถูก gitignore ไว้ และไม่ควรฝังลงหน้าเว็บที่เผยแพร่สาธารณะ\n"
        "โดยยังไม่ได้ตรวจสอบ\n",
        encoding="utf-8",
    )
