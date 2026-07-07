"""CodeMaker Coach API — FastAPI 진입점.

라우터(problems, submissions, hints, community, auth)는 이후 브랜치에서 추가된다.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from app.gateway import StubAgentGateway, get_agent_gateway
from app.routers import problems_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="CodeMaker Coach API", version="0.1.0")
app.include_router(problems_router)


@app.get("/health")
def health() -> dict:
    """헬스체크 + 현재 AI 게이트웨이 모드 표시."""
    gateway = get_agent_gateway()
    mode = "stub" if isinstance(gateway, StubAgentGateway) else "live"
    return {"status": "ok", "agent_mode": mode}
