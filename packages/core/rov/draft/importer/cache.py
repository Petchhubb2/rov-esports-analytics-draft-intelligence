"""Cache ของ response จาก Liquipedia

กฎเหล็ก: ทุก response ต้องถูกเก็บลงดิสก์ก่อนแปลงข้อมูล และห้ามยิงซ้ำ
สิ่งที่ cache ไว้แล้ว แม้ในตอนทดสอบ

เหตุผล: โควตาคือ 60 requests ต่อชั่วโมง การ debug parser ที่ต้องยิงใหม่ทุกครั้ง
จะกินโควตาหมดภายในไม่กี่นาที และอาจโดนแบน IP
"""

from __future__ import annotations

import gzip
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CacheEntry:
    key: str
    fetched_at: float
    url: str
    params: dict
    body: str

    @property
    def age_sec(self) -> float:
        return time.time() - self.fetched_at


class ResponseCache:
    """เก็บ response เป็นไฟล์ gzip ชื่อตาม hash ของ (url, params)"""

    def __init__(self, root: str | Path = "data/cache/liquipedia"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def make_key(url: str, params: dict) -> str:
        blob = url + "|" + json.dumps(params, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]

    def _path(self, key: str) -> Path:
        # แบ่งเป็นโฟลเดอร์ย่อยกันไฟล์เยอะเกินในไดเรกทอรีเดียว
        return self.root / key[:2] / f"{key}.json.gz"

    def get(self, url: str, params: dict, max_age_sec: float | None = None) -> CacheEntry | None:
        key = self.make_key(url, params)
        p = self._path(key)
        if not p.exists():
            return None
        try:
            with gzip.open(p, "rt", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, json.JSONDecodeError, EOFError):
            return None
        entry = CacheEntry(
            key=key,
            fetched_at=raw.get("fetched_at", 0.0),
            url=raw.get("url", url),
            params=raw.get("params", params),
            body=raw.get("body", ""),
        )
        if max_age_sec is not None and entry.age_sec > max_age_sec:
            return None
        return entry

    def put(self, url: str, params: dict, body: str) -> CacheEntry:
        key = self.make_key(url, params)
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        entry = CacheEntry(key=key, fetched_at=time.time(), url=url, params=params, body=body)
        tmp = p.with_suffix(".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as fh:
            json.dump(
                {
                    "fetched_at": entry.fetched_at,
                    "url": url,
                    "params": params,
                    "body": body,
                },
                fh,
                ensure_ascii=False,
            )
        tmp.replace(p)  # เขียนแบบ atomic กันไฟล์เสียเมื่อถูกขัดจังหวะ
        return entry

    def stats(self) -> dict:
        files = list(self.root.rglob("*.json.gz"))
        return {
            "entries": len(files),
            "bytes": sum(f.stat().st_size for f in files),
            "root": str(self.root),
        }
