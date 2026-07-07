"""공용 설정 로더.

.env 값을 읽어 타입 검증된 Settings 객체로 노출한다.
packages/*, apps/* 어디서든 `from config.settings import settings`로 사용한다.
시크릿은 코드에 하드코딩하지 않는다. (NFR-3)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM Provider ──────────────────────────────
    llm_provider: Literal["claude", "openai"] = "claude"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # ── Embeddings / Vector Store (RAG) ───────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    embedding_model: str = ""

    # ── Database ──────────────────────────────────
    database_url: str = "postgresql://postgres:postgres@localhost:5432/codemaker"

    # ── 인증 (JWT) ────────────────────────────────
    # 시크릿은 반드시 .env로 설정한다. 코드에 기본값을 두지 않는다 (NFR-3).
    jwt_secret_key: str = ""
    jwt_expire_minutes: int = 60

    # ── Judge0 (채점) ─────────────────────────────
    judge0_url: str = "http://localhost:2358"
    judge0_auth_token: str = ""

    # ── Graph RAG (Neo4j, 확장) ───────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # ── App ───────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # 채점 큐: MVP는 인메모리. 확장 시 redis 로 전환. (ARCHITECTURE 2.6)
    queue_backend: Literal["memory", "redis"] = "memory"
    redis_url: str = Field(default="redis://localhost:6379/0")


@lru_cache
def get_settings() -> Settings:
    """설정 싱글턴. 프로세스 내 1회 로드."""
    return Settings()


settings = get_settings()
