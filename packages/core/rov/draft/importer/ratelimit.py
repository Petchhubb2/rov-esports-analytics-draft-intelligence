"""ตัวจำกัดอัตราการเรียก Liquipedia API

ข้อกำหนดของ Liquipedia (https://liquipedia.net/api-terms-of-use)

    ไม่เกิน 60 requests ต่อชั่วโมง
    request ทั่วไป  ไม่เกิน 1 ครั้งต่อ 2 วินาที
    action=parse    ไม่เกิน 1 ครั้งต่อ 30 วินาที

ละเมิดแล้วโดนแบน IP ชั่วคราว ทำซ้ำอาจถาวร

ตัวนี้บังคับหน่วงจริงด้วยการนอน ไม่ใช่แค่หวังว่าโค้ดจะเรียกช้าพอ
และเก็บสถานะลงดิสก์ เพื่อให้การรันครั้งใหม่ไม่ลืมว่าเพิ่งยิงไปเท่าไร
"""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from pathlib import Path

# ตั้งให้เข้มกว่าที่ประกาศไว้เล็กน้อย เผื่อความคลาดเคลื่อนของนาฬิกา
HOURLY_LIMIT = 55
GENERAL_INTERVAL = 2.2
PARSE_INTERVAL = 31.0
WINDOW_SEC = 3600.0


class RateLimiter:
    """บังคับทั้งเพดานรายชั่วโมงและระยะห่างขั้นต่ำระหว่างครั้ง"""

    def __init__(
        self,
        state_path: str | Path | None = None,
        hourly_limit: int = HOURLY_LIMIT,
        general_interval: float = GENERAL_INTERVAL,
        parse_interval: float = PARSE_INTERVAL,
        sleep=time.sleep,
        clock=time.monotonic,
    ):
        self.hourly_limit = hourly_limit
        self.general_interval = general_interval
        self.parse_interval = parse_interval
        self._sleep = sleep
        self._clock = clock
        self._lock = threading.Lock()
        self._hits: deque[float] = deque()
        self._last_general = float("-inf")
        self._last_parse = float("-inf")
        self._state_path = Path(state_path) if state_path else None
        self._load()

    # ------------------------------------------------------------------

    def acquire(self, kind: str = "general") -> float:
        """รอจนกว่าจะยิง request ได้ คืนจำนวนวินาทีที่รอไป"""
        with self._lock:
            waited = 0.0
            while True:
                now = self._clock()
                self._evict(now)

                need = 0.0
                if len(self._hits) >= self.hourly_limit:
                    need = max(need, self._hits[0] + WINDOW_SEC - now)
                need = max(need, self._last_general + self.general_interval - now)
                if kind == "parse":
                    need = max(need, self._last_parse + self.parse_interval - now)

                if need <= 0:
                    break
                self._sleep(need)
                waited += need

            now = self._clock()
            self._hits.append(now)
            self._last_general = now
            if kind == "parse":
                self._last_parse = now
            self._save()
            return waited

    # ------------------------------------------------------------------

    def _evict(self, now: float) -> None:
        while self._hits and now - self._hits[0] >= WINDOW_SEC:
            self._hits.popleft()

    @property
    def remaining_this_hour(self) -> int:
        with self._lock:
            self._evict(self._clock())
            return max(0, self.hourly_limit - len(self._hits))

    def estimate_seconds(self, n_requests: int, kind: str = "general") -> float:
        """ประมาณเวลาที่ต้องใช้ยิง n ครั้ง — ใช้เตือนก่อนเริ่ม crawl ยาว"""
        interval = self.parse_interval if kind == "parse" else self.general_interval
        by_interval = n_requests * interval
        full_hours = max(0, (n_requests - 1) // self.hourly_limit)
        return max(by_interval, full_hours * WINDOW_SEC)

    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._state_path or not self._state_path.exists():
            return
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        # เก็บเป็นเวลาจริง (wall clock) แต่ใช้ monotonic ตอนทำงาน
        # จึงแปลงกลับโดยอิงว่า "ผ่านมากี่วินาทีแล้ว"
        saved_at = raw.get("saved_at", 0.0)
        elapsed = max(0.0, time.time() - saved_at)
        if elapsed >= WINDOW_SEC:
            return
        base = self._clock() - elapsed
        self._hits = deque(
            base + (t - saved_at) for t in raw.get("hits", []) if time.time() - t < WINDOW_SEC
        )

    def _save(self) -> None:
        if not self._state_path:
            return
        now_mono = self._clock()
        now_wall = time.time()
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(
                json.dumps(
                    {
                        "saved_at": now_wall,
                        "hits": [now_wall - (now_mono - t) for t in self._hits],
                    }
                ),
                encoding="utf-8",
            )
        except OSError:
            pass  # การบันทึกสถานะล้มเหลวไม่ควรทำให้งานทั้งหมดพัง
