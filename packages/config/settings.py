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
    embedding_model: str = "text-embedding-3-small"

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
    api_port: int = 10000
    # 채점 큐: MVP는 인메모리. 확장 시 redis 로 전환. (ARCHITECTURE 2.6)
    queue_backend: Literal["memory", "redis"] = "memory"
    redis_url: str = Field(default="redis://localhost:6379/0")
    # 프론트엔드 배포 주소를 콤마로 구분해 등록한다 (CORS 허용 origin).
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:10001,http://127.0.0.1:10001"

    # ── 문제 신고 / HITL (FR-34) ───────────────────
    # 누적 신고 수가 이 값 이상이면 문제가 under_review 상태가 되어 공개 카탈로그에서
    # 숨겨지고, 관리자(is_admin)의 검토(기각/삭제/수정)를 기다린다.
    problem_report_threshold: int = 5


@lru_cache
def get_settings() -> Settings:
    """설정 싱글턴. 프로세스 내 1회 로드."""
    return Settings()


settings = get_settings()
