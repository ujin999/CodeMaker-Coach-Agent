"""CodeMaker Coach API — FastAPI 진입점."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.gateway import StubAgentGateway, get_agent_gateway
from app.routers.auth import router as auth_router
from app.routers.problems import router as problems_router
from app.routers.submissions import router as submissions_router
from app.routers.hints import router as hints_router
from app.routers.community import router as community_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="CodeMaker Coach API",
    version="0.2.0",
    description="LLM 기반 코딩테스트 문제 생성·채점·힌트 학습 플랫폼 API",
)

# CORS — 개발용 (운영에서는 실제 도메인으로 교체)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth_router)
app.include_router(problems_router)
app.include_router(submissions_router)
app.include_router(hints_router)
app.include_router(community_router)


@app.get("/health", tags=["health"])
def health() -> dict:
    """헬스체크 + 현재 AI 게이트웨이 모드 표시."""
    gateway = get_agent_gateway()
    mode = "stub" if isinstance(gateway, StubAgentGateway) else "live"
    return {"status": "ok", "agent_mode": mode}
