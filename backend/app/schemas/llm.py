"""LLM 任务相关 schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateDraftBody(BaseModel):
    skill_name: str = Field(..., min_length=3, max_length=64)
    description: str = Field(..., min_length=1)
    goal: str = Field(..., min_length=1)
    scenario: str = ""
    trigger: str = ""
    target_agent: str = ""
    extra_materials: str = ""
    constraints: str = ""
    include_scripts: bool = True
    include_references: bool = True


class UpdateBody(BaseModel):
    skill_id: int
    goal: str = Field(..., min_length=1)
    target_version: str | None = None


class LLMJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    skill_id: int | None
    skill_name: str | None = None
    job_type: str
    status: str
    model: str
    input_summary: str | None
    output_summary: str | None
    error_message: str | None
    applied_at: datetime | None = None
    patches: list[dict[str, Any]] = []
    tests: list[str] = []
    risks: list[str] = []
    created_at: datetime
    updated_at: datetime


class LLMJobDetail(LLMJobOut):
    output_payload: dict[str, Any] | None = None


class ApplyResult(BaseModel):
    skill_id: int | None = None
    applied_paths: list[str] | None = None
    change_type: str | None = None
