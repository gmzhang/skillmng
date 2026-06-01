"""Skill 文件 API (PRD §10.3)。"""
from __future__ import annotations

from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.deps import CurrentUserDep, DBDep, get_client_ip
from app.core.config import get_settings
from app.core.errors import ValidationError
from app.schemas.skill import SkillFileContent, SkillFileOut
from app.services import audit_service, skill_service

router = APIRouter()


class WriteFileBody(BaseModel):
    path: str
    content: str  # 文本写入;二进制走 upload


@router.get("", response_model=list[SkillFileOut])
def list_files(skill_id: int, user: CurrentUserDep, db: DBDep):
    files = skill_service.list_files(db, user_id=user.user_id, skill_id=skill_id)
    return [SkillFileOut.model_validate(f) for f in files]


@router.get("/content", response_model=SkillFileContent)
def get_file_content(skill_id: int, path: str, user: CurrentUserDep, db: DBDep):
    f = skill_service.get_file(db, user_id=user.user_id, skill_id=skill_id, path=path)
    if f.content_type == "binary":
        raise ValidationError(
            "二进制文件请使用下载接口。", code="binary_file"
        )
    return SkillFileContent(path=f.path, content=f.content_text or "")


@router.put("/content", response_model=SkillFileOut)
def write_file_content(
    skill_id: int,
    body: WriteFileBody,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    settings = get_settings()
    skill = skill_service.get_skill(db, user_id=user.user_id, skill_id=skill_id)
    f = skill_service.write_file(
        db,
        user_id=user.user_id,
        skill=skill,
        path=body.path,
        content=body.content,
        max_default=settings.max_file_bytes,
        max_asset=settings.max_asset_file_bytes,
        max_files=settings.max_files_per_skill,
    )
    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.file.write",
        skill_id=skill.id,
        summary=f"path={f.path} size={f.size}",
        ip=get_client_ip(request),
    )
    return SkillFileOut.model_validate(f)


@router.delete("/content", status_code=204)
def delete_file(
    skill_id: int,
    path: str,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    skill_service.delete_file(db, user_id=user.user_id, skill_id=skill_id, path=path)
    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.file.delete",
        skill_id=skill_id,
        summary=f"path={path}",
        ip=get_client_ip(request),
    )


@router.post("/upload", response_model=SkillFileOut)
async def upload_file(
    skill_id: int,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
    path: str,
    file: UploadFile = File(...),
):
    settings = get_settings()
    skill = skill_service.get_skill(db, user_id=user.user_id, skill_id=skill_id)
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise ValidationError(
            f"上传文件超过 {settings.max_upload_bytes} bytes。", code="upload_too_large"
        )
    # 文本(常见 SKILL.md/scripts/refs)用 utf-8 解码,失败则按 binary
    try:
        text = data.decode("utf-8")
        content: str | bytes = text
    except UnicodeDecodeError:
        content = data
    f = skill_service.write_file(
        db,
        user_id=user.user_id,
        skill=skill,
        path=path,
        content=content,
        max_default=settings.max_file_bytes,
        max_asset=settings.max_asset_file_bytes,
        max_files=settings.max_files_per_skill,
    )
    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.file.upload",
        skill_id=skill.id,
        summary=f"path={f.path} size={f.size}",
        ip=get_client_ip(request),
    )
    return SkillFileOut.model_validate(f)


@router.get("/download")
def download_file(skill_id: int, path: str, user: CurrentUserDep, db: DBDep):
    f = skill_service.get_file(db, user_id=user.user_id, skill_id=skill_id, path=path)
    if f.content_type == "binary":
        return Response(content=f.content_blob or b"", media_type="application/octet-stream")
    return Response(content=(f.content_text or "").encode("utf-8"), media_type="text/plain; charset=utf-8")
