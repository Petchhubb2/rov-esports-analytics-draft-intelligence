"""System 01 — Video Ingestion

ขอบเขต (Blueprint §7, §73):
    รับไฟล์ MP4 -> อ่าน metadata -> สร้าง Match, Video, ProcessingJob -> คืน id

สิ่งที่ระบบนี้ไม่ทำ: minimap detection, tracking, macro, draft
ตามกฎ "Do not implement future systems"
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from rov.domain.enums import JobStatus
from rov.ingest.probe import VideoMeta, probe
from rov.store.repo import JobRepo, MatchRepo, VideoRepo

# ลำดับ stage ของ pipeline — job เดินตามรายการนี้ทีละขั้น
DEFAULT_STAGES = ["sample", "background", "detect", "hud", "track", "zones", "events"]

# ข้อจำกัดของ input ที่ยอมรับ
MIN_DURATION_SEC = 30.0
MIN_WIDTH = 640
ALLOWED_SUFFIXES = {".mp4", ".mkv", ".mov", ".m4v"}


class IngestError(ValueError):
    """input ไม่ผ่านการตรวจ — ไม่ใช่ข้อผิดพลาดของระบบ"""


@dataclass(slots=True)
class IngestResult:
    match_id: str
    video_id: str
    job_id: str
    meta: VideoMeta
    warnings: list[str]
    duplicate_of: str | None = None


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def validate(path: Path, meta: VideoMeta) -> list[str]:
    """ตรวจ input แล้วคืนรายการคำเตือน — โยน IngestError ถ้ารับไม่ได้เลย"""
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise IngestError(
            f"นามสกุลไฟล์ {path.suffix} ไม่รองรับ — ต้องเป็นหนึ่งใน "
            f"{sorted(ALLOWED_SUFFIXES)}"
        )
    if meta.width < MIN_WIDTH:
        raise IngestError(
            f"ความกว้าง {meta.width} ต่ำเกินไป — minimap จะเล็กจนตรวจ icon ไม่ได้ "
            f"(ต้องอย่างน้อย {MIN_WIDTH})"
        )
    if meta.duration < MIN_DURATION_SEC:
        raise IngestError(
            f"คลิปยาว {meta.duration:.1f} วินาที สั้นเกินกว่าจะเป็นเกมแข่ง "
            f"(ต้องอย่างน้อย {MIN_DURATION_SEC:.0f})"
        )

    warnings: list[str] = []
    if meta.variable_fps:
        warnings.append(
            "คลิปเป็น variable frame rate — ระบบใช้ PTS อยู่แล้วจึงยังทำงานได้ "
            "แต่ห้ามคำนวณเวลาจาก frame index ที่ใดก็ตาม"
        )
    if meta.width < 1280:
        warnings.append(
            f"ความละเอียด {meta.width}x{meta.height} ต่ำกว่า 720p — "
            "hero icon จะเล็กกว่าที่ threshold ตั้งไว้ ต้องปรับ layout config"
        )
    if meta.duration > 3600:
        warnings.append(
            f"คลิปยาว {meta.duration / 60:.0f} นาที — น่าจะมีหลายเกมในไฟล์เดียว "
            "ต้องแบ่ง game_id ก่อนวิเคราะห์"
        )
    if meta.fps < 20:
        warnings.append(f"เฟรมเรต {meta.fps:.1f} ต่ำ — การติดตามอาจขาดช่วง")
    return warnings


def ingest_video(
    session: Session,
    source: str | Path,
    *,
    match_id: str | None = None,
    title: str | None = None,
    broadcast_profile_id: str | None = None,
    store_dir: str | Path = "data/videos",
    copy_file: bool = False,
    stages: list[str] | None = None,
    code_version: str | None = None,
) -> IngestResult:
    """รับไฟล์วิดีโอเข้าระบบ

    copy_file=True  จะคัดลอกไฟล์เข้า store_dir (ใช้กับการอัปโหลดผ่าน API)
    copy_file=False จะอ้างถึงไฟล์เดิมที่อยู่ในเครื่อง (ใช้กับ CLI)
    """
    src = Path(source)
    if not src.exists():
        raise IngestError(f"ไม่พบไฟล์: {src}")

    meta = probe(src)
    warnings = validate(src, meta)
    digest = sha256_file(src)

    videos = VideoRepo(session)
    duplicate = videos.find_by_hash(digest)
    if duplicate is not None:
        warnings.append(
            f"ไฟล์นี้เคยเข้าระบบแล้วในชื่อ video_id={duplicate.id} "
            f"(match_id={duplicate.match_id}) — กำลังสร้างรายการใหม่ซ้ำ"
        )

    matches = MatchRepo(session)
    if match_id:
        match = matches.get(match_id)
        if match is None:
            raise IngestError(f"ไม่พบ match_id ที่ระบุ: {match_id}")
        # ไฟล์เดียวกันในแมตช์เดียวกันเป็นความผิดพลาดแน่นอน ไม่ใช่แค่คำเตือน
        # ดักที่นี่เพื่อให้ได้ข้อความที่อ่านรู้เรื่อง แทน IntegrityError จากฐานข้อมูล
        if any(v.sha256 == digest for v in videos.by_match(match_id)):
            raise IngestError(
                f"ไฟล์นี้อยู่ในแมตช์ {match_id} อยู่แล้ว "
                "ถ้าต้องการประมวลผลซ้ำให้ลบวิดีโอเดิมก่อน"
            )
    else:
        match = matches.create(
            title=title or src.stem,
            broadcast_profile_id=broadcast_profile_id,
        )

    final_path = src
    if copy_file:
        dest_dir = Path(store_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        final_path = dest_dir / f"{digest[:16]}{src.suffix.lower()}"
        if not final_path.exists():
            shutil.copy2(src, final_path)

    video = videos.create(
        match_id=match.id,
        path=str(final_path.resolve()),
        original_name=src.name,
        sha256=digest,
        size_bytes=src.stat().st_size,
        width=meta.width,
        height=meta.height,
        fps=meta.fps,
        duration=meta.duration,
        n_frames_est=meta.n_frames_est,
        codec=meta.codec,
        pix_fmt=meta.pix_fmt,
        time_base=meta.time_base,
        variable_fps=meta.variable_fps,
    )

    job = JobRepo(session).create(
        match_id=match.id,
        video_id=video.id,
        stages=stages or list(DEFAULT_STAGES),
        code_version=code_version,
    )

    return IngestResult(
        match_id=match.id,
        video_id=video.id,
        job_id=job.id,
        meta=meta,
        warnings=warnings,
        duplicate_of=duplicate.id if duplicate else None,
    )


def job_state(session: Session, job_id: str) -> dict:
    """สถานะของ job สำหรับให้ frontend polling"""
    job = JobRepo(session).get(job_id)
    if job is None:
        raise IngestError(f"ไม่พบ job: {job_id}")
    return {
        "job_id": job.id,
        "match_id": job.match_id,
        "video_id": job.video_id,
        "status": job.status,
        "stage": job.current_stage,
        "stage_index": job.stage_index,
        "stages": list(job.stages),
        "progress": job.progress,
        "error": job.error,
        "is_terminal": JobStatus(job.status).is_terminal,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }
