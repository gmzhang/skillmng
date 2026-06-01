"""Skill 模型 — 一个 Skill 一行,绑定到一个 Git 仓库 (PRD §9.2)。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    argument_hint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    disable_model_invocation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_invocable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    current_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    git_group_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    git_repo_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    git_remote_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    git_local_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # AntCode project metadata (PRD2 §4.6)
    git_project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    git_namespace_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    git_path_with_namespace: Mapped[str | None] = mapped_column(String(512), nullable=True)
    git_http_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    git_ssh_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    git_web_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    default_branch: Mapped[str] = mapped_column(String(128), nullable=False, default="master")
    draft_branch: Mapped[str | None] = mapped_column(String(256), nullable=True)
    draft_commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    draft_status: Mapped[str] = mapped_column(String(16), nullable=False, default="none")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_skills_user_name"),
        Index("ix_skills_user_status", "user_id", "status"),
    )
