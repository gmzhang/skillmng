"""导入导出 + 审计日志 API (PRD §10.6 / §7.8)。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DBDep, get_client_ip
from app.core.config import get_settings
from app.core.errors import ValidationError
from app.models.audit_log import AuditLog
from app.services import audit_service, importexport_service

router = APIRouter()


class ImportResult(BaseModel):
    skill_id: int
    name: str
    file_count: int


@router.post("/import/zip", response_model=ImportResult, status_code=201)
async def import_zip(
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
    file: UploadFile = File(...),
):
    settings = get_settings()
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise ValidationError(
            f"压缩包超过 {settings.max_upload_bytes} bytes。", code="upload_too_large"
        )
    result = importexport_service.import_zip(
        db,
        user_id=user.user_id,
        data=data,
        max_total_bytes=settings.max_upload_bytes,
        max_file_bytes=settings.max_file_bytes,
        max_asset_bytes=settings.max_asset_file_bytes,
        max_files=settings.max_files_per_skill,
    )
    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.import.zip",
        skill_id=result.skill_id,
        summary=f"name={result.name} files={result.file_count}",
        ip=get_client_ip(request),
    )
    return ImportResult(
        skill_id=result.skill_id, name=result.name, file_count=result.file_count
    )


class ImportMdBody(BaseModel):
    content: str = Field(..., min_length=1)


@router.post("/import/skill-md", response_model=ImportResult, status_code=201)
def import_skill_md(
    body: ImportMdBody,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    result = importexport_service.import_skill_md(
        db, user_id=user.user_id, content=body.content
    )
    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.import.md",
        skill_id=result.skill_id,
        summary=f"name={result.name}",
        ip=get_client_ip(request),
    )
    return ImportResult(
        skill_id=result.skill_id, name=result.name, file_count=result.file_count
    )


# 挂到 /api/skills/{skill_id}/export.zip 与 /api/skills/{skill_id}/versions/{version_id}/export.zip
export_router = APIRouter()


@export_router.get("/export.zip")
def export_current(skill_id: int, user: CurrentUserDep, db: DBDep):
    data = importexport_service.export_zip_current(
        db, user_id=user.user_id, skill_id=skill_id
    )
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="skill-{skill_id}.zip"'
        },
    )


@export_router.get("/versions/{version_id}/export.zip")
def export_version(
    skill_id: int, version_id: int, user: CurrentUserDep, db: DBDep
):
    data = importexport_service.export_zip_version(
        db, user_id=user.user_id, skill_id=skill_id, version_id=version_id
    )
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="skill-{skill_id}-v{version_id}.zip"'
        },
    )


# ---------- 审计日志 ----------

audit_router = APIRouter()


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    skill_id: int | None
    skill_name: str | None = None
    version_id: int | None
    version: str | None = None
    action: str
    action_label: str | None = None
    summary: str | None
    ip: str | None
    llm_job_id: int | None
    git_commit_sha: str | None
    commit_short: str | None = None
    metadata_json: str | None = None
    created_at: datetime


# action → 中文标签 (PRD2 §2.8, PRD5 §4.6)
ACTION_LABELS: dict[str, str] = {
    "skill.create": "创建 Skill",
    "skill.update": "更新 Skill",
    "skill.delete": "删除 Skill",
    "skill.file.write": "写入文件",
    "skill.file.upload": "上传文件",
    "skill.file.delete": "删除文件",
    "skill.version.publish": "发布版本",
    "skill.version.restore": "恢复版本",
    "skill.import.zip": "导入 zip",
    "skill.import.md": "导入 SKILL.md",
    "skill.repository.create": "创建 Git 仓库",
    "skill.repository.bind": "绑定 Git 仓库",
    "skill.repository.sync": "同步 Git 仓库",
    "skill.draft.commit": "提交草稿到分支",
    "skill.skill_md.fix": "修复 SKILL.md",
    "settings.antcode.test": "测试 AntCode 连接",
    "settings.llm.test": "测试 LLM 连接",
    "llm.create.submit": "提交 LLM 创建任务",
    "llm.create.apply": "落地 LLM 创建结果",
    "llm.update.submit": "提交 LLM 更新任务",
    "llm.update.apply": "落地 LLM 更新补丁",
    "llm.job.cancel": "取消 LLM 任务",
}


@audit_router.get("", response_model=list[AuditLogOut])
def list_audit(
    user: CurrentUserDep,
    db: DBDep,
    action: str | None = None,
    skill_id: int | None = None,
    version_id: int | None = None,
    llm_job_id: int | None = None,
    limit: int = 100,
):
    from app.models.skill import Skill
    from app.models.skill_version import SkillVersion

    stmt = select(AuditLog).where(AuditLog.user_id == user.user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if skill_id is not None:
        stmt = stmt.where(AuditLog.skill_id == skill_id)
    if version_id is not None:
        stmt = stmt.where(AuditLog.version_id == version_id)
    if llm_job_id is not None:
        stmt = stmt.where(AuditLog.llm_job_id == llm_job_id)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(min(limit, 500))
    rows = list(db.scalars(stmt).all())

    skill_ids = {r.skill_id for r in rows if r.skill_id}
    version_ids = {r.version_id for r in rows if r.version_id}
    skill_names: dict[int, str] = {}
    if skill_ids:
        for s in db.scalars(select(Skill).where(Skill.id.in_(skill_ids))).all():
            skill_names[s.id] = s.name
    version_labels: dict[int, str] = {}
    if version_ids:
        for v in db.scalars(
            select(SkillVersion).where(SkillVersion.id.in_(version_ids))
        ).all():
            version_labels[v.id] = v.version

    out: list[AuditLogOut] = []
    for r in rows:
        item = AuditLogOut.model_validate(r)
        if r.skill_id and r.skill_id in skill_names:
            item.skill_name = skill_names[r.skill_id]
        if r.version_id and r.version_id in version_labels:
            item.version = version_labels[r.version_id]
        item.action_label = ACTION_LABELS.get(r.action)
        if r.git_commit_sha:
            item.commit_short = r.git_commit_sha[:9]
        out.append(item)
    return out
