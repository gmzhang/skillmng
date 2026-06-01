"""add antcode project metadata to skills

Revision ID: 0005_antcode_metadata
Revises: 0004_llm_jobs
Create Date: 2026-05-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_antcode_metadata"
down_revision: Union[str, None] = "0004_llm_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("skills") as batch:
        batch.add_column(sa.Column("git_project_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("git_namespace_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("git_path_with_namespace", sa.String(length=512), nullable=True)
        )
        batch.add_column(sa.Column("git_http_url", sa.String(length=512), nullable=True))
        batch.add_column(sa.Column("git_ssh_url", sa.String(length=512), nullable=True))
        batch.add_column(sa.Column("git_web_url", sa.String(length=512), nullable=True))
        batch.add_column(
            sa.Column(
                "default_branch",
                sa.String(length=128),
                nullable=False,
                server_default="master",
            )
        )
        batch.add_column(sa.Column("draft_branch", sa.String(length=256), nullable=True))
        batch.add_column(sa.Column("draft_commit_sha", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("published_commit_sha", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("current_version", sa.String(length=32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("skills") as batch:
        batch.drop_column("current_version")
        batch.drop_column("published_commit_sha")
        batch.drop_column("draft_commit_sha")
        batch.drop_column("draft_branch")
        batch.drop_column("default_branch")
        batch.drop_column("git_web_url")
        batch.drop_column("git_ssh_url")
        batch.drop_column("git_http_url")
        batch.drop_column("git_path_with_namespace")
        batch.drop_column("git_namespace_id")
        batch.drop_column("git_project_id")
