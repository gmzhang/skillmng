"""Skill 版本服务 — 在 git_service 基础上做版本元数据管理。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import BusinessError, ConflictError, NotFoundError, ValidationError
from app.models.skill import Skill
from app.models.skill_version import SkillVersion
from app.services import git_service, skill_service


def list_versions(db: Session, *, user_id: str, skill_id: int) -> list[SkillVersion]:
    skill_service.get_skill(db, user_id=user_id, skill_id=skill_id)
    stmt = (
        select(SkillVersion)
        .where(SkillVersion.skill_id == skill_id, SkillVersion.user_id == user_id)
        .order_by(SkillVersion.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def get_version(db: Session, *, user_id: str, skill_id: int, version_id: int) -> SkillVersion:
    v = db.scalar(
        select(SkillVersion).where(
            SkillVersion.id == version_id,
            SkillVersion.skill_id == skill_id,
            SkillVersion.user_id == user_id,
        )
    )
    if v is None:
        raise NotFoundError("版本不存在或无权访问。")
    return v


def _resolve_repo_slug(skill: Skill, user_id: str) -> str:
    """PRD7 §4.4: AntCode 绑定的 Skill 使用 antcode_skill_service 的本地 clone 路径。"""
    if skill.git_project_id:
        from app.services import antcode_skill_service
        return antcode_skill_service.local_repo_path(skill).name
    if not skill.git_repo_name:
        skill.git_repo_name = git_service.compute_repo_name(user_id, skill.name)
    return skill.git_repo_name


def publish_version(
    db: Session,
    *,
    user_id: str,
    skill_id: int,
    version: str,
    summary: str,
    change_type: str,
    author_name: str,
    author_email: str,
    create_tag: bool | None = None,
) -> SkillVersion:
    """Legacy/local 发布 (PRD6 §4.2)。

    当 Skill 已绑定 AntCode 仓库时,拒绝此路径——
    正式发布必须走 /drafts/commit → /drafts/diff → /publish。
    """
    settings = get_settings()
    skill = skill_service.get_skill(db, user_id=user_id, skill_id=skill_id)

    if skill.git_project_id:
        raise ValidationError(
            "该 Skill 已绑定 AntCode 仓库,请通过 提交草稿 -> 查看 diff -> 发布 流程操作。"
        )

    if not git_service.is_semver(version):
        raise ValidationError("版本号必须是 MAJOR.MINOR.PATCH 形式。")

    files = skill_service.list_files(db, user_id=user_id, skill_id=skill_id)
    if not any(f.path == "SKILL.md" for f in files):
        raise ValidationError("发布前必须有 SKILL.md。")

    materialized = skill_service.materialize_files_for_publish(files)

    repo_slug = _resolve_repo_slug(skill, user_id)

    push_url = skill.git_ssh_url or skill.git_remote_url
    if not push_url and settings.skill_git_repo_url_template:
        push_url = settings.skill_git_repo_url_template.replace("{repo_slug}", skill.name)
        skill.git_remote_url = push_url

    result = git_service.publish_version(
        repo_slug,
        files=materialized,
        version=version,
        summary=summary,
        skill_name=skill.name,
        author_name=author_name,
        author_email=author_email,
        remote_url=push_url,
        create_tag=True,
    )

    record = SkillVersion(
        skill_id=skill.id,
        user_id=user_id,
        version=version,
        change_type=change_type,
        summary=summary,
        git_commit_sha=result.commit_sha,
        git_tag=result.tag,
        author_name=author_name,
        author_email=author_email,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(f"版本 {version} 已存在。")
    db.refresh(record)

    skill.current_version_id = record.id
    skill.current_version = version
    skill.published_commit_sha = result.commit_sha
    skill.git_local_path = str(git_service.repo_path_for(repo_slug))
    skill.default_branch = settings.skill_default_branch
    if result.tag:
        skill.published_tag = result.tag
    if skill.status == "draft":
        skill.status = "published"
    db.commit()

    record._push_result = result  # type: ignore[attr-defined]
    return record


def list_files_at_version(
    db: Session, *, user_id: str, skill_id: int, version_id: int
) -> list[str]:
    v = get_version(db, user_id=user_id, skill_id=skill_id, version_id=version_id)
    skill = skill_service.get_skill(db, user_id=user_id, skill_id=skill_id)
    repo_slug = _resolve_repo_slug(skill, user_id)
    return git_service.list_files_at(repo_slug, v.git_commit_sha)


def diff_versions(
    db: Session,
    *,
    user_id: str,
    skill_id: int,
    from_version_id: int,
    to_version_id: int,
) -> list[git_service.FileDiffEntry]:
    a = get_version(db, user_id=user_id, skill_id=skill_id, version_id=from_version_id)
    b = get_version(db, user_id=user_id, skill_id=skill_id, version_id=to_version_id)
    skill = skill_service.get_skill(db, user_id=user_id, skill_id=skill_id)
    repo_slug = _resolve_repo_slug(skill, user_id)
    try:
        return git_service.diff_versions(repo_slug, a.git_commit_sha, b.git_commit_sha)
    except Exception as e:
        raise BusinessError(
            f"版本 diff 失败: {e}",
            code="git_diff_failed",
        ) from e


def restore_version(
    db: Session,
    *,
    user_id: str,
    skill_id: int,
    version_id: int,
    new_version: str,
    summary: str,
    author_name: str,
    author_email: str,
) -> SkillVersion:
    """恢复 = 用旧版本内容创建新 commit (PRD §7.6)。"""
    target = get_version(db, user_id=user_id, skill_id=skill_id, version_id=version_id)
    skill = skill_service.get_skill(db, user_id=user_id, skill_id=skill_id)
    repo_slug = _resolve_repo_slug(skill, user_id)

    files = git_service.restore_to_files(repo_slug, target.git_commit_sha)

    # 同步回 sqlite skill_files,使 UI 与状态一致
    from app.models.skill_file import SkillFile

    db.query(SkillFile).filter(
        SkillFile.skill_id == skill.id, SkillFile.user_id == user_id
    ).delete(synchronize_session=False)
    db.commit()
    for path, data in files.items():
        try:
            text = data.decode("utf-8")
            content: str | bytes = text
        except UnicodeDecodeError:
            content = data
        skill_service.write_file(
            db,
            user_id=user_id,
            skill=skill,
            path=path,
            content=content,
            skip_skill_md_validation=True,
        )

    return publish_version(
        db,
        user_id=user_id,
        skill_id=skill_id,
        version=new_version,
        summary=summary or f"restore from v{target.version}",
        change_type="patch",
        author_name=author_name,
        author_email=author_email,
    )
