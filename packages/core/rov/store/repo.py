"""Repository — ห่อการเข้าถึงฐานข้อมูลไว้ชั้นเดียว

service เรียก repository ไม่เรียก session ตรง ๆ
ทำให้เปลี่ยนวิธีเก็บข้อมูลได้โดยไม่กระทบตรรกะทางธุรกิจ
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from rov.domain.enums import JobStatus
from rov.store.models import BroadcastProfile, Match, ProcessingJob, Video


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return True


class MatchRepo:
    def __init__(self, session: Session):
        self.s = session

    def create(self, **kw) -> Match:
        m = Match(**kw)
        self.s.add(m)
        self.s.flush()
        return m

    def get(self, match_id: str) -> Match | None:
        return self.s.get(Match, match_id)

    def list(self, limit: int = 50, offset: int = 0) -> list[Match]:
        stmt = (
            select(Match)
            .order_by(Match.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.s.scalars(stmt))

    def count(self) -> int:
        from sqlalchemy import func

        return int(self.s.scalar(select(func.count()).select_from(Match)) or 0)


class VideoRepo:
    def __init__(self, session: Session):
        self.s = session

    def create(self, **kw) -> Video:
        v = Video(**kw)
        self.s.add(v)
        self.s.flush()
        return v

    def get(self, video_id: str) -> Video | None:
        return self.s.get(Video, video_id)

    def by_match(self, match_id: str) -> list[Video]:
        return list(self.s.scalars(select(Video).where(Video.match_id == match_id)))

    def find_by_hash(self, sha256: str) -> Video | None:
        """หาไฟล์ที่เคยอัปโหลดแล้ว ป้องกันการประมวลผลซ้ำโดยไม่ตั้งใจ"""
        return self.s.scalars(select(Video).where(Video.sha256 == sha256)).first()


class JobRepo:
    def __init__(self, session: Session):
        self.s = session

    def create(
        self,
        match_id: str,
        video_id: str,
        stages: list[str],
        code_version: str | None = None,
        config_hash: str | None = None,
    ) -> ProcessingJob:
        j = ProcessingJob(
            match_id=match_id,
            video_id=video_id,
            stages=stages,
            status=JobStatus.UPLOADED.value,
            code_version=code_version,
            config_hash=config_hash,
        )
        self.s.add(j)
        self.s.flush()
        return j

    def get(self, job_id: str) -> ProcessingJob | None:
        """คืน None เมื่อไม่พบ หรือเมื่อรูปแบบ id ไม่ใช่ UUID

        ต้องตรวจรูปแบบก่อน เพราะคอลัมน์เป็นชนิด UUID ของ PostgreSQL
        การส่งสตริงที่ไม่ใช่ UUID เข้าไปจะทำให้เกิด DataError
        แล้ว API ตอบ 500 แทนที่จะเป็น 404
        """
        if not _is_uuid(job_id):
            return None
        return self.s.get(ProcessingJob, job_id)

    def by_match(self, match_id: str) -> list[ProcessingJob]:
        stmt = (
            select(ProcessingJob)
            .where(ProcessingJob.match_id == match_id)
            .order_by(ProcessingJob.created_at.desc())
        )
        return list(self.s.scalars(stmt))

    def claim_next(self) -> ProcessingJob | None:
        """หยิบงานถัดไปมาทำ พร้อมล็อกกันสอง worker แย่งกัน

        SKIP LOCKED ทำให้ worker ตัวอื่นข้ามแถวที่ถูกล็อกไปแทนที่จะรอ
        """
        stmt = (
            select(ProcessingJob)
            .where(ProcessingJob.status.in_([JobStatus.UPLOADED.value, JobStatus.QUEUED.value]))
            .order_by(ProcessingJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = self.s.scalars(stmt).first()
        if job is not None:
            job.status = JobStatus.EXTRACTING.value
            job.started_at = datetime.now(UTC)
            self.s.flush()
        return job

    def update_status(
        self,
        job: ProcessingJob,
        status: JobStatus,
        progress: float | None = None,
        error: str | None = None,
    ) -> ProcessingJob:
        job.status = status.value
        if progress is not None:
            job.progress = max(0.0, min(1.0, progress))
        if error is not None:
            job.error = error
        if status.is_terminal:
            job.finished_at = datetime.now(UTC)
            if status is JobStatus.COMPLETED:
                job.progress = 1.0
        self.s.flush()
        return job


class BroadcastProfileRepo:
    def __init__(self, session: Session):
        self.s = session

    def upsert_from_layout(self, layout, config_path: str, config_hash: str) -> BroadcastProfile:
        existing = self.s.get(BroadcastProfile, layout.id)
        w, h = layout.source_resolution
        if existing is None:
            existing = BroadcastProfile(id=layout.id)
            self.s.add(existing)
        existing.source_width = w
        existing.source_height = h
        existing.config_path = config_path
        existing.config_hash = config_hash
        existing.fog_of_war = layout.minimap.fog_of_war
        self.s.flush()
        return existing

    def get(self, profile_id: str) -> BroadcastProfile | None:
        return self.s.get(BroadcastProfile, profile_id)
