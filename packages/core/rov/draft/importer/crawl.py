"""เดินเก็บหน้า Liquipedia ที่มีข้อมูล draft

โครงสร้างที่ตรวจสอบแล้วจากของจริง

    RoV Pro League/2026/Summer               หน้ารวม ไม่มี {{Match}}
      └── Tabs static ชี้ไปหน้าย่อย
            RoV Pro League/2026/Summer/Group Stage   มี 72 ซีรีส์ 360 เกม
            RoV Pro League/2026/Summer/Playoffs
            RoV Pro League/2026/Summer/Statistics    ไม่มี draft

ข้อค้นพบสำคัญ: หน้าย่อยหนึ่งหน้าให้เกมหลักร้อยเกม
การดึงจึงถูกกว่าที่ประเมินไว้มาก ไม่ใช่หนึ่ง request ต่อหนึ่งแมตช์
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rov.draft.importer.liquipedia import LiquipediaClient, LiquipediaError
from rov.draft.importer.parser import SeriesDraft, parse_page

# หน้าที่ไม่เคยมีข้อมูล draft — ข้ามเพื่อไม่ให้เปลืองโควตา
SKIP_SUFFIXES = ("/Statistics", "/Prize Pool", "/Participants", "/Broadcast Talent")


@dataclass
class CrawlResult:
    pages_fetched: list[str] = field(default_factory=list)
    pages_skipped: list[str] = field(default_factory=list)
    pages_failed: list[tuple[str, str]] = field(default_factory=list)
    series: list[SeriesDraft] = field(default_factory=list)

    @property
    def games(self) -> int:
        return sum(len(s.games) for s in self.series)

    @property
    def complete_games(self) -> int:
        return sum(len(s.complete_games) for s in self.series)


def normalize_title(title: str) -> str:
    """MediaWiki ถือว่า _ กับช่องว่างเท่ากัน และตัวอักษรแรกเป็นตัวใหญ่เสมอ

    ต้อง normalize ก่อน กันการดึงหน้าเดียวกันซ้ำซึ่งเปลืองโควตาโดยเปล่าประโยชน์
    พบจริงในหน้า GCS ที่มีทั้ง "Regular_Season" และ "Regular Season"
    """
    t = " ".join(title.replace("_", " ").split())
    return t[:1].upper() + t[1:] if t else t


def discover_subpages(wikitext: str, root: str) -> list[str]:
    """หาหน้าย่อยจาก {{Tabs static}} และลิงก์ภายในที่ชี้ลงหน้าลูก"""
    root_n = normalize_title(root)
    seen: set[str] = set()
    found: list[str] = []

    def add(raw: str) -> None:
        t = normalize_title(raw)
        # ต้องเป็นหน้าลูกจริง ไม่ใช่ตัวหน้ารวมเอง
        # เพราะ {{Tabs static}} มีลิงก์กลับมาหาหน้าตัวเองด้วย
        if not t.startswith(root_n + "/"):
            return
        if any(t.endswith(normalize_title(sfx)) for sfx in SKIP_SUFFIXES):
            return
        if t in seen:
            return
        seen.add(t)
        found.append(t)

    for m in re.finditer(r"\|link\d+\s*=\s*([^\n|}]+)", wikitext):
        add(m.group(1).strip())
    for m in re.finditer(r"\[\[([^\]|#]+)", wikitext):
        add(m.group(1).strip())
    return found


def crawl_tournament(
    client: LiquipediaClient,
    root: str,
    max_pages: int = 8,
    dry_run: bool = True,
) -> CrawlResult:
    """ดึงข้อมูล draft ของรายการแข่งหนึ่งรายการ

    dry_run=True (ค่าเริ่มต้น) จะไม่ยิง request ใหม่เลย
    ใช้เฉพาะหน้าที่อยู่ใน cache แล้ว เพื่อไม่ให้เผลอกินโควตา
    ต้องส่ง dry_run=False อย่างชัดแจ้งจึงจะยิงจริง
    """
    result = CrawlResult()

    def fetch(title: str) -> str | None:
        cached = client.cache.get(
            "https://liquipedia.net/honorofkings/api.php",
            {
                "action": "query",
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "titles": title,
                "format": "json",
                "formatversion": "2",
            },
        )
        if cached is None and dry_run:
            result.pages_skipped.append(title)
            return None
        try:
            return client.page_wikitext(title)
        except LiquipediaError as exc:
            result.pages_failed.append((title, str(exc)))
            return None

    root_text = fetch(root)
    if root_text is None:
        return result
    result.pages_fetched.append(root)

    # หน้ารวมเองอาจมี {{Match}} ในรายการเล็ก ๆ ที่ไม่ได้แยกหน้าย่อย
    result.series.extend(parse_page(root_text))

    targets = discover_subpages(root_text, root)
    for title in targets[:max_pages]:
        text = fetch(title)
        if text is None:
            continue
        result.pages_fetched.append(title)
        result.series.extend(parse_page(text))

    return result


def plan_crawl(client: LiquipediaClient, roots: list[str], pages_each: int = 3) -> dict:
    """ประมาณต้นทุนก่อนเริ่มดึงจริง — ต้องเรียกก่อนงานยาวเสมอ"""
    n = len(roots) * (1 + pages_each)
    plan = client.plan(n)
    plan["tournaments"] = len(roots)
    plan["pages_per_tournament"] = 1 + pages_each
    return plan
