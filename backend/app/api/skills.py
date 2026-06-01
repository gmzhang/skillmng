"""Skill 相关 API (PRD §10.2)。"""
from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DBDep, get_client_ip
from app.core.errors import ValidationError
from app.models.skill import Skill
from app.models.skill_file import SkillFile
from app.models.skill_version import SkillVersion
from app.schemas.skill import (
    RepositoryBind,
    SkillCreate,
    SkillListItem,
    SkillOut,
    SkillUpdate,
)
from app.services import audit_service, skill_service

router = APIRouter()


@router.get("", response_model=list[SkillListItem])
def list_skills(
    user: CurrentUserDep,
    db: DBDep,
    q: str | None = None,
    status: str | None = None,
):
    skills = skill_service.list_skills(db, user_id=user.user_id, query=q, status=status)
    if not skills:
        return []
    counts = dict(
        db.execute(
            select(SkillFile.skill_id, func.count(SkillFile.id))
            .where(SkillFile.skill_id.in_([s.id for s in skills]))
            .group_by(SkillFile.skill_id)
        ).all()
    )
    # Batch-load tags for skills with current_version_id
    version_ids = [s.current_version_id for s in skills if s.current_version_id]
    tag_map: dict[int, str | None] = {}
    if version_ids:
        rows = db.execute(
            select(SkillVersion.id, SkillVersion.git_tag)
            .where(SkillVersion.id.in_(version_ids))
        ).all()
        tag_map = {r[0]: r[1] for r in rows}

    items: list[SkillListItem] = []
    for s in skills:
        out = SkillListItem.model_validate(s)
        out.file_count = counts.get(s.id, 0)
        out.git_bound = bool(s.git_project_id or s.git_remote_url)
        out.last_commit_short = (
            s.published_commit_sha[:9] if s.published_commit_sha else None
        )
        if s.current_version_id:
            out.published_tag = tag_map.get(s.current_version_id)
        out.validation_status = "valid"
        items.append(out)
    return items


@router.post("", response_model=SkillOut, status_code=201)
def create_skill(
    body: SkillCreate,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    skill = skill_service.create_skill(
        db,
        user_id=user.user_id,
        name=body.name,
        description=body.description,
        argument_hint=body.argument_hint,
        disable_model_invocation=body.disable_model_invocation,
        user_invocable=body.user_invocable,
        initial_body=body.initial_body,
    )
    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.create",
        skill_id=skill.id,
        summary=f"name={skill.name}",
        ip=get_client_ip(request),
    )
    return SkillOut.model_validate(skill)


@router.get("/{skill_id}", response_model=SkillOut)
def get_skill(skill_id: int, user: CurrentUserDep, db: DBDep):
    skill = skill_service.get_skill(db, user_id=user.user_id, skill_id=skill_id)
    out = SkillOut.model_validate(skill)
    if skill.current_version_id:
        ver = db.scalar(
            select(SkillVersion).where(SkillVersion.id == skill.current_version_id)
        )
        if ver:
            out.published_tag = ver.git_tag
    return out


@router.patch("/{skill_id}", response_model=SkillOut)
def update_skill(
    skill_id: int,
    body: SkillUpdate,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    skill = skill_service.update_skill(
        db,
        user_id=user.user_id,
        skill_id=skill_id,
        description=body.description,
        argument_hint=body.argument_hint,
        disable_model_invocation=body.disable_model_invocation,
        user_invocable=body.user_invocable,
        status=body.status,
    )
    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.update",
        skill_id=skill.id,
        ip=get_client_ip(request),
    )
    return SkillOut.model_validate(skill)


@router.delete("/{skill_id}", status_code=204)
def delete_skill(skill_id: int, user: CurrentUserDep, db: DBDep, request: Request):
    skill_service.soft_delete_skill(db, user_id=user.user_id, skill_id=skill_id)
    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.delete",
        skill_id=skill_id,
        ip=get_client_ip(request),
    )


