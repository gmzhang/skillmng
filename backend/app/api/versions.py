"""版本 API (PRD §10.4)。"""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.deps import CurrentUserDep, DBDep, get_client_ip
from app.core.config import get_settings
from app.schemas.version import (
    DiffEntryOut,
    DiffOut,
    RestoreBody,
    SkillVersionOut,
    VersionFileEntry,
    VersionPublish,
)
from app.services import audit_service, version_service

router = APIRouter()


def _author(user, settings):
    return (
        settings.skill_git_author_name or user.user_name,
        settings.skill_git_author_email or user.user_email,
    )


@router.get("", response_model=list[SkillVersionOut])
def list_versions(skill_id: int, user: CurrentUserDep, db: DBDep):
    from app.services import skill_service
    skill = skill_service.get_skill(db, user_id=user.user_id, skill_id=skill_id)
    versions = version_service.list_versions(db, user_id=user.user_id, skill_id=skill_id)
    results = []
    for v in versions:
        out = SkillVersionOut.model_validate(v)
        if skill.git_web_url:
            out.commit_url = f"{skill.git_web_url}/-/commit/{v.git_commit_sha}"
            if v.git_tag:
                out.tag_url = f"{skill.git_web_url}/-/tags/{v.git_tag}"
        results.append(out)
    return results


@router.post("", response_model=SkillVersionOut, status_code=201)
def publish(
    skill_id: int,
    body: VersionPublish,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    from app.services import skill_service

    settings = get_settings()
    name, email = _author(user, settings)
    # 预先加载 skill,publish_version 内部会更新其字段,无需二次查询
    skill = skill_service.get_skill(db, user_id=user.user_id, skill_id=skill_id)
    record = version_service.publish_version(
        db,
        user_id=user.user_id,
        skill_id=skill_id,
        version=body.version,
        summary=body.summary,
        change_type=body.change_type,
        author_name=name,
        author_email=email,
        create_tag=body.create_tag,
    )
    # PRD5 §5.3: 审计 metadata 包含 commit/tag URL
    commit_url = ""
    tag_url = ""
    if skill.git_web_url:
        commit_url = f"{skill.git_web_url}/-/commit/{record.git_commit_sha}"
        if record.git_tag:
            tag_url = f"{skill.git_web_url}/-/tags/{record.git_tag}"

    push_result = getattr(record, "_push_result", None)
    git_pushed = push_result.pushed if push_result else None
    push_error = push_result.push_error if push_result else None

    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.version.publish",
        skill_id=skill_id,
        version_id=record.id,
        summary=f"v{record.version} {body.change_type} tag={record.git_tag or '-'} pushed={git_pushed}",
        ip=get_client_ip(request),
        git_commit_sha=record.git_commit_sha,
        metadata={
            "version": record.version,
            "branch": settings.skill_default_branch,
            "commit_sha": record.git_commit_sha,
            "git_tag": record.git_tag,
            "commit_url": commit_url,
            "tag_url": tag_url,
            "git_pushed": git_pushed,
        },
    )
    out = SkillVersionOut.model_validate(record)
    out.git_pushed = git_pushed
    out.push_error = push_error
    return out


@router.get("/{version_id}", response_model=SkillVersionOut)
def get_version(skill_id: int, version_id: int, user: CurrentUserDep, db: DBDep):
    v = version_service.get_version(
        db, user_id=user.user_id, skill_id=skill_id, version_id=version_id
    )
    return SkillVersionOut.model_validate(v)


@router.get("/{version_id}/files", response_model=list[VersionFileEntry])
def list_files_at_version(
    skill_id: int, version_id: int, user: CurrentUserDep, db: DBDep
):
    paths = version_service.list_files_at_version(
        db, user_id=user.user_id, skill_id=skill_id, version_id=version_id
    )
    return [VersionFileEntry(path=p) for p in paths]


@router.post("/{version_id}/restore", response_model=SkillVersionOut)
def restore(
    skill_id: int,
    version_id: int,
    body: RestoreBody,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    settings = get_settings()
    name, email = _author(user, settings)
    record = version_service.restore_version(
        db,
        user_id=user.user_id,
        skill_id=skill_id,
        version_id=version_id,
        new_version=body.new_version,
        summary=body.summary,
        author_name=name,
        author_email=email,
    )
    push_result = getattr(record, "_push_result", None)
    git_pushed = push_result.pushed if push_result else None
    push_error = push_result.push_error if push_result else None

    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.version.restore",
        skill_id=skill_id,
        version_id=record.id,
        summary=f"restore from version_id={version_id} → v{record.version} pushed={git_pushed}",
        ip=get_client_ip(request),
        git_commit_sha=record.git_commit_sha,
    )
    out = SkillVersionOut.model_validate(record)
    out.git_pushed = git_pushed
    out.push_error = push_error
    return out


# diff 路由放在 /api/skills/{skill_id}/diff,挂在另一个 router 上
diff_router = APIRouter()


@diff_router.get("/diff", response_model=DiffOut)
def diff(
    skill_id: int,
    from_version_id: int,
    to_version_id: int,
    user: CurrentUserDep,
    db: DBDep,
):
    entries = version_service.diff_versions(
        db,
        user_id=user.user_id,
        skill_id=skill_id,
        from_version_id=from_version_id,
        to_version_id=to_version_id,
    )
    return DiffOut(
        from_version_id=from_version_id,
        to_version_id=to_version_id,
        files=[
            DiffEntryOut(path=e.path, change=e.change, before=e.before, after=e.after)
            for e in entries
        ],
    )
