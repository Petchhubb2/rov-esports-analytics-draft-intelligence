"""ทดสอบ System 01 กับ PostgreSQL จริง

ต้องมี PostgreSQL รันอยู่ ถ้าไม่มีจะข้ามทั้งไฟล์
ตั้ง ROV_TEST_DATABASE_URL เพื่อชี้ไปฐานข้อมูลทดสอบแยก
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
from rov.domain.enums import JobStatus
from rov.ingest.probe import probe
from rov.ingest.service import IngestError, ingest_video, job_state, validate
from rov.store.db import create_all, drop_all, ping, session_scope
from rov.store.repo import JobRepo, MatchRepo, VideoRepo

TEST_URL = os.environ.get(
    "ROV_TEST_DATABASE_URL",
    "postgresql+psycopg://postgres@localhost:5432/rov_analytics_test",
)

pytestmark = pytest.mark.skipif(
    not ping(TEST_URL), reason="ไม่มี PostgreSQL สำหรับทดสอบ"
)


@pytest.fixture(scope="module")
def clean_db():
    drop_all(TEST_URL)
    create_all(TEST_URL)
    yield
    drop_all(TEST_URL)


@pytest.fixture(scope="module")
def video(tmp_path_factory) -> str:
    """สร้างคลิปทดสอบด้วย ffmpeg — ข้ามถ้าไม่มี ffmpeg"""
    import shutil

    if not shutil.which("ffmpeg"):
        pytest.skip("ไม่มี ffmpeg")
    out = tmp_path_factory.mktemp("vid") / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "testsrc2=size=1280x720:rate=30:duration=35",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            str(out),
        ],
        capture_output=True,
        check=True,
    )
    return str(out)


@pytest.fixture(scope="module")
def video_second(tmp_path_factory) -> str:
    """คลิปที่สองที่เนื้อหาต่างกัน จึงได้ sha256 คนละค่า"""
    import shutil

    if not shutil.which("ffmpeg"):
        pytest.skip("ไม่มี ffmpeg")
    out = tmp_path_factory.mktemp("vid2") / "clip2.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "smptebars=size=1280x720:rate=30:duration=33",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            str(out),
        ],
        capture_output=True,
        check=True,
    )
    return str(out)


# ---------------------------------------------------------------- validation


def test_rejects_unsupported_extension(tmp_path, video):
    from pathlib import Path

    meta = probe(video)
    with pytest.raises(IngestError, match="นามสกุลไฟล์"):
        validate(Path("x.avi"), meta)


def test_rejects_too_short_clip(video):
    from dataclasses import replace
    from pathlib import Path

    meta = probe(video)
    short = replace(meta, duration=5.0)
    with pytest.raises(IngestError, match="สั้นเกิน"):
        validate(Path("x.mp4"), short)


def test_rejects_too_small_resolution(video):
    from dataclasses import replace
    from pathlib import Path

    meta = probe(video)
    tiny = replace(meta, width=320)
    with pytest.raises(IngestError, match="ต่ำเกินไป"):
        validate(Path("x.mp4"), tiny)


def test_warns_on_sub_720p(video):
    from dataclasses import replace
    from pathlib import Path

    meta = probe(video)
    warns = validate(Path("x.mp4"), replace(meta, width=854, height=480))
    assert any("720p" in w for w in warns)


# ------------------------------------------------------------------- ingest


def test_ingest_creates_match_video_and_job(clean_db, video):
    """เกณฑ์ผ่านของ System 01 ตาม Blueprint §73"""
    with session_scope(TEST_URL) as s:
        r = ingest_video(s, video, title="เทสต์")

    assert r.match_id and r.video_id and r.job_id
    assert r.meta.width == 1280
    assert r.duplicate_of is None

    with session_scope(TEST_URL) as s:
        m = MatchRepo(s).get(r.match_id)
        assert m is not None and m.title == "เทสต์"

        vids = VideoRepo(s).by_match(r.match_id)
        assert len(vids) == 1
        assert vids[0].resolution == "1280x720"
        assert vids[0].sha256 is not None

        job = JobRepo(s).get(r.job_id)
        assert job is not None
        assert job.status == JobStatus.UPLOADED.value
        assert job.current_stage == "sample"
        assert job.progress == 0.0


def test_duplicate_file_is_flagged(clean_db, video):
    with session_scope(TEST_URL) as s:
        ingest_video(s, video, title="ครั้งแรก")
    with session_scope(TEST_URL) as s:
        second = ingest_video(s, video, title="ครั้งสอง")
    assert second.duplicate_of is not None
    assert any("เคยเข้าระบบแล้ว" in w for w in second.warnings)


def test_same_file_twice_in_one_match_is_rejected(clean_db, video):
    """ไฟล์เดิมในแมตช์เดิมเป็นความผิดพลาด ไม่ใช่แค่คำเตือน

    ต้องได้ข้อความที่อ่านรู้เรื่อง ไม่ใช่ IntegrityError ดิบจากฐานข้อมูล
    """
    with session_scope(TEST_URL) as s:
        first = ingest_video(s, video, title="แมตช์เดียว")
    with session_scope(TEST_URL) as s, pytest.raises(IngestError, match="อยู่แล้ว"):
        ingest_video(s, video, match_id=first.match_id)


def test_different_file_can_join_existing_match(clean_db, video, video_second):
    with session_scope(TEST_URL) as s:
        first = ingest_video(s, video, title="สองมุมกล้อง")
    with session_scope(TEST_URL) as s:
        second = ingest_video(s, video_second, match_id=first.match_id)
    assert second.match_id == first.match_id
    with session_scope(TEST_URL) as s:
        assert len(VideoRepo(s).by_match(first.match_id)) == 2


def test_unknown_match_id_is_rejected(clean_db, video):
    import uuid

    with session_scope(TEST_URL) as s, pytest.raises(IngestError, match="ไม่พบ match_id"):
        ingest_video(s, video, match_id=str(uuid.uuid4()))


# --------------------------------------------------------------------- job


def test_job_state_shape(clean_db, video):
    with session_scope(TEST_URL) as s:
        r = ingest_video(s, video)
    with session_scope(TEST_URL) as s:
        st = job_state(s, r.job_id)
    assert st["status"] == "UPLOADED"
    assert st["is_terminal"] is False
    assert st["stages"][0] == "sample"


def test_job_state_rejects_unknown_id(clean_db):
    with session_scope(TEST_URL) as s, pytest.raises(IngestError, match="ไม่พบ job"):
        job_state(s, "ไม่ใช่ uuid")


def test_claim_next_takes_oldest_job_first(clean_db, video):
    """คิวเป็น FIFO — งานที่เข้าคิวก่อนต้องถูกหยิบก่อน"""
    with session_scope(TEST_URL) as s:
        JobRepo(s).claim_next()  # เคลียร์งานค้างจากเทสต์ก่อนหน้า
    with session_scope(TEST_URL) as s:
        first = ingest_video(s, video, title="งานแรก")
    with session_scope(TEST_URL) as s:
        # ลบคิวเก่าทั้งหมดออกก่อน เพื่อให้เหลืองานที่เราสร้างเท่านั้น
        repo = JobRepo(s)
        while (j := repo.claim_next()) is not None and j.id != first.job_id:
            pass
    with session_scope(TEST_URL) as s:
        st = job_state(s, first.job_id)
    assert st["status"] == JobStatus.EXTRACTING.value


def test_claim_next_returns_none_when_queue_empty(clean_db):
    with session_scope(TEST_URL) as s:
        repo = JobRepo(s)
        while repo.claim_next() is not None:
            pass
        assert repo.claim_next() is None


def test_completed_job_is_terminal_with_full_progress(clean_db, video):
    with session_scope(TEST_URL) as s:
        r = ingest_video(s, video)
    with session_scope(TEST_URL) as s:
        repo = JobRepo(s)
        repo.update_status(repo.get(r.job_id), JobStatus.COMPLETED)
    with session_scope(TEST_URL) as s:
        st = job_state(s, r.job_id)
    assert st["is_terminal"] is True
    assert st["progress"] == 1.0


def test_failed_job_keeps_error_message(clean_db, video):
    with session_scope(TEST_URL) as s:
        r = ingest_video(s, video)
    with session_scope(TEST_URL) as s:
        repo = JobRepo(s)
        repo.update_status(repo.get(r.job_id), JobStatus.FAILED, error="detect พัง")
    with session_scope(TEST_URL) as s:
        st = job_state(s, r.job_id)
    assert st["status"] == "FAILED"
    assert st["error"] == "detect พัง"
    assert st["is_terminal"] is True


# --------------------------------------------------------------------- API


def test_api_endpoints(clean_db, video):
    sys.path.insert(0, ".")
    os.environ["ROV_DATABASE_URL"] = TEST_URL
    from fastapi.testclient import TestClient

    from apps.api.main import app

    c = TestClient(app)
    assert c.get("/health").json()["database"] is True

    r = c.post("/videos/register", data={"path": video, "title": "ผ่าน API"})
    assert r.status_code == 201
    body = r.json()

    assert c.get(f"/matches/{body['match_id']}").status_code == 200
    assert c.get(f"/jobs/{body['job_id']}").status_code == 200
    assert c.get("/matches/ไม่มีจริง").status_code == 404
    assert c.get("/jobs/ไม่มีจริง").status_code == 404
    assert c.post("/videos/register", data={"path": "ไม่มีไฟล์.mp4"}).status_code == 422
