"""FastAPI — ชั้นบางที่สุด

API ห้ามประมวลผลวิดีโอเอง (Blueprint §56)
หน้าที่คือรับไฟล์ สร้าง job รายงานสถานะ และอ่านผล
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from rov.ingest.service import IngestError, ingest_video, job_state
from rov.store.db import get_session, ping
from rov.store.repo import JobRepo, MatchRepo, VideoRepo
from sqlalchemy.orm import Session

from .schemas import (
    HealthOut,
    IngestOut,
    JobOut,
    MatchDetailOut,
    MatchOut,
    VideoOut,
)

app = FastAPI(
    title="RoV Analytics API",
    version="0.1.0",
    description="System 01 — Video Ingestion",
)

# ขนาดสูงสุดที่ยอมรับ กันไฟล์หลุดมาเต็มดิสก์
MAX_UPLOAD_BYTES = 8 * 1024**3  # 8 GB


def db() -> Iterator[Session]:
    yield from get_session()


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(status="ok", database=ping())


# ------------------------------------------------------------------ ingest


@app.post("/videos/upload", response_model=IngestOut, status_code=201)
async def upload_video(
    file: UploadFile = File(...),
    match_id: str | None = Form(None),
    title: str | None = Form(None),
    broadcast_profile_id: str | None = Form(None),
    session: Session = Depends(db),
) -> IngestOut:
    """อัปโหลดไฟล์วิดีโอ แล้วสร้าง Match, Video, ProcessingJob"""
    if not file.filename:
        raise HTTPException(400, "ไม่มีชื่อไฟล์")

    suffix = Path(file.filename).suffix or ".mp4"
    written = 0
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = Path(tmp.name)
            while chunk := await file.read(1 << 22):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        413, f"ไฟล์ใหญ่เกิน {MAX_UPLOAD_BYTES // 1024**3} GB"
                    )
                tmp.write(chunk)

        result = ingest_video(
            session,
            tmp_path,
            match_id=match_id,
            title=title or Path(file.filename).stem,
            broadcast_profile_id=broadcast_profile_id,
            copy_file=True,
        )
    except IngestError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    return IngestOut(
        match_id=result.match_id,
        video_id=result.video_id,
        job_id=result.job_id,
        width=result.meta.width,
        height=result.meta.height,
        fps=result.meta.fps,
        duration=result.meta.duration,
        codec=result.meta.codec,
        variable_fps=result.meta.variable_fps,
        warnings=result.warnings,
        duplicate_of=result.duplicate_of,
    )


@app.post("/videos/register", response_model=IngestOut, status_code=201)
def register_local_video(
    path: str = Form(...),
    match_id: str | None = Form(None),
    title: str | None = Form(None),
    session: Session = Depends(db),
) -> IngestOut:
    """รับไฟล์ที่อยู่บนเครื่องอยู่แล้ว โดยไม่ต้องอัปโหลดซ้ำ

    ใช้กับไฟล์ขนาดหลาย GB ที่การอัปโหลดผ่าน HTTP ไม่คุ้ม
    """
    try:
        result = ingest_video(session, path, match_id=match_id, title=title, copy_file=False)
    except IngestError as exc:
        raise HTTPException(422, str(exc)) from exc

    return IngestOut(
        match_id=result.match_id,
        video_id=result.video_id,
        job_id=result.job_id,
        width=result.meta.width,
        height=result.meta.height,
        fps=result.meta.fps,
        duration=result.meta.duration,
        codec=result.meta.codec,
        variable_fps=result.meta.variable_fps,
        warnings=result.warnings,
        duplicate_of=result.duplicate_of,
    )


# ------------------------------------------------------------------ read


@app.get("/matches", response_model=list[MatchOut])
def list_matches(
    limit: int = 50, offset: int = 0, session: Session = Depends(db)
) -> list[MatchOut]:
    limit = max(1, min(limit, 200))
    return [MatchOut.model_validate(m) for m in MatchRepo(session).list(limit, offset)]


@app.get("/matches/{match_id}", response_model=MatchDetailOut)
def get_match(match_id: str, session: Session = Depends(db)) -> MatchDetailOut:
    match = MatchRepo(session).get(match_id)
    if match is None:
        raise HTTPException(404, f"ไม่พบ match: {match_id}")
    return MatchDetailOut(
        **MatchOut.model_validate(match).model_dump(),
        videos=[VideoOut.model_validate(v) for v in VideoRepo(session).by_match(match_id)],
        jobs=[JobOut.model_validate(j) for j in JobRepo(session).by_match(match_id)],
    )


@app.get("/jobs/{job_id}", response_model=dict)
def get_job(job_id: str, session: Session = Depends(db)) -> dict:
    """สถานะของ job — frontend polling ทุก 2 วินาที"""
    try:
        return job_state(session, job_id)
    except IngestError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/matches/{match_id}/processing", response_model=list[JobOut])
def match_processing(match_id: str, session: Session = Depends(db)) -> list[JobOut]:
    if MatchRepo(session).get(match_id) is None:
        raise HTTPException(404, f"ไม่พบ match: {match_id}")
    return [JobOut.model_validate(j) for j in JobRepo(session).by_match(match_id)]
