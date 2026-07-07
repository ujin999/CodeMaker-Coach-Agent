"""User 모델 — 학습자 계정."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relations
    submissions: Mapped[list["Submission"]] = relationship("Submission", back_populates="user")
    shared_solutions: Mapped[list["SharedSolution"]] = relationship("SharedSolution", back_populates="user")


# Circular import 방지용 지연 임포트
from app.models.submission import Submission  # noqa: E402
from app.models.community import SharedSolution  # noqa: E402
