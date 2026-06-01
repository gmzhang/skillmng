"""AntCode 仓库工作流 API (PRD2 §4.5, PRD6 §4.3/§4.4)。"""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUserDep, DBDep, get_client_ip
from app.core.config import get_settings
from app.schemas.skill import SkillOut
from app.schemas.version import SkillVersionOut
from app.services import (
    antcode_skill_service,
    audit_service,
    skill_service,
)

router = APIRouter()


class DraftCommitBody(BaseModel):
    summary: str = Field(default="save draft", max_length=500)


class DraftCommitOut(BaseModel):
    branch: str
    commit_sha: str | None
    changed: bool


class DraftDiffEntry(BaseModel):
    path: str
    change: str
    before: str | None
    after: str | None


class DraftDiffOut(BaseModel):
    draft_branch: str | None
    files: list[DraftDiffEntry]


class PublishBody(BaseModel):
    version: str = Field(..., min_length=1, max_length=32)
    summary: str = Field(default="", max_length=2000)
    change_type: str = Field(default="patch", pattern=r"^(patch|minor|major)$")
    create_tag: bool | None = None


def _author(user, settings):
    return (
        user.user_name or settings.skill_git_author_name,
        user.user_email or settings.skill_git_author_email,
    )


@router.post("/repository/create", response_model=SkillOut)
def create_repository(
    skill_id: int,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    """在 xiaojin-skills group 下创建独立仓库,保存 AntCode metadata。"""
    skill = antcode_skill_service.create_or_bind_repository(
        db, user_id=user.user_id, skill_id=skill_id
    )
    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.repository.create",
        skill_id=skill.id,
        summary=f"project_id={skill.git_project_id} path={skill.git_path_with_namespace}",
        ip=get_client_ip(request),
    )
    return SkillOut.model_validate(skill)


@router.post("/drafts/commit", response_model=DraftCommitOut)
def commit_draft(
    skill_id: int,
    body: DraftCommitBody,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    """把当前 sqlite 文件树推送到草稿分支。"""
    settings = get_settings()
    name, email = _author(user, settings)
    result = antcode_skill_service.commit_draft(
        db,
        user_id=user.user_id,
        skill_id=skill_id,
        author_name=name,
        author_email=email,
        summary=body.summary,
    )
    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.draft.commit",
        skill_id=skill_id,
        summary=f"branch={result.branch} sha={result.commit_sha}",
        ip=get_client_ip(request),
        git_commit_sha=result.commit_sha,
    )
    return DraftCommitOut(
        branch=result.branch, commit_sha=result.commit_sha, changed=result.changed
    )


@router.get("/drafts/diff", response_model=DraftDiffOut)
def get_draft_diff(
    skill_id: int,
    user: CurrentUserDep,
    db: DBDep,
):
    entries = antcode_skill_service.diff_draft_vs_master(
        db, user_id=user.user_id, skill_id=skill_id
    )
    skill = skill_service.get_skill(db, user_id=user.user_id, skill_id=skill_id)
    return DraftDiffOut(
        draft_branch=skill.draft_branch,
        files=[
            DraftDiffEntry(
                path=e.path, change=e.change, before=e.before, after=e.after
            )
            for e in entries
        ],
    )


@router.post("/publish", response_model=SkillVersionOut, status_code=201)
def publish(
    skill_id: int,
    body: PublishBody,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    """合并草稿到 master 并打 tag。

    PRD6 §4.4: publish_to_master 内部在 push 成功后才创建 SkillVersion
    并更新 Skill 正式指针,此处不再重复写入。
    """
    settings = get_settings()
    name, email = _author(user, settings)
    result = antcode_skill_service.publish_to_master(
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

    # 读回 skill 以构造审计 URL
    skill = skill_service.get_skill(db, user_id=user.user_id, skill_id=skill_id)
    commit_url = ""
    tag_url = ""
    if skill.git_web_url:
        commit_url = f"{skill.git_web_url}/-/commit/{result.commit_sha}"
        if result.tag:
            tag_url = f"{skill.git_web_url}/-/tags/{result.tag}"
    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.version.publish",
        skill_id=skill.id,
        version_id=skill.current_version_id,
        summary=f"v{body.version} {body.change_type} tag={result.tag or '-'}",
        ip=get_client_ip(request),
        git_commit_sha=result.commit_sha,
        metadata={
            "version": body.version,
            "branch": skill.default_branch,
            "commit_sha": result.commit_sha,
            "git_tag": result.tag,
            "commit_url": commit_url,
            "tag_url": tag_url,
        },
    )

    # 从数据库读取 publish_to_master 创建的 SkillVersion 返回
    from app.models.skill_version import SkillVersion
    record = db.get(SkillVersion, skill.current_version_id)
    out = SkillVersionOut.model_validate(record)
    out.commit_url = commit_url or None
    out.tag_url = tag_url or None
    return out


@router.post("/repository/sync")
def sync_repository(
    skill_id: int,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    info = antcode_skill_service.sync_from_remote(
        db, user_id=user.user_id, skill_id=skill_id
    )
    audit_service.record(
        db,
        user_id=user.user_id,
        action="skill.repository.sync",
        skill_id=skill_id,
        summary=f"published={info.get('published_commit_sha')}",
        ip=get_client_ip(request),
    )
    return info
