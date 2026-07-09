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
from config.settings import settings

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="CodeMaker Coach API",
    version="0.2.0",
    description="LLM 기반 코딩테스트 문제 생성·채점·힌트 학습 플랫폼 API",
)

# CORS — 허용 origin은 .env의 CORS_ORIGINS(콤마 구분)로 배포 환경마다 설정한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
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


@app.on_event("startup")
async def start_sweeper_agent():
    import asyncio
    from app.db import SessionLocal
    from agent.services.sweeper_service import run_sweeper_cycle

    async def sweeper_scheduler_loop():
        # 최초 기동 후 10초 대기하여 인프라 준비 완료 보증
        await asyncio.sleep(10)
        logger = logging.getLogger("app.main")
        logger.info("Background Problem Sweeper Agent scheduler initiated.")
        while True:
            try:
                db = SessionLocal()
                # 백그라운드 비동기 루프로 정화 실행
                await run_sweeper_cycle(db)
            except Exception as e:
                logger.exception(f"Error occurred in background sweeper cycle: {e}")
            finally:
                db.close()
            # 1시간 주기로 반복 실행
            await asyncio.sleep(3600)

    asyncio.create_task(sweeper_scheduler_loop())
