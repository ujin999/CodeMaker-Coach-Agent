"""problem_report_hitl

Revision ID: a7246491255e
Revises: 41b500aad174
Create Date: 2026-07-08 19:54:23.582348

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7246491255e'
down_revision: Union[str, Sequence[str], None] = '41b500aad174'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "problems",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
    )
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # 기존 중복 신고(같은 유저가 같은 문제를 여러 번 신고한 행)를 정리한 뒤 unique 제약을 건다.
    # 가장 오래된 신고만 남기고 나머지는 삭제한다.
    op.execute(
        """
        DELETE FROM problem_reports pr
        USING problem_reports newer
        WHERE pr.user_id = newer.user_id
          AND pr.problem_id = newer.problem_id
          AND pr.id > newer.id
        """
    )
    op.create_unique_constraint(
        "uq_problem_report", "problem_reports", ["user_id", "problem_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_problem_report", "problem_reports", type_="unique")
    op.drop_column("users", "is_admin")
    op.drop_column("problems", "status")
