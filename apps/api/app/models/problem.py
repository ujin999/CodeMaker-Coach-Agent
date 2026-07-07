"""Problem, TestCase, Hint 모델 — 문제 도메인."""

from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)  # problem_id (LLM 생성 slug)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    algorithm: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    learning_goal: Mapped[str] = mapped_column(Text, nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    input_format: Mapped[str] = mapped_column(Text, nullable=False)
    output_format: Mapped[str] = mapped_column(Text, nullable=False)
    constraints: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    sample_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    sample_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_time_complexity: Mapped[str] = mapped_column(String(100), nullable=False)
    # reference_solution은 절대 API 응답에 포함하지 않음 (FR-20, 정책 1)
    reference_solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relations
    testcases: Mapped[list["TestCase"]] = relationship("TestCase", back_populates="problem", cascade="all, delete-orphan")
    hints: Mapped[list["Hint"]] = relationship("Hint", back_populates="problem", cascade="all, delete-orphan")
    submissions: Mapped[list["Submission"]] = relationship("Submission", back_populates="problem")
    shared_solutions: Mapped[list["SharedSolution"]] = relationship("SharedSolution", back_populates="problem")


class TestCase(Base):
    __tablename__ = "testcases"

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)  # sample | hidden | edge
    input: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)

    problem: Mapped["Problem"] = relationship("Problem", back_populates="testcases")


class Hint(Base):
    """단계별 힌트 — reveals_core_code 는 항상 False (FR-19, 정책 2).

    DB에 저장되는 hints는 문제 생성 시 미리 만들어진 것이며
    RAG로 서빙된다. (REQUIREMENTS FR-5, FR-16)
    """
    __tablename__ = "hints"

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 | 2 | 3
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reveals_core_code: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    code_skeleton: Mapped[str | None] = mapped_column(Text, nullable=True)
    concept_refs: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="generated")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    problem: Mapped["Problem"] = relationship("Problem", back_populates="hints")


# Circular import 방지용 지연 임포트
from app.models.submission import Submission  # noqa: E402
from app.models.community import SharedSolution  # noqa: E402
