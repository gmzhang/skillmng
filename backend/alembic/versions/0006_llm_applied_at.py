"""llm_jobs.applied_at

Revision ID: 0006_llm_applied_at
Revises: 0005_antcode_metadata
Create Date: 2026-05-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_llm_applied_at"
down_revision: Union[str, None] = "0005_antcode_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("llm_jobs") as batch:
        batch.add_column(
            sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("llm_jobs") as batch:
        batch.drop_column("applied_at")
