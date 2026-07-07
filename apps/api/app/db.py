"""DB 계층 — 동기 SQLAlchemy 2.0.

- Base: 모든 모델의 선언적 베이스
- engine / SessionLocal: settings.database_url 기반 (서버 postgres)
- get_db: FastAPI 의존성 (요청당 세션)
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import settings


class Base(DeclarativeBase):
    """모든 ORM 모델의 베이스."""


engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