@router.post("/{skill_id}/repository", response_model=SkillOut)
def create_repository(
    skill_id: int,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    """在 Git group 下创建独立 Skill 仓库 (M3 才会真正调 Git API)。

    第一阶段:仅初始化本地 git_repo_name 字段,提示需配合 PATCH 绑定 remote URL。
    """
    skill = skill_service.get_skill(db, user_id=user.user_id, skill_id=skill_id)
    if not skill.git_repo_name:
        # 这里不实际调 Git 平台 API。M3 git_service.compute_repo_name 会复用同样规则。
        from app.services.git_service import compute_repo_name

        skill.git_repo_name = compute_repo_name(user.user_id, skill.name)
        db.commit()
        db.refresh(skill)
    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.repository.create",
        skill_id=skill.id,
        summary=f"repo_name={skill.git_repo_name}",
        ip=get_client_ip(request),
    )
    return SkillOut.model_validate(skill)


@router.patch("/{skill_id}/repository", response_model=SkillOut)
def bind_repository(
    skill_id: int,
    body: RepositoryBind,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    """绑定已存在仓库的 remote URL。"""
    skill = skill_service.get_skill(db, user_id=user.user_id, skill_id=skill_id)
    if not body.git_remote_url.strip():
        raise ValidationError("git_remote_url 不能为空。")
    skill.git_remote_url = body.git_remote_url.strip()
    if body.git_repo_name:
        skill.git_repo_name = body.git_repo_name.strip()
    db.commit()
    db.refresh(skill)
    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.repository.bind",
        skill_id=skill.id,
        summary=f"remote={skill.git_remote_url}",
        ip=get_client_ip(request),
    )
    return SkillOut.model_validate(skill)


@router.post("/{skill_id}/draft/commit")
def commit_draft(
    skill_id: int,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    """将当前 sqlite 草稿文件提交到远端草稿分支 (PRD3 §2.3)。"""
    from app.core.config import get_settings as _get_settings
    from app.services import git_service

    settings = _get_settings()
    skill = skill_service.get_skill(db, user_id=user.user_id, skill_id=skill_id)
    files = skill_service.list_files(db, user_id=user.user_id, skill_id=skill_id)
    if not files:
        raise ValidationError("Skill 无任何文件,无法提交草稿。")

    materialized = skill_service.materialize_files_for_publish(files)

    # 自动创建 AntCode 仓库
    from app.services import antcode_client
    if not skill.git_project_id and antcode_client.is_configured(settings):
        from app.services import antcode_skill_service
        skill = antcode_skill_service.create_or_bind_repository(
            db, user_id=user.user_id, skill_id=skill_id,
        )

    repo_slug = skill.git_repo_name
    if not repo_slug:
        repo_slug = git_service.compute_repo_name(user.user_id, skill.name)
        skill.git_repo_name = repo_slug

    branch = f"{settings.skill_draft_branch_prefix}/{user.user_id}/{skill.name}"
    push_url = skill.git_ssh_url or skill.git_remote_url
    if not push_url and settings.skill_git_repo_url_template:
        push_url = settings.skill_git_repo_url_template.replace("{repo_slug}", skill.name)
        skill.git_remote_url = push_url

    result = git_service.commit_draft(
        repo_slug,
        files=materialized,
        branch=branch,
        message=f"draft: {skill.name} save",
        author_name=settings.skill_git_author_name,
        author_email=settings.skill_git_author_email,
        remote_url=push_url,
    )

    skill.draft_branch = branch
    skill.draft_commit_sha = result.commit_sha
    db.commit()

    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.draft.commit",
        skill_id=skill.id,
        summary=f"branch={branch} sha={result.commit_sha[:9]}",
        ip=get_client_ip(request),
    )
    return {
        "commit_sha": result.commit_sha,
        "branch": result.branch,
        "pushed": result.pushed,
    }


@router.get("/{skill_id}/validation")
def get_validation(skill_id: int, user: CurrentUserDep, db: DBDep):
    """返回当前 SKILL.md 的校验状态 (PRD2 §2.4)。"""
    return skill_service.get_validation_status(
        db, user_id=user.user_id, skill_id=skill_id
    )


@router.post("/{skill_id}/skill-md/fix")
def fix_skill_md(
    skill_id: int, user: CurrentUserDep, db: DBDep, request: Request
):
    """自动拆分双 front matter (PRD2 §5)。"""
    result = skill_service.fix_skill_md(
        db, user_id=user.user_id, skill_id=skill_id
    )
    if result["fixed"]:
        audit_service.record(
            db,
            user_id=user.user_id,
            action="skill.skill_md.fix",
            skill_id=skill_id,
            summary="auto-split duplicate frontmatter",
            ip=get_client_ip(request),
        )
    return result
