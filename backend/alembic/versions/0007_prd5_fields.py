"""PRD5: published_tag, draft_status on skills; metadata_json on audit_logs.

Revision ID: 0007_prd5_fields
Revises: 0006_llm_applied_at
Create Date: 2026-05-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_prd5_fields"
down_revision: Union[str, None] = "0006_llm_applied_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("skills") as batch:
        batch.add_column(
            sa.Column("published_tag", sa.String(64), nullable=True)
        )
        batch.add_column(
            sa.Column("draft_status", sa.String(16), nullable=False, server_default="none")
        )

    with op.batch_alter_table("audit_logs") as batch:
        batch.add_column(
            sa.Column("metadata_json", sa.Text(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("skills") as batch:
        batch.drop_column("published_tag")
        batch.drop_column("draft_status")

    with op.batch_alter_table("audit_logs") as batch:
        batch.drop_column("metadata_json")
