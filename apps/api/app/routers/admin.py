"""Admin 라우터 — 신고 누적 문제 HITL 검토/조치 (FR-34).

is_admin 사용자만 접근 가능하다. 최초 관리자 계정은 API로 만들 수 없으므로
DB에서 직접 `UPDATE users SET is_admin = true WHERE email = '...'`로 설정한다.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.db import get_db
from app.models.community import ProblemReport
from app.models.problem import Problem
from app.schemas.domain import (
    FlaggedProblemResponse,
    FlaggedReportSummary,
    ProblemReviewRequest,
    ProblemReviewResponse,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _report_count(db: Session, problem_id: str) -> int:
    return db.query(ProblemReport).filter(ProblemReport.problem_id == problem_id).count()


@router.get("/problems/flagged", response_model=List[FlaggedProblemResponse])
def list_flagged_problems(
    _admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
) -> List[FlaggedProblemResponse]:
    """검토 대기(under_review) 문제 목록 — 신고 사유 포함."""
    problems = (
        db.query(Problem)
        .filter(Problem.status == "under_review")
        .order_by(Problem.created_at.desc())
        .all()
    )

    result: List[FlaggedProblemResponse] = []
    for p in problems:
        reports = (
            db.query(ProblemReport)
            .filter(ProblemReport.problem_id == p.id)
            .order_by(ProblemReport.created_at.desc())
            .all()
        )
        result.append(
            FlaggedProblemResponse(
                id=p.id,
                title=p.title,
                difficulty=p.difficulty,
                algorithm=p.algorithm,
                statement=p.statement,
                status=p.status,
                report_count=len(reports),
                reports=[FlaggedReportSummary.model_validate(r) for r in reports],
                created_at=p.created_at,
            )
        )
    return result


@router.post("/problems/{problem_id}/review", response_model=ProblemReviewResponse)
def review_flagged_problem(
    problem_id: str,
    body: ProblemReviewRequest,
    _admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProblemReviewResponse:
    """HITL 조치.

    - dismiss: 신고가 근거 없다고 판단 — 기존 신고 기록을 지우고 active로 복구한다.
    - remove: 문제를 소프트 삭제한다(상태만 변경). 신고 기록은 감사 목적으로 남긴다.
      실제 DELETE를 하지 않는 이유: Submission/SharedSolution 등 관련 레코드가
      ondelete=CASCADE라서, 하드 삭제하면 사용자들의 기존 제출/학습 이력까지
      같이 사라진다.
    - edit: 지적된 필드를 수정한 뒤 신고 기록을 지우고 active로 복구한다(내용이
      바뀌었으므로 기존 신고는 더 이상 유효하지 않다고 본다).
    """
    problem = db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문제를 찾을 수 없습니다.")

    if body.action == "remove":
        problem.status = "removed"
    else:
        if body.action == "edit":
            if body.title is not None:
                problem.title = body.title
            if body.statement is not None:
                problem.statement = body.statement
            if body.difficulty is not None:
                problem.difficulty = body.difficulty
            if body.constraints is not None:
                problem.constraints = body.constraints
            if body.sample_input is not None:
                problem.sample_input = body.sample_input
            if body.sample_output is not None:
                problem.sample_output = body.sample_output

        # dismiss/edit 모두 조치가 끝났으므로 기존 신고를 지우고 복구한다.
        db.query(ProblemReport).filter(ProblemReport.problem_id == problem_id).delete()
        problem.status = "active"

    db.commit()

    return ProblemReviewResponse(
        id=problem.id,
        status=problem.status,
        report_count=_report_count(db, problem_id),
    )
