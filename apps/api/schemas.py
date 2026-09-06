"""Pydantic schema สำหรับ request/response ของ API

แยกจาก SQLAlchemy model โดยเจตนา เพื่อไม่ให้การเปลี่ยนสคีมาฐานข้อมูล
รั่วออกไปเป็น breaking change ของ API
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthOut(BaseModel):
    status: str
    database: bool


class IngestOut(BaseModel):
    match_id: str
    video_id: str
    job_id: str
    width: int
    height: int
    fps: float
    duration: float
    codec: str | None = None
    variable_fps: bool = False
    warnings: list[str] = Field(default_factory=list)
    duplicate_of: str | None = None


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None = None
    tournament_id: str | None = None
    series_id: str | None = None
    game_index: int | None = None
    blue_team_id: str | None = None
    red_team_id: str | None = None
    winner_team_id: str | None = None
    broadcast_profile_id: str | None = None
    created_at: datetime | None = None


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    match_id: str
    original_name: str | None = None
    width: int
    height: int
    fps: float
    duration: float
    codec: str | None = None
    variable_fps: bool
    size_bytes: int | None = None
    created_at: datetime | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    match_id: str
    video_id: str
    status: str
    stages: list[str]
    stage_index: int
    progress: float
    error: str | None = None
    code_version: str | None = None
    created_at: datetime | None = None
    finished_at: datetime | None = None


class MatchDetailOut(MatchOut):
    videos: list[VideoOut] = Field(default_factory=list)
    jobs: list[JobOut] = Field(default_factory=list)
