"""Submissions 라우터 — 제출 → 인메모리 큐 → Judge0 채점 (FR-11~FR-14, ARCHITECTURE 2.6).

채점은 JudgeQueue(app/queue.py)를 통해 비동기로 처리되며, 클라이언트는
GET /submissions/{id}로 폴링한다. 실제 채점 로직은 app/judge_worker.py에 있다.
큐 인터페이스는 추상화되어 있어 Redis+Celery 전환 시 routers 변경 없음.
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.db import get_db
from app.models.problem import Problem
from app.models.submission import Submission
from app.queue import JudgeQueue, get_judge_queue
from app.schemas.domain import SubmissionRequest, SubmissionResponse, SubmissionReviewRequest

from agent import (
    GeneratedProblem,
    SubmissionResult,
    review_submission_package,
    review_package_to_dict,
)
from agent.schemas import HintBlueprint

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/submissions", tags=["submissions"])


@router.post("/review", status_code=status.HTTP_200_OK)
async def review_submission(
    body: SubmissionReviewRequest,
    user_id: int = Depends(get_current_user_id),
) -> dict:
    """제출 리뷰 — Agent 패키지의 비동기 review_submission_package() 호출.

    채점 결과와 사용자 코드를 분석하여 오답 원인, 반례 설명, 복잡도 분석 등을
    포함한 리뷰 패키지를 반환한다. reference_solution은 포함되지 않는다.
    Judge0 실행 없이 결정론적 분석만 수행한다.
    """
    # Reconstruct minimal GeneratedProblem for the review service
    problem = GeneratedProblem(
        problem_id=body.problem_id,
        title=body.problem_title or "Unknown",
        difficulty=body.problem_difficulty,
        algorithm=body.problem_algorithm,
        learning_goal="",
        statement=body.problem_statement or "",
        input_format="",
        output_format="",
        constraints=[],
        expected_time_complexity="",
        hint_blueprint=HintBlueprint(
            intended_algorithm=body.problem_algorithm,
            core_insight="",
            common_misconceptions=[],
            edge_case_focus=[],
            forbidden_disclosures=[],
            level_1_guidance="",
            level_2_guidance="",
            level_3_guidance="",
        ),
    )

    submission_result = SubmissionResult(
        problem_id=body.problem_id,
        result_type=body.result_type,
        user_code=body.user_code,
        language=body.language,
        failed_testcase_name=body.failed_testcase_name,
        failed_input=body.failed_input,
        expected_output=body.expected_output,
        actual_output=body.actual_output,
        stderr=body.stderr,
    )

    package = await review_submission_package(
        problem=problem,
        submission_result=submission_result,
        include_concept_context=body.include_concept_context,
    )

    return review_package_to_dict(package)


@router.post("/{problem_id}", response_model=SubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit(
    problem_id: str,
    body: SubmissionRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    queue: JudgeQueue = Depends(get_judge_queue),
) -> SubmissionResponse:
    """코드 제출 → 채점 큐에 작업 등록 → 202 즉시 응답.

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

    # 채점 큐에 등록 (ARCHITECTURE 2.6) — 실제 채점은 app/judge_worker.py가 수행
    await queue.enqueue(submission.id)

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




