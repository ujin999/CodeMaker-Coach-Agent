"""Submission, HintProgress, SolvedRecord, LearningLog 모델 — 채점·학습 도메인."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(30), nullable=False)
    # AC | WA | TLE | RE | MLE | PENDING | JUDGING
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    runtime_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    judge0_token: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 비동기 폴링용
    failed_testcase_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    failed_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="submissions")
    problem: Mapped["Problem"] = relationship("Problem", back_populates="submissions")
    shared_solution: Mapped["SharedSolution | None"] = relationship("SharedSolution", back_populates="submission", uselist=False)


class HintProgress(Base):
    """(user, problem)별 허용 힌트 단계 상태 — 힌트 게이트키핑 핵심 (FR-17, FR-18, NFR-4).

    allowed_level 은 서버만 변경할 수 있으며, 클라이언트가 직접 조작 불가.
    """
    __tablename__ = "hint_progress"
    __table_args__ = (UniqueConstraint("user_id", "problem_id", name="uq_hint_progress"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    allowed_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 1~3
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SolvedRecord(Base):
    """AC 기록 — 커뮤니티 공유 코드 gating 판단용 (FR-29, FR-30, 정책 5)."""

    __tablename__ = "solved_records"
    __table_args__ = (UniqueConstraint("user_id", "problem_id", name="uq_solved_record"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    solved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LearningLog(Base):
    """사용자별 학습 이력 (FR-24)."""

    __tablename__ = "learning_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    submission_id: Mapped[int | None] = mapped_column(ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # TLE | WA | RE | MLE
    hint_level_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# Circular import 방지용 지연 임포트
from app.models.user import User  # noqa: E402
from app.models.problem import Problem  # noqa: E402
from app.models.community import SharedSolution  # noqa: E402
