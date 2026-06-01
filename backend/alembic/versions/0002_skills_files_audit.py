"""skills + skill_files + audit_logs

Revision ID: 0002_skills_files_audit
Revises: 0001_init_users
Create Date: 2026-05-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_skills_files_audit"
down_revision: Union[str, None] = "0001_init_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("argument_hint", sa.String(length=128), nullable=True),
        sa.Column(
            "disable_model_invocation",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("user_invocable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("current_version_id", sa.Integer(), nullable=True),
        sa.Column("git_group_url", sa.String(length=512), nullable=True),
        sa.Column("git_repo_name", sa.String(length=256), nullable=True),
        sa.Column("git_remote_url", sa.String(length=512), nullable=True),
        sa.Column("git_local_path", sa.String(length=1024), nullable=True),
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
        sa.UniqueConstraint("user_id", "name", name="uq_skills_user_name"),
    )
    op.create_index("ix_skills_user_id", "skills", ["user_id"])
    op.create_index("ix_skills_user_status", "skills", ["user_id", "status"])

    op.create_table(
        "skill_files",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "skill_id",
            sa.Integer(),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("content_blob", sa.LargeBinary(), nullable=True),
        sa.Column("content_type", sa.String(length=16), nullable=False, server_default="text"),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sha256", sa.String(length=64), nullable=False, server_default=""),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("skill_id", "path", name="uq_skill_files_skill_path"),
    )
    op.create_index("ix_skill_files_user_skill", "skill_files", ["user_id", "skill_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=True),
        sa.Column("version_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("llm_job_id", sa.Integer(), nullable=True),
        sa.Column("git_commit_sha", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_user_created", "audit_logs", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_user_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_skill_files_user_skill", table_name="skill_files")
    op.drop_table("skill_files")
    op.drop_index("ix_skills_user_status", table_name="skills")
    op.drop_index("ix_skills_user_id", table_name="skills")
    op.drop_table("skills")
