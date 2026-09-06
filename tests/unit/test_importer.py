"""ทดสอบ rate limiter และ cache ของ Liquipedia importer

ตัวจำกัดอัตราคือส่วนที่ห้ามผิด เพราะการยิงเกินโควตาทำให้โดนแบน IP
จึงทดสอบด้วยนาฬิกาปลอม ไม่ใช่การนอนจริง
"""

from __future__ import annotations

import json

import pytest
from rov.draft.importer.cache import ResponseCache
from rov.draft.importer.ratelimit import WINDOW_SEC, RateLimiter


class FakeClock:
    """นาฬิกาปลอมที่เดินเฉพาะเมื่อถูกสั่งให้นอน"""

    def __init__(self) -> None:
        self.t = 0.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.t

    def sleep(self, sec: float) -> None:
        self.slept.append(sec)
        self.t += sec

    def advance(self, sec: float) -> None:
        self.t += sec


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def make_limiter(clock: FakeClock, **kw) -> RateLimiter:
    return RateLimiter(sleep=clock.sleep, clock=clock, **kw)


# ------------------------------------------------------------- ระยะห่างขั้นต่ำ


def test_first_request_does_not_wait(clock):
    lim = make_limiter(clock)
    assert lim.acquire() == 0.0


def test_second_request_waits_general_interval(clock):
    lim = make_limiter(clock, general_interval=2.2)
    lim.acquire()
    waited = lim.acquire()
    assert waited == pytest.approx(2.2), "ต้องหน่วงอย่างน้อย 2 วินาทีระหว่างครั้ง"


def test_no_wait_if_enough_time_already_passed(clock):
    lim = make_limiter(clock, general_interval=2.2)
    lim.acquire()
    clock.advance(5.0)
    assert lim.acquire() == 0.0


def test_parse_requests_use_longer_interval(clock):
    lim = make_limiter(clock, general_interval=2.2, parse_interval=31.0)
    lim.acquire("parse")
    waited = lim.acquire("parse")
    assert waited == pytest.approx(31.0), "action=parse ถูกจำกัด 1 ครั้งต่อ 30 วินาที"


def test_general_request_after_parse_only_waits_general(clock):
    lim = make_limiter(clock, general_interval=2.2, parse_interval=31.0)
    lim.acquire("parse")
    assert lim.acquire("general") == pytest.approx(2.2)


# ------------------------------------------------------------- เพดานรายชั่วโมง


def test_hourly_cap_is_enforced(clock):
    lim = make_limiter(clock, hourly_limit=5, general_interval=0.0)
    for _ in range(5):
        lim.acquire()
    assert lim.remaining_this_hour == 0

    waited = lim.acquire()
    assert waited > 0, "ครั้งที่เกินเพดานต้องถูกบังคับให้รอ"
    assert waited == pytest.approx(WINDOW_SEC, abs=1.0)


def test_quota_frees_up_after_the_window(clock):
    lim = make_limiter(clock, hourly_limit=3, general_interval=0.0)
    for _ in range(3):
        lim.acquire()
    assert lim.remaining_this_hour == 0

    clock.advance(WINDOW_SEC + 1)
    assert lim.remaining_this_hour == 3
    assert lim.acquire() == 0.0


def test_never_exceeds_cap_over_a_long_run(clock):
    """ยิงรัวหลายครั้ง แล้วตรวจว่าในทุกหน้าต่างหนึ่งชั่วโมงไม่เกินเพดาน"""
    lim = make_limiter(clock, hourly_limit=10, general_interval=1.0)
    times: list[float] = []
    for _ in range(35):
        lim.acquire()
        times.append(clock.t)

    for i, t in enumerate(times):
        in_window = sum(1 for u in times[: i + 1] if t - u < WINDOW_SEC)
        assert in_window <= 10, f"ครั้งที่ {i} มี {in_window} ครั้งในหน้าต่างเดียว"


# ------------------------------------------------------------------ ประมาณเวลา


def test_estimate_warns_about_long_crawls(clock):
    lim = make_limiter(clock, hourly_limit=55, general_interval=2.2)
    # 500 แมตช์ ต้องใช้เวลาหลายชั่วโมง ไม่ใช่หลักนาที
    est = lim.estimate_seconds(500)
    assert est > 8 * 3600, "การดึง 500 หน้าต้องประเมินว่าใช้เวลาหลายชั่วโมง"


def test_estimate_of_small_batch_is_interval_bound(clock):
    lim = make_limiter(clock, hourly_limit=55, general_interval=2.0)
    assert lim.estimate_seconds(10) == pytest.approx(20.0)


# ------------------------------------------------------------- บันทึกสถานะ


def test_state_survives_restart(tmp_path, clock):
    """รันใหม่แล้วต้องจำได้ว่าเพิ่งยิงไปเท่าไร ไม่ใช่เริ่มนับศูนย์"""
    state = tmp_path / "rl.json"
    lim = make_limiter(clock, state_path=state, hourly_limit=5, general_interval=0.0)
    for _ in range(5):
        lim.acquire()
    assert state.exists()

    clock2 = FakeClock()
    lim2 = RateLimiter(
        state_path=state, hourly_limit=5, general_interval=0.0,
        sleep=clock2.sleep, clock=clock2,
    )
    assert lim2.remaining_this_hour == 0, "โควตาที่ใช้ไปแล้วต้องไม่ถูกลืมหลังรีสตาร์ต"


def test_corrupt_state_file_does_not_crash(tmp_path, clock):
    state = tmp_path / "rl.json"
    state.write_text("ไม่ใช่ json", encoding="utf-8")
    lim = make_limiter(clock, state_path=state, hourly_limit=5)
    assert lim.remaining_this_hour == 5


# ------------------------------------------------------------------- cache


def test_cache_round_trip(tmp_path):
    c = ResponseCache(tmp_path)
    params = {"action": "query", "titles": "หน้าทดสอบ"}
    assert c.get("http://x", params) is None

    c.put("http://x", params, '{"ok": true}')
    entry = c.get("http://x", params)
    assert entry is not None
    assert json.loads(entry.body)["ok"] is True


def test_cache_key_depends_on_params(tmp_path):
    c = ResponseCache(tmp_path)
    c.put("http://x", {"a": 1}, "หนึ่ง")
    assert c.get("http://x", {"a": 2}) is None
    assert c.get("http://x", {"a": 1}).body == "หนึ่ง"


def test_cache_key_ignores_param_order(tmp_path):
    c = ResponseCache(tmp_path)
    c.put("http://x", {"a": 1, "b": 2}, "เนื้อหา")
    assert c.get("http://x", {"b": 2, "a": 1}) is not None


def test_cache_respects_max_age(tmp_path):
    c = ResponseCache(tmp_path)
    c.put("http://x", {"a": 1}, "เก่า")
    assert c.get("http://x", {"a": 1}, max_age_sec=0.0) is None
    assert c.get("http://x", {"a": 1}, max_age_sec=9999) is not None


def test_cache_stats(tmp_path):
    c = ResponseCache(tmp_path)
    c.put("http://x", {"a": 1}, "x" * 100)
    c.put("http://x", {"a": 2}, "y" * 100)
    st = c.stats()
    assert st["entries"] == 2
    assert st["bytes"] > 0
