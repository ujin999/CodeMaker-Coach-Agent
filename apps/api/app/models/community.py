"""SharedSolution, Comment, Like, ProblemReport 모델 — 커뮤니티 도메인."""

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


class SharedSolution(Base):
    """공유된 풀이 코드 — AC한 사용자만 공유 가능 (FR-29).

    조회 역시 해당 문제를 AC한 사용자에게만 허용 (FR-30, gating).
    """
    __tablename__ = "shared_solutions"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    likes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    submission: Mapped["Submission"] = relationship("Submission", back_populates="shared_solution")
    problem: Mapped["Problem"] = relationship("Problem", back_populates="shared_solutions")
    user: Mapped["User"] = relationship("User", back_populates="shared_solutions")
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="shared_solution", cascade="all, delete-orphan")
    likes: Mapped[list["Like"]] = relationship("Like", back_populates="shared_solution", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    shared_solution_id: Mapped[int] = mapped_column(
        ForeignKey("shared_solutions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    shared_solution: Mapped["SharedSolution"] = relationship("SharedSolution", back_populates="comments")
    user: Mapped["User"] = relationship("User")


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("user_id", "shared_solution_id", name="uq_like"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shared_solution_id: Mapped[int] = mapped_column(
        ForeignKey("shared_solutions.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    shared_solution: Mapped["SharedSolution"] = relationship("SharedSolution", back_populates="likes")
    user: Mapped["User"] = relationship("User")


class ProblemReport(Base):
    """품질 낮은 생성 문제 신고 (FR-34)."""

    __tablename__ = "problem_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")


# Circular import 방지용 지연 임포트
from app.models.user import User  # noqa: E402
from app.models.problem import Problem  # noqa: E402
from app.models.submission import Submission  # noqa: E402
