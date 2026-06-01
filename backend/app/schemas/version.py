"""Skill 版本相关 schema。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VersionPublish(BaseModel):
    version: str = Field(..., min_length=1, max_length=32)
    summary: str = Field(default="", max_length=2000)
    change_type: str = Field(default="patch", pattern=r"^(patch|minor|major)$")
    create_tag: bool | None = None  # None → 走 settings 默认


class SkillVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    skill_id: int
    version: str
    change_type: str
    summary: str | None
    git_commit_sha: str
    git_tag: str | None
    tag_url: str | None = None
    commit_url: str | None = None
    git_pushed: bool | None = None
    push_error: str | None = None
    author_name: str | None
    author_email: str | None
    created_at: datetime


class VersionFileEntry(BaseModel):
    path: str


class DiffEntryOut(BaseModel):
    path: str
    change: str
    before: str | None
    after: str | None


class DiffOut(BaseModel):
    from_version_id: int
    to_version_id: int
    files: list[DiffEntryOut]


class RestoreBody(BaseModel):
    new_version: str = Field(..., min_length=1, max_length=32)
    summary: str = Field(default="", max_length=2000)
