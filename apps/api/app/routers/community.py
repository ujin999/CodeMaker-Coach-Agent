"""Community 라우터 — 코드 공유 / gating / 좋아요·댓글 (FR-29~FR-33).

gating 규칙: 특정 문제의 공유 코드는 해당 문제를 스스로 AC한 사용자에게만 노출 (FR-30, 정책 5).
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.db import get_db
from app.models.community import Comment, Like, SharedSolution
from app.models.submission import SolvedRecord, Submission
from app.schemas.domain import (
    CommentRequest,
    CommentResponse,
    ShareSolutionRequest,
    SharedSolutionResponse,
)

router = APIRouter(prefix="/api/community", tags=["community"])


def _assert_solved(user_id: int, problem_id: str, db: Session) -> None:
    """해당 문제를 AC한 기록이 없으면 403 (FR-30 gating)."""
    solved = (
        db.query(SolvedRecord)
        .filter(SolvedRecord.user_id == user_id, SolvedRecord.problem_id == problem_id)
        .first()
    )
    if not solved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 문제를 먼저 직접 풀어야 다른 사람의 풀이를 볼 수 있습니다.",
        )


@router.post("/share", response_model=SharedSolutionResponse, status_code=status.HTTP_201_CREATED)
def share_solution(
    body: ShareSolutionRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SharedSolutionResponse:
    """풀이 공유 — AC된 제출만 공유 가능 (FR-29)."""
    submission = db.get(Submission, body.submission_id)
    if not submission or submission.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="제출 내역을 찾을 수 없습니다.")
    if submission.status != "AC":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="정답(AC) 처리된 제출만 공유할 수 있습니다.",
        )
    # 이미 공유한 경우
    existing = (
        db.query(SharedSolution)
        .filter(SharedSolution.submission_id == body.submission_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 공유된 제출입니다.")

    shared = SharedSolution(
        submission_id=body.submission_id,
        problem_id=submission.problem_id,
        user_id=user_id,
        title=body.title,
        description=body.description,
        is_public=body.is_public,
    )
    db.add(shared)
    db.commit()
    db.refresh(shared)
    return SharedSolutionResponse.model_validate(shared)


@router.get("/{problem_id}", response_model=List[SharedSolutionResponse])
def list_shared_solutions(
    problem_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    order_by: Optional[str] = Query(default="recent", pattern="^(recent|popular)$"),
) -> List[SharedSolutionResponse]:
    """문제별 공유 풀이 목록 — AC gating 적용 (FR-30, FR-31)."""
    _assert_solved(user_id, problem_id, db)

    q = (
        db.query(SharedSolution)
        .filter(SharedSolution.problem_id == problem_id, SharedSolution.is_public == True)
    )
    if order_by == "popular":
        q = q.order_by(SharedSolution.likes_count.desc())
    else:
        q = q.order_by(SharedSolution.created_at.desc())

    shared = q.offset(skip).limit(limit).all()
    return [SharedSolutionResponse.model_validate(s) for s in shared]


@router.post("/{shared_solution_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def toggle_like(
    shared_solution_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    """좋아요 토글 (FR-32). 없으면 추가, 있으면 취소."""
    shared = db.get(SharedSolution, shared_solution_id)
    if not shared:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공유 풀이를 찾을 수 없습니다.")

    _assert_solved(user_id, shared.problem_id, db)

    existing = (
        db.query(Like)
        .filter(Like.user_id == user_id, Like.shared_solution_id == shared_solution_id)
        .first()
    )
    if existing:
        db.delete(existing)
        shared.likes_count = max(0, shared.likes_count - 1)
    else:
        db.add(Like(user_id=user_id, shared_solution_id=shared_solution_id))
        shared.likes_count += 1
    db.commit()


@router.post("/{shared_solution_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    shared_solution_id: int,
    body: CommentRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CommentResponse:
    """댓글 추가 — AC gating 적용 (FR-32)."""
    shared = db.get(SharedSolution, shared_solution_id)
    if not shared:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공유 풀이를 찾을 수 없습니다.")

    _assert_solved(user_id, shared.problem_id, db)

    comment = Comment(
        shared_solution_id=shared_solution_id,
        user_id=user_id,
        content=body.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return CommentResponse.model_validate(comment)


@router.get("/{shared_solution_id}/comments", response_model=List[CommentResponse])
def list_comments(
    shared_solution_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> List[CommentResponse]:
    """댓글 목록."""
    shared = db.get(SharedSolution, shared_solution_id)
    if not shared:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="공유 풀이를 찾을 수 없습니다.")

    _assert_solved(user_id, shared.problem_id, db)

    comments = (
        db.query(Comment)
        .filter(Comment.shared_solution_id == shared_solution_id)
        .order_by(Comment.created_at.asc())
        .all()
    )
    return [CommentResponse.model_validate(c) for c in comments]
