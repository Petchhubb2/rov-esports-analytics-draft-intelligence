"""SQLAlchemy models

ขอบเขตตอนนี้: เฉพาะตารางที่ System 01 (Video Ingestion) ต้องใช้
ตารางที่เหลือใน Blueprint §55 จะเพิ่มเมื่อถึงระบบที่ใช้จริง
ตามกฎ "Do not implement future systems"

ใช้ PostgreSQL เป็นหลัก ชนิดข้อมูลจึงใช้ JSONB และ ARRAY ตรง ๆ
ไม่ทำ abstraction ให้รองรับ SQLite เพราะจะทำให้เกิดความต่างระหว่าง
dev กับ prod ที่หา bug ยาก
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


# --------------------------------------------------------------- reference


class Patch(Base):
    __tablename__ = "patches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(Date)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    tag: Mapped[str | None] = mapped_column(String(16))


class BroadcastProfile(Base):
    """ผูก layout config เข้ากับฐานข้อมูล — Blueprint §8, §55

    ตัวไฟล์ YAML ยังเป็นแหล่งความจริง ตารางนี้เก็บไว้อ้างอิงว่า
    match ไหนถูกประมวลผลด้วย layout เวอร์ชันใด
    """

    __tablename__ = "broadcast_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_width: Mapped[int] = mapped_column(Integer, nullable=False)
    source_height: Mapped[int] = mapped_column(Integer, nullable=False)
    config_path: Mapped[str] = mapped_column(Text, nullable=False)
    config_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    fog_of_war: Mapped[bool | None] = mapped_column()
    verified_on: Mapped[datetime | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ------------------------------------------------------------------- match


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    tournament_id: Mapped[str | None] = mapped_column(String(64))
    series_id: Mapped[str | None] = mapped_column(String(64))
    game_index: Mapped[int | None] = mapped_column(Integer)
    patch_id: Mapped[int | None] = mapped_column(ForeignKey("patches.id"))
    played_at: Mapped[datetime | None] = mapped_column(Date)
    blue_team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"))
    red_team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"))
    winner_team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"))
    broadcast_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("broadcast_profiles.id")
    )
    title: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    videos: Mapped[list[Video]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )
    jobs: Mapped[list[ProcessingJob]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )


class Video(Base):
    """ไฟล์วิดีโอหนึ่งไฟล์ — หนึ่ง match อาจมีหลายไฟล์ (มุมกล้อง/คุณภาพต่างกัน)"""

    __tablename__ = "videos"
    __table_args__ = (
        UniqueConstraint("match_id", "sha256", name="uq_video_match_hash"),
        CheckConstraint("width > 0 AND height > 0", name="ck_video_dimensions"),
        CheckConstraint("fps > 0", name="ck_video_fps"),
        CheckConstraint("duration >= 0", name="ck_video_duration"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    match_id: Mapped[str] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    original_name: Mapped[str | None] = mapped_column(Text)
    sha256: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(Integer)

    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    fps: Mapped[float] = mapped_column(Float, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    n_frames_est: Mapped[int | None] = mapped_column(Integer)
    codec: Mapped[str | None] = mapped_column(String(32))
    pix_fmt: Mapped[str | None] = mapped_column(String(32))
    time_base: Mapped[str | None] = mapped_column(String(32))
    # ต้องรู้ เพราะการคำนวณเวลาจาก frame_index จะผิดถ้าเป็น VFR
    variable_fps: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    match: Mapped[Match] = relationship(back_populates="videos")

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"


class ProcessingJob(Base):
    """งานประมวลผลแบบ asynchronous — Blueprint §56

    เก็บรายการ stage ไว้ทั้งหมด แล้วเดินทีละขั้น ทำให้ resume จากจุดที่พังได้
    ไม่ใช้ Celery/Redis ในตอนนี้ ตาราง + worker หนึ่งตัวพอสำหรับเครื่องเดียว
    """

    __tablename__ = "video_processing_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('UPLOADED','QUEUED','EXTRACTING','DETECTING','TRACKING',"
            "'ANALYZING','COMPLETED','FAILED')",
            name="ck_job_status",
        ),
        CheckConstraint("progress >= 0 AND progress <= 1", name="ck_job_progress"),
        Index("ix_job_status_created", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    match_id: Mapped[str] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    video_id: Mapped[str] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="UPLOADED")
    stages: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    stage_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error: Mapped[str | None] = mapped_column(Text)

    # ตามกฎข้อ 10-11 ของ Blueprint §70 — ทุก analysis ต้องรู้ว่าใช้เวอร์ชันใด
    code_version: Mapped[str | None] = mapped_column(String(32))
    config_hash: Mapped[str | None] = mapped_column(String(32))
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    match: Mapped[Match] = relationship(back_populates="jobs")

    @property
    def current_stage(self) -> str | None:
        if 0 <= self.stage_index < len(self.stages):
            return self.stages[self.stage_index]
        return None
