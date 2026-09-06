"""การเชื่อมต่อฐานข้อมูลและ session

DATABASE_URL อ่านจาก environment เสมอ ไม่ hardcode
ค่าเริ่มต้นชี้ไปที่ PostgreSQL บนเครื่อง
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_URL = "postgresql+psycopg://postgres@localhost:5432/rov_analytics"


def database_url() -> str:
    return os.environ.get("ROV_DATABASE_URL", DEFAULT_URL)


@lru_cache(maxsize=4)
def get_engine(url: str | None = None) -> Engine:
    return create_engine(
        url or database_url(),
        pool_pre_ping=True,  # กัน connection ที่ตายไปแล้วหลังเครื่องหลับ
        future=True,
    )


@lru_cache(maxsize=4)
def _session_factory(url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(url), expire_on_commit=False, future=True)


@contextmanager
def session_scope(url: str | None = None) -> Iterator[Session]:
    """session ที่ commit เมื่อสำเร็จ และ rollback เมื่อมี exception"""
    s = _session_factory(url)()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_session(url: str | None = None) -> Iterator[Session]:
    """dependency ของ FastAPI"""
    with session_scope(url) as s:
        yield s


def ping(url: str | None = None) -> bool:
    """ตรวจว่าต่อฐานข้อมูลได้จริงหรือไม่"""
    try:
        with get_engine(url).connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def create_all(url: str | None = None) -> None:
    """สร้างตารางทั้งหมด — ใช้ตอน dev และในเทสต์เท่านั้น

    บน production ให้ใช้ alembic เพื่อให้ migration ตรวจสอบย้อนหลังได้
    """
    from rov.store.models import Base

    Base.metadata.create_all(get_engine(url))


def drop_all(url: str | None = None) -> None:
    from rov.store.models import Base

    Base.metadata.drop_all(get_engine(url))
