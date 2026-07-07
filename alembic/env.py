"""Alembic env.py — CodeMaker Coach Agent.

- SQLAlchemy Base 메타데이터를 읽어 autogenerate한다.
- DATABASE_URL은 config.settings에서 읽는다 (환경변수 기반).
"""

from __future__ import annotations

import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ── 패키지 경로 추가 ────────────────────────────────────────────────────────
# alembic은 프로젝트 루트에서 실행되므로 아래 경로를 추가해야 모델을 임포트할 수 있다.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "packages"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

# ── 모델 & Base 임포트 ──────────────────────────────────────────────────────
from app.db import Base  # noqa: E402
import app.models  # noqa: E402 — 모든 모델을 Base에 등록시킴

# ── DATABASE_URL ────────────────────────────────────────────────────────────
from config.settings import settings  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# autogenerate가 인식할 메타데이터
target_metadata = Base.metadata


def get_url() -> str:
    return settings.database_url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
