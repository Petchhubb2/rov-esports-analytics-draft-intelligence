"""Liquipedia API client

แหล่งข้อมูล draft ของ RoV Pro League ย้อนหลังถึงปี 2021
ดู docs/08-game-reference.md §8

ข้อกำหนดที่ต้องทำตาม (https://liquipedia.net/api-terms-of-use)
  - ระบุ User-Agent ที่บอกได้ว่าใครเป็นคนเรียกและติดต่อได้อย่างไร
  - เคารพ rate limit อย่างเคร่งครัด
  - cache ทุก response ห้ามยิงซ้ำ

client นี้ไม่ยิง request ใด ๆ ตอน import โมดูล และ dry_run เป็นค่าเริ่มต้น
ของ crawl เพื่อไม่ให้เผลอยิงจำนวนมากโดยไม่ตั้งใจ
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from rov.draft.importer.cache import ResponseCache
from rov.draft.importer.ratelimit import RateLimiter

BASE_URL = "https://liquipedia.net/honorofkings/api.php"
WIKI = "honorofkings"

# Liquipedia กำหนดให้ User-Agent บอกชื่อโครงการและช่องทางติดต่อ
DEFAULT_UA = (
    "RoVEsportsAnalytics/0.1 (research/scouting tool; "
    "contact via ROV_CONTACT_EMAIL env var)"
)


class LiquipediaError(RuntimeError):
    pass


class RateLimitBanned(LiquipediaError):
    """โดนแบนเพราะยิงถี่เกิน — ต้องหยุดทันที ห้าม retry"""


@dataclass
class ClientStats:
    requests_made: int = 0
    cache_hits: int = 0
    seconds_waited: float = 0.0
    errors: int = 0

    def as_dict(self) -> dict:
        total = self.requests_made + self.cache_hits
        return {
            "requests_made": self.requests_made,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": round(self.cache_hits / total, 3) if total else 0.0,
            "seconds_waited": round(self.seconds_waited, 1),
            "errors": self.errors,
        }


@dataclass
class LiquipediaClient:
    """client ที่บังคับ rate limit และ cache ให้อัตโนมัติ"""

    contact: str | None = None
    cache_root: str | Path = "data/cache/liquipedia"
    state_path: str | Path = "data/cache/liquipedia/_ratelimit.json"
    timeout: float = 30.0
    user_agent: str | None = None

    cache: ResponseCache = field(init=False)
    limiter: RateLimiter = field(init=False)
    stats: ClientStats = field(init=False, default_factory=ClientStats)

    def __post_init__(self) -> None:
        self.cache = ResponseCache(self.cache_root)
        self.limiter = RateLimiter(state_path=self.state_path)
        contact = self.contact or os.environ.get("ROV_CONTACT_EMAIL")
        if self.user_agent is None:
            self.user_agent = (
                f"RoVEsportsAnalytics/0.1 (research/scouting tool; {contact})"
                if contact
                else DEFAULT_UA
            )

    # ------------------------------------------------------------------

    def _get(self, params: dict[str, Any], kind: str = "general") -> str:
        """ยิง request หนึ่งครั้ง โดยใช้ cache ก่อนเสมอ"""
        cached = self.cache.get(BASE_URL, params)
        if cached is not None:
            self.stats.cache_hits += 1
            return cached.body

        waited = self.limiter.acquire(kind)
        self.stats.seconds_waited += waited

        headers = {"User-Agent": self.user_agent, "Accept-Encoding": "gzip"}
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as c:
                resp = c.get(BASE_URL, params=params, headers=headers)
        except httpx.HTTPError as exc:
            self.stats.errors += 1
            raise LiquipediaError(f"เรียก Liquipedia ไม่สำเร็จ: {exc}") from exc

        self.stats.requests_made += 1

        if resp.status_code == 429:
            self.stats.errors += 1
            raise RateLimitBanned(
                "Liquipedia ตอบ 429 — ยิงถี่เกินไป หยุดทันที ห้าม retry "
                "และรอจนกว่าจะพ้นช่วงแบน"
            )
        if resp.status_code >= 400:
            self.stats.errors += 1
            raise LiquipediaError(f"HTTP {resp.status_code} จาก Liquipedia")

        body = resp.text
        self.cache.put(BASE_URL, params, body)
        return body

    # ------------------------------------------------------------------

    def query_category(self, category: str, limit: int = 50, cont: str | None = None) -> dict:
        """ดึงรายชื่อหน้าในหมวดหนึ่ง เช่นรายการแข่งทั้งหมด"""
        params: dict[str, Any] = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": min(limit, 500),
            "format": "json",
        }
        if cont:
            params["cmcontinue"] = cont
        import json as _json

        return _json.loads(self._get(params))

    def page_wikitext(self, title: str) -> str:
        """ดึง wikitext ดิบของหน้าหนึ่ง

        ใช้ action=query&prop=revisions ซึ่งอยู่ใต้เพดาน 1 ครั้ง/2 วินาที
        ไม่ใช่ action=parse ที่ถูกจำกัดหนักกว่าถึง 1 ครั้ง/30 วินาที
        """
        import json as _json

        params = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": title,
            "format": "json",
            "formatversion": "2",
        }
        data = _json.loads(self._get(params))
        pages = data.get("query", {}).get("pages", [])
        if not pages:
            raise LiquipediaError(f"ไม่พบหน้า: {title}")
        page = pages[0]
        if page.get("missing"):
            raise LiquipediaError(f"ไม่พบหน้า: {title}")
        try:
            return page["revisions"][0]["slots"]["main"]["content"]
        except (KeyError, IndexError) as exc:
            raise LiquipediaError(f"รูปแบบผลลัพธ์ผิดคาดสำหรับหน้า {title}") from exc

    def site_info(self) -> dict:
        """เรียกเบา ๆ ไว้ทดสอบว่า client ทำงานและ UA ผ่าน"""
        import json as _json

        return _json.loads(
            self._get(
                {
                    "action": "query",
                    "meta": "siteinfo",
                    "siprop": "general",
                    "format": "json",
                }
            )
        )

    # ------------------------------------------------------------------

    def plan(self, n_requests: int) -> dict:
        """ประมาณเวลาก่อนเริ่ม crawl — ต้องเรียกก่อนงานยาวเสมอ"""
        sec = self.limiter.estimate_seconds(n_requests)
        return {
            "requests": n_requests,
            "estimated_seconds": round(sec),
            "estimated_hours": round(sec / 3600, 2),
            "remaining_this_hour": self.limiter.remaining_this_hour,
        }
