"""llm_jobs

Revision ID: 0004_llm_jobs
Revises: 0003_skill_versions
Create Date: 2026-05-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_llm_jobs"
down_revision: Union[str, None] = "0003_skill_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=True),
        sa.Column("job_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("model", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("output_payload", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_llm_jobs_user_id", "llm_jobs", ["user_id"])
    op.create_index("ix_llm_jobs_user_created", "llm_jobs", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_llm_jobs_user_created", table_name="llm_jobs")
    op.drop_index("ix_llm_jobs_user_id", table_name="llm_jobs")
    op.drop_table("llm_jobs")
