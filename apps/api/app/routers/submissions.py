"""Submissions 라우터 — 제출 → 인메모리 큐 → Judge0 채점 (FR-11~FR-14, ARCHITECTURE 2.6).

채점은 비동기(BackgroundTasks)로 처리하며, 클라이언트는 GET /submissions/{id}로 폴링한다.
큐 인터페이스는 추상화되어 있어 Redis+Celery 전환 시 routers 변경 없음.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.db import get_db
from app.models.problem import Problem, TestCase
from app.models.submission import Submission, SolvedRecord, LearningLog
from app.schemas.domain import SubmissionRequest, SubmissionResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/submissions", tags=["submissions"])


# ── 인메모리 채점 큐 (ARCHITECTURE 2.6) ──────────────────────────────────────
_judge_queue: asyncio.Queue = asyncio.Queue()


async def _judge_worker(submission_id: int, db: Session) -> None:
    """백그라운드 Judge0 채점 워커.

    Judge0 URL이 설정된 경우 실제 채점, 없으면 stub(WA)으로 처리한다.
    실제 Judge0 연동은 Phase 4(feat/judging)에서 완성한다.
    """
    from config.settings import settings

    submission = db.get(Submission, submission_id)
    if not submission:
        return

    submission.status = "JUDGING"
    db.commit()

    try:
        if settings.judge0_url:
            result = await _call_judge0(submission, db)
        else:
            # stub: 항상 AC (개발용)
            result = {"status": "AC", "runtime_ms": 100, "memory_kb": 1024}

        submission.status = result["status"]
        submission.runtime_ms = result.get("runtime_ms")
        submission.memory_kb = result.get("memory_kb")
        db.commit()

        # AC면 SolvedRecord 생성 (커뮤니티 gating용 — FR-30)
        if result["status"] == "AC":
            from sqlalchemy.exc import IntegrityError
            try:
                db.add(SolvedRecord(user_id=submission.user_id, problem_id=submission.problem_id))
                db.commit()
            except IntegrityError:
                db.rollback()  # 이미 AC 기록 있음

        # 학습 로그 저장 (FR-24)
        if result["status"] != "AC":
            db.add(LearningLog(
                user_id=submission.user_id,
                problem_id=submission.problem_id,
                submission_id=submission.id,
                error_type=result["status"],
                resolved=False,
            ))
            db.commit()

    except Exception as exc:
        logger.exception("채점 워커 오류 (submission_id=%s): %s", submission_id, exc)
        submission.status = "RE"
        db.commit()


async def _call_judge0(submission: "Submission", db: Session) -> dict:
    """Judge0 REST API 호출 — hidden testcase 기준 채점.

    실제 구현은 Phase 4에서 run_user_code Tool과 연결한다.
    현재는 stub 결과를 반환한다.
    """
    import httpx
    from config.settings import settings

    hidden_cases = (
        db.query(TestCase)
        .filter(TestCase.problem_id == submission.problem_id, TestCase.type == "hidden")
        .all()
    )
    if not hidden_cases:
        return {"status": "AC", "runtime_ms": 0, "memory_kb": 0}

    # 언어 ID 매핑 (Judge0 기준)
    lang_map = {"python": 71, "python3": 71, "java": 62, "cpp": 54, "c++": 54}
    language_id = lang_map.get(submission.language.lower(), 71)

    headers = {}
    if settings.judge0_auth_token:
        headers["X-Auth-Token"] = settings.judge0_auth_token

    worst_status = "AC"
    worst_runtime = 0
    worst_memory = 0

    async with httpx.AsyncClient(base_url=settings.judge0_url, timeout=30) as client:
        for tc in hidden_cases[:5]:  # 최대 5케이스
            payload = {
                "source_code": submission.code,
                "language_id": language_id,
                "stdin": tc.input,
                "expected_output": tc.expected_output,
            }
            resp = await client.post("/submissions?wait=true", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            status_id = data.get("status", {}).get("id", 3)
            # Judge0 status: 3=AC, 4=WA, 5=TLE, 6=CE, 7-12=RE, 14=MLE
            status_map = {3: "AC", 4: "WA", 5: "TLE", 6: "RE", 14: "MLE"}
            tc_status = status_map.get(status_id, "RE")

            if tc_status != "AC":
                worst_status = tc_status
                break

            worst_runtime = max(worst_runtime, int(float(data.get("time", 0) or 0) * 1000))
            worst_memory = max(worst_memory, int(data.get("memory", 0) or 0))

    return {"status": worst_status, "runtime_ms": worst_runtime, "memory_kb": worst_memory}


@router.post("/{problem_id}", response_model=SubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit(
    problem_id: str,
    body: SubmissionRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SubmissionResponse:
    """코드 제출 → 인메모리 큐에 채점 작업 등록 → 202 즉시 응답.

    채점 결과는 GET /api/submissions/{submission_id}로 폴링한다 (FR-14).
    """
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문제를 찾을 수 없습니다.")

    submission = Submission(
        user_id=user_id,
        problem_id=problem_id,
        code=body.code,
        language=body.language,
        status="PENDING",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # 백그라운드 채점 (인메모리 큐 — ARCHITECTURE 2.6)
    background_tasks.add_task(_judge_worker, submission.id, db)

    return SubmissionResponse.model_validate(submission)


@router.get("/{submission_id}", response_model=SubmissionResponse)
def get_submission(
    submission_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SubmissionResponse:
    """채점 결과 폴링 — 본인 제출만 조회 가능."""
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="제출 내역을 찾을 수 없습니다.")
    if submission.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")
    return SubmissionResponse.model_validate(submission)


@router.get("/problem/{problem_id}", response_model=List[SubmissionResponse])
def list_submissions_for_problem(
    problem_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> List[SubmissionResponse]:
    """특정 문제의 내 제출 이력."""
    subs = (
        db.query(Submission)
        .filter(Submission.user_id == user_id, Submission.problem_id == problem_id)
        .order_by(Submission.created_at.desc())
        .limit(20)
        .all()
    )
    return [SubmissionResponse.model_validate(s) for s in subs]
