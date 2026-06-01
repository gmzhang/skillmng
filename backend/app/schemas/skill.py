"""Skill / SkillFile / Repository 相关 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SkillCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=64)
    description: str = Field(..., min_length=1)
    argument_hint: str | None = Field(default=None, max_length=128)
    disable_model_invocation: bool = False
    user_invocable: bool = True
    initial_body: str | None = None


class SkillUpdate(BaseModel):
    description: str | None = None
    argument_hint: str | None = None
    disable_model_invocation: bool | None = None
    user_invocable: bool | None = None
    status: str | None = None


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    name: str
    description: str
    argument_hint: str | None
    disable_model_invocation: bool
    user_invocable: bool
    status: str
    current_version_id: int | None
    current_version: str | None = None
    published_commit_sha: str | None = None
    published_tag: str | None = None
    draft_status: str = "none"
    git_remote_url: str | None
    git_repo_name: str | None
    git_project_id: int | None = None
    git_namespace_id: int | None = None
    git_path_with_namespace: str | None = None
    git_http_url: str | None = None
    git_ssh_url: str | None = None
    git_web_url: str | None = None
    default_branch: str | None = None
    draft_branch: str | None = None
    draft_commit_sha: str | None = None
    created_at: datetime
    updated_at: datetime


class SkillListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    status: str
    current_version_id: int | None
    current_version: str | None = None
    published_tag: str | None = None
    draft_branch: str | None = None
    draft_commit_sha: str | None = None
    draft_status: str = "none"
    published_commit_sha: str | None = None
    git_bound: bool = False
    git_project_id: int | None = None
    git_web_url: str | None = None
    git_ssh_url: str | None = None
    validation_status: str = "valid"  # valid / warning / error
    updated_at: datetime
    file_count: int = 0
    last_commit_short: str | None = None


class SkillFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    path: str
    content_type: str
    size: int
    sha256: str
    updated_at: datetime


class SkillFileContent(BaseModel):
    path: str
    content: str  # 文本内容(二进制走 upload 接口)


class RepositoryBind(BaseModel):
    git_remote_url: str = Field(..., min_length=1)
    git_repo_name: str | None = None
