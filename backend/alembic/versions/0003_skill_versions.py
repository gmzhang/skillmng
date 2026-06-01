"""skill_versions

Revision ID: 0003_skill_versions
Revises: 0002_skills_files_audit
Create Date: 2026-05-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_skill_versions"
down_revision: Union[str, None] = "0002_skills_files_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "skill_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "skill_id",
            sa.Integer(),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("change_type", sa.String(length=8), nullable=False, server_default="patch"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("git_commit_sha", sa.String(length=64), nullable=False),
        sa.Column("git_tag", sa.String(length=64), nullable=True),
        sa.Column("author_name", sa.String(length=128), nullable=True),
        sa.Column("author_email", sa.String(length=256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "skill_id", "version", name="uq_skill_versions_skill_version"
        ),
    )
    op.create_index("ix_skill_versions_user_id", "skill_versions", ["user_id"])
    op.create_index(
        "ix_skill_versions_skill_created", "skill_versions", ["skill_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_skill_versions_skill_created", table_name="skill_versions")
    op.drop_index("ix_skill_versions_user_id", table_name="skill_versions")
    op.drop_table("skill_versions")
