"""AntCode 仓库工作流服务 (PRD2 §2.10、§4.5)。

职责:
- 在 xiaojin-skills group 下创建独立仓库,保存 project metadata。
- 把当前编辑文件树提交到草稿分支 draft/{user_id}/{skill_name}。
- 计算草稿 vs master 的 diff。
- 把草稿合并到 master、打 tag,作为正式发布。
- 从远端同步:把 master 文件树写回 sqlite。

Git 操作通过本地临时 clone + GitPython 完成;
- HTTPS clone URL 中携带 PRIVATE-TOKEN (oauth2:{token}@host/...) 进行认证。
- token 仅在 URL 中存在于内存,不写文件、不入日志。
"""
from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from git import GitCommandError, Repo
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import BusinessError, ValidationError
from app.models.skill import Skill
from app.services import antcode_client, git_service, skill_service
from app.services.antcode_client import AntCodeProject

_LOGGER = logging.getLogger("app.antcode_workflow")


# ---- slug ----

_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def _slug(value: str) -> str:
    s = (value or "").strip().lower()
    s = _SLUG_RE.sub("-", s)
    return s.strip("-") or "unknown"


def compute_repo_path(skill_name: str) -> str:
    """仓库 path (URL 段)。"""
    return _slug(skill_name)


def compute_draft_branch(user_id: str, skill_name: str) -> str:
    settings = get_settings()
    return f"{settings.skill_draft_branch_prefix}/{_slug(user_id)}/{_slug(skill_name)}"


def resolve_publish_branch(skill: Skill | None = None) -> str:
    """PRD7 §3.4: 正式发布目标分支,第一阶段始终返回 settings.skill_default_branch。

    拒绝 draft/ 开头的分支名。即使 skill.default_branch 被污染也返回正确值。
    """
    settings = get_settings()
    return settings.skill_default_branch


# ---- URL 注 token ----


def inject_token(http_url: str, token: str) -> str:
    """把 PRIVATE-TOKEN 注入 HTTPS URL,用于本地 git clone/push。"""
    if not http_url or not token:
        return http_url
    parsed = urlparse(http_url)
    if not parsed.scheme.startswith("http"):
        return http_url
    netloc = f"oauth2:{token}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


# ---- local clone path ----


def local_repo_path(skill: Skill) -> Path:
    settings = get_settings()
    settings.git_workdir_path.mkdir(parents=True, exist_ok=True)
    slug = compute_repo_path(skill.name)
    return settings.git_workdir_path / f"{skill.user_id}--{slug}"


# ---- 公共操作 ----


@dataclass(frozen=True)
class RepositoryInfo:
    project_id: int
    name: str
    path_with_namespace: str
    http_url: str
    ssh_url: str
    web_url: str
    default_branch: str


def _apply_project_to_skill(db: Session, skill: Skill, project: AntCodeProject) -> Skill:
    """PRD7 §3.4: 回填 AntCode project metadata,但 default_branch 不得被 draft 分支污染。"""
    settings = get_settings()
    skill.git_project_id = project.id
    skill.git_namespace_id = settings.antcode_namespace_id
    skill.git_path_with_namespace = project.path_with_namespace
    skill.git_http_url = project.http_url_to_repo
    skill.git_ssh_url = project.ssh_url_to_repo
    skill.git_web_url = project.web_url
    skill.git_remote_url = project.http_url_to_repo
    skill.git_repo_name = project.path

    remote_branch = project.default_branch or ""
    if remote_branch.startswith(f"{settings.skill_draft_branch_prefix}/"):
        _LOGGER.warning(
            "AntCode 返回 default_branch=%r (draft 分支),忽略并使用 %s",
            remote_branch, settings.skill_default_branch,
        )
        skill.default_branch = settings.skill_default_branch
    elif not remote_branch:
        skill.default_branch = settings.skill_default_branch
    else:
        skill.default_branch = remote_branch

    # PRD7 §3.5: 自动修复已被污染的 default_branch
    if skill.default_branch and skill.default_branch.startswith(
        f"{settings.skill_draft_branch_prefix}/"
    ):
        skill.default_branch = settings.skill_default_branch

    db.commit()
    db.refresh(skill)
    return skill


def _find_existing_project(
    client: antcode_client.AntCodeClient, namespace_path: str, path: str
) -> AntCodeProject | None:
    """按 namespace/path 查找现存项目;失败返回 None。"""
    try:
        return client.get_project_by_path(f"{namespace_path}/{path}")
    except antcode_client.AntCodeError:
        return None


def create_or_bind_repository(
    db: Session,
    *,
    user_id: str,
    skill_id: int,
) -> Skill:
    """首次发布/保存草稿前调用。如果未绑定,创建仓库并保存 metadata;已绑定则刷新一次。"""
    skill = skill_service.get_skill(db, user_id=user_id, skill_id=skill_id)
    settings = get_settings()

    if not antcode_client.is_configured(settings):
        raise BusinessError(
            "ANTCODE_PRIVATE_TOKEN 未配置,请在 .env / .env.local 中填入。",
            code="antcode_token_missing",
        )

    with antcode_client.build_client(settings) as client:
        if skill.git_project_id:
            project = client.get_project(skill.git_project_id)
            return _apply_project_to_skill(db, skill, project)

        # 推 path 用 skill name 的 slug
        path = compute_repo_path(skill.name)
        # 取 namespace 信息以便构造 path_with_namespace 查找
        group = client.get_group(settings.antcode_namespace_id)
        namespace_path = group.get("path") or group.get("full_path") or ""

        # 优先尝试按 path 查找,存在就直接绑定;避免重复创建
        if namespace_path:
            existing = _find_existing_project(client, namespace_path, path)
            if existing is not None:
                return _apply_project_to_skill(db, skill, existing)

        try:
            project = client.create_project(
                name=skill.name,
                path=path,
                namespace_id=settings.antcode_namespace_id,
                description=skill.description[:200] if skill.description else None,
                visibility="private",
                initialize_with_readme=True,
            )
        except antcode_client.AntCodeError as e:
            raise BusinessError(
                f"AntCode 创建仓库失败:{e.message}", code="antcode_create_failed"
            )

        return _apply_project_to_skill(db, skill, project)


# ---- 本地 clone 帮助 ----


def _author_env(user_name: str, user_email: str) -> dict[str, str]:
    return {
        "GIT_AUTHOR_NAME": user_name,
        "GIT_AUTHOR_EMAIL": user_email,
        "GIT_COMMITTER_NAME": user_name,
        "GIT_COMMITTER_EMAIL": user_email,
    }


def _git_ssh_env(settings: Any) -> dict[str, str]:
    """构造 GIT_SSH_COMMAND 环境变量,用于 SSH 认证。"""
    ssh_key = settings.skill_git_ssh_key
    if not ssh_key:
        return {"GIT_SSH_COMMAND": "ssh -o StrictHostKeyChecking=no"}
    import os
    if os.path.isfile(ssh_key):
        return {"GIT_SSH_COMMAND": f"ssh -i {ssh_key} -o IdentitiesOnly=yes -o StrictHostKeyChecking=no"}
    return {"GIT_SSH_COMMAND": "ssh -o StrictHostKeyChecking=no"}


def _resolve_clone_url(skill: Skill, settings: Any) -> tuple[str, dict[str, str]]:
    """决定 clone URL 和额外 env:优先 SSH (避免 token auth 兼容性问题),退回 HTTPS。"""
    if settings.skill_git_ssh_key and skill.git_ssh_url:
        return skill.git_ssh_url, _git_ssh_env(settings)
    auth_url = inject_token(skill.git_http_url or "", settings.antcode_private_token)
    return auth_url, {}


def _apply_git_env(repo: Repo, skill: Skill) -> None:
    """把 SSH env 持久化到 repo 对象,后续 push/fetch 自动使用。"""
    settings = get_settings()
    env = _git_ssh_env(settings) if (settings.skill_git_ssh_key and skill.git_ssh_url) else {}
    if env:
        repo.git.update_environment(**env)


def _ensure_git_remote(repo: Repo, remote_url: str) -> None:
    """PRD5 §4.2: 确保本地仓库存在 origin remote 且 URL 正确。"""
    try:
        origin = repo.remote("origin")
        if origin.url != remote_url:
            origin.set_url(remote_url)
    except ValueError:
        repo.create_remote("origin", remote_url)


def _ensure_clone(skill: Skill) -> Repo:
    """本地不存在则 clone;已存在则 fetch。PRD5 §4.2: 自动修复缺少 origin 的情况。"""
    settings = get_settings()
    if not skill.git_http_url and not skill.git_ssh_url:
        raise BusinessError("Skill 未绑定 Git 仓库,请先创建仓库。", code="repo_not_bound")
    if not antcode_client.is_configured(settings):
        raise BusinessError(
            "ANTCODE_PRIVATE_TOKEN 未配置。", code="antcode_token_missing"
        )

    repo_dir = local_repo_path(skill)
    clone_url, git_env = _resolve_clone_url(skill, settings)

    if (repo_dir / ".git").exists():
        repo = Repo(repo_dir)
        with repo.git.custom_environment(**git_env):
            _ensure_git_remote(repo, clone_url)
            try:
                repo.git.fetch("origin", "--prune")
            except GitCommandError as e:
                _LOGGER.warning("git fetch 失败(将继续尝试): %s", e)
        return repo

    repo_dir.mkdir(parents=True, exist_ok=True)
    try:
        repo = Repo.clone_from(clone_url, repo_dir, env=git_env)
    except GitCommandError as e:
        if repo_dir.exists():
            shutil.rmtree(repo_dir, ignore_errors=True)
        raise BusinessError(
            f"git clone 失败:{e}", code="git_clone_failed"
        ) from e
    return repo


def _checkout_branch(repo: Repo, branch_name: str, *, base: str) -> None:
    """切到 branch_name;不存在则基于 base 创建。"""
    try:
        repo.git.checkout(branch_name)
    except GitCommandError:
        # 远端可能已有该分支
        try:
            repo.git.checkout("-B", branch_name, f"origin/{branch_name}")
        except GitCommandError:
            repo.git.checkout("-B", branch_name, f"origin/{base}")


def _clear_worktree_tracked(repo: Repo) -> None:
    """删掉 worktree 里已跟踪文件(保留 .git)。"""
    for item in Path(repo.working_dir).iterdir():
        if item.name == ".git":
            continue
        if item.is_file():
            item.unlink()
        else:
            shutil.rmtree(item, ignore_errors=True)


# ---- 草稿 commit ----


@dataclass(frozen=True)
class DraftCommitResult:
    branch: str
    commit_sha: str | None
    changed: bool


def commit_draft(
    db: Session,
    *,
    user_id: str,
    skill_id: int,
    author_name: str,
    author_email: str,
    summary: str = "save draft",
) -> DraftCommitResult:
    """把当前 sqlite 文件树推送到 draft/{user_id}/{skill_name}。

    若没改变,返回 changed=False 且 commit_sha 保持原值。
    """
    skill = skill_service.get_skill(db, user_id=user_id, skill_id=skill_id)
    if not skill.git_project_id:
        skill = create_or_bind_repository(db, user_id=user_id, skill_id=skill_id)

    repo = _ensure_clone(skill)
    _apply_git_env(repo, skill)
    settings = get_settings()
    draft_branch = skill.draft_branch or compute_draft_branch(user_id, skill.name)
    default_branch = resolve_publish_branch(skill)

    # 确保 default_branch 在本地存在 (空仓库可能还没有任何分支)
    has_origin_default = False
    try:
        repo.git.rev_parse("--verify", f"origin/{default_branch}")
        has_origin_default = True
    except GitCommandError:
        pass

    if has_origin_default:
        try:
            repo.git.checkout(default_branch)
        except GitCommandError:
            repo.git.checkout("-B", default_branch, f"origin/{default_branch}")
        _checkout_branch(repo, draft_branch, base=default_branch)
    else:
        # 空仓库:直接在孤立分支上工作
        try:
            repo.git.checkout("--orphan", draft_branch)
        except GitCommandError:
            repo.git.checkout(draft_branch)

    # 同步 sqlite 文件树到 worktree
    _clear_worktree_tracked(repo)
    files = skill_service.list_files(db, user_id=user_id, skill_id=skill_id)
    materialized = skill_service.materialize_files_for_publish(files)
    for path, data in materialized.items():
        target = Path(repo.working_dir) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    repo.git.add(A=True)

    # 没有变更直接返回
    if not repo.is_dirty(untracked_files=True) and not repo.head.is_detached:
        try:
            staged = repo.git.diff("--cached", "--name-only").strip()
        except GitCommandError:
            staged = ""
        if not staged:
            head_sha = repo.head.commit.hexsha if not repo.head.is_detached else None
            skill.draft_branch = draft_branch
            skill.draft_commit_sha = head_sha
            db.commit()
            return DraftCommitResult(
                branch=draft_branch, commit_sha=head_sha, changed=False
            )

    repo.git.update_environment(**_author_env(author_name, author_email))
    try:
        repo.git.commit("-m", summary, "--allow-empty")
    except GitCommandError as e:
        raise BusinessError(f"git commit 失败:{e}", code="git_commit_failed") from e

    pushed = False
    try:
        repo.git.push("-u", "origin", draft_branch)
        pushed = True
    except GitCommandError as e:
        _LOGGER.warning("git push 草稿分支失败: %s", e)

    commit_sha = repo.head.commit.hexsha
    skill.draft_branch = draft_branch
    skill.draft_commit_sha = commit_sha
    skill.draft_status = "remote" if pushed else "local_only"
    db.commit()
    return DraftCommitResult(branch=draft_branch, commit_sha=commit_sha, changed=True)


# ---- diff ----


@dataclass(frozen=True)
class DraftDiffEntry:
    path: str
    change: str  # added / modified / removed
    before: str | None
    after: str | None


def diff_draft_vs_master(
    db: Session, *, user_id: str, skill_id: int
) -> list[DraftDiffEntry]:
    skill = skill_service.get_skill(db, user_id=user_id, skill_id=skill_id)
    if not skill.git_project_id:
        raise BusinessError("Skill 未绑定 Git 仓库,请先创建仓库。", code="repo_not_bound")
    if not skill.draft_branch:
        return []
    repo = _ensure_clone(skill)
    _apply_git_env(repo, skill)
    default_branch = resolve_publish_branch(skill)

    try:
        master_sha = repo.git.rev_parse(f"origin/{default_branch}")
    except GitCommandError:
        return []
    try:
        draft_sha = repo.git.rev_parse(f"origin/{skill.draft_branch}")
    except GitCommandError:
        # 远端 draft 分支不存在,可能已被删除
        return []

    entries = git_service.diff_versions(
        _local_slug_for_diff(skill), master_sha, draft_sha
    )
    return [
        DraftDiffEntry(
            path=e.path, change=e.change, before=e.before, after=e.after
        )
        for e in entries
    ]


def _local_slug_for_diff(skill: Skill) -> str:
    """给 git_service.diff_versions 用的 slug — 直接复用本地目录名。"""
    path = local_repo_path(skill)
    return path.name


# ---- 正式发布 ----


@dataclass(frozen=True)
class PublishResult:
    commit_sha: str
    tag: str | None
    merged: bool


def publish_to_master(
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
) -> PublishResult:
    """把草稿分支合并到 master,打 tag,推送。

    PRD6 §4.3: 发布前预检,任何失败都不会更新正式发布字段。
    PRD6 §4.4: push 成功后才写 SkillVersion 和更新 Skill 正式指针。
    """
    from sqlalchemy import select as sa_select
    from app.models.skill_version import SkillVersion
    from app.services import validation_service

    settings = get_settings()
    skill = skill_service.get_skill(db, user_id=user_id, skill_id=skill_id)

    # ---- 预检 1: 版本号格式 ----
    if not git_service.is_semver(version):
        raise ValidationError("版本号必须是 MAJOR.MINOR.PATCH 形式。")

    # ---- 预检 2: 数据库中该 Skill 下版本不存在 ----
    existing_ver = db.scalar(
        sa_select(SkillVersion).where(
            SkillVersion.skill_id == skill_id,
            SkillVersion.user_id == user_id,
            SkillVersion.version == version,
        )
    )
    if existing_ver:
        raise BusinessError(f"版本 {version} 已存在。", code="version_exists")

    # ---- 预检 3: Skill 已绑定 AntCode ----
    if not skill.git_project_id:
        raise BusinessError(
            "Skill 未绑定 Git 仓库,请先创建仓库。", code="repo_not_bound"
        )

    # ---- 预检 4: 草稿存在且状态为 remote ----
    if not skill.draft_branch or not skill.draft_commit_sha:
        raise BusinessError(
            "尚未提交任何草稿,无法发布。", code="no_draft",
        )
    if skill.draft_status == "local_only":
        raise BusinessError(
            "草稿仅存在于本地,请先推送到远端草稿分支。", code="draft_local_only",
        )

    # ---- 预检 5: SKILL.md 校验 ----
    files = skill_service.list_files(db, user_id=user_id, skill_id=skill_id)
    skill_md_file = next((f for f in files if f.path == "SKILL.md"), None)
    if not skill_md_file:
        raise ValidationError("发布前必须有 SKILL.md。")
    skill_md_content = skill_md_file.content_text or ""
    report = validation_service.evaluate_skill_md(
        skill_md_content, expected_name=skill.name
    )
    if report.status == "error":
        raise ValidationError(
            f"SKILL.md 校验失败: {'; '.join(report.errors)}"
        )

    # ---- 预检 6: 本地 clone 可用,origin 正确,可 fetch ----
    repo = _ensure_clone(skill)
    _apply_git_env(repo, skill)
    default_branch = resolve_publish_branch(skill)
    draft_branch = skill.draft_branch

    has_origin_default = True
    try:
        repo.git.fetch("origin", "--prune")
    except GitCommandError as e:
        raise BusinessError(f"无法 fetch 远端仓库: {e}", code="git_fetch_failed")

    try:
        repo.git.rev_parse("--verify", f"origin/{default_branch}")
    except GitCommandError:
        has_origin_default = False

    # ---- 预检 7: 远端 draft branch 存在 ----
    try:
        repo.git.rev_parse("--verify", f"origin/{draft_branch}")
    except GitCommandError:
        raise BusinessError(
            f"远端草稿分支 {draft_branch} 不存在,请先提交草稿。",
            code="draft_branch_missing",
        )

    # ---- 预检 8: draft SHA 一致性 ----
    remote_draft_sha = repo.git.rev_parse(f"origin/{draft_branch}")
    if skill.draft_commit_sha and remote_draft_sha != skill.draft_commit_sha:
        raise BusinessError(
            f"远端草稿分支 HEAD ({remote_draft_sha[:9]}) 与数据库记录 "
            f"({skill.draft_commit_sha[:9]}) 不一致,请重新提交草稿或同步。",
            code="draft_sha_mismatch",
        )

    # ---- 预检 9: 远端 tag 不存在 ----
    tag_name = f"v{version}"
    try:
        repo.git.rev_parse("--verify", f"refs/tags/{tag_name}")
        raise BusinessError(
            f"远端 tag {tag_name} 已存在,请使用新版本号。",
            code="tag_exists",
        )
    except GitCommandError:
        pass  # tag 不存在,符合预期

    # ---- 执行: merge / tag / push ----
    repo.git.update_environment(**_author_env(author_name, author_email))

    if not has_origin_default:
        try:
            repo.git.checkout("-B", default_branch, f"origin/{draft_branch}")
        except GitCommandError as e:
            raise BusinessError(
                f"从草稿创建 master 失败:{e}", code="git_checkout_failed"
            ) from e
        commit_sha = repo.head.commit.hexsha
        try:
            repo.create_tag(tag_name, message=f"release {version}")
        except GitCommandError as e:
            raise BusinessError(f"git tag 失败:{e}", code="git_tag_failed") from e
        try:
            repo.git.push("origin", f"HEAD:{default_branch}")
            repo.git.push("origin", tag_name)
        except GitCommandError as e:
            raise BusinessError(f"git push 失败:{e}", code="git_push_failed") from e
        merged = False
    else:
        repo.git.checkout("-B", default_branch, f"origin/{default_branch}")
        merge_msg = (
            f"release: {skill.name} v{version}\n\nchange_type: {change_type}\n{summary}"
        ).strip() + "\n"
        try:
            repo.git.merge(
                "--no-ff", "-m", merge_msg, f"origin/{draft_branch}",
            )
        except GitCommandError as e:
            raise BusinessError(
                f"merge 草稿到 master 冲突或失败:{e}", code="git_merge_failed"
            )
        commit_sha = repo.head.commit.hexsha
        try:
            repo.create_tag(tag_name, message=f"release {version}")
        except GitCommandError as e:
            raise BusinessError(f"git tag 失败:{e}", code="git_tag_failed")
        try:
            repo.git.push("origin", default_branch)
            repo.git.push("origin", tag_name)
        except GitCommandError as e:
            raise BusinessError(f"git push 失败:{e}", code="git_push_failed")
        merged = True

    # ---- PRD6 §4.4: push 成功后才写 SkillVersion 和更新正式指针 ----
    from sqlalchemy.exc import IntegrityError as _IntegrityError

    version_record = SkillVersion(
        skill_id=skill.id,
        user_id=user_id,
        version=version,
        change_type=change_type,
        summary=summary,
        git_commit_sha=commit_sha,
        git_tag=tag_name,
        author_name=author_name,
        author_email=author_email,
    )
    db.add(version_record)
    try:
        db.flush()
    except _IntegrityError:
        db.rollback()
        raise BusinessError(f"版本 {version} 已存在(并发冲突)。", code="version_exists")

    skill.published_commit_sha = commit_sha
    skill.published_tag = tag_name
    skill.current_version = version
    skill.current_version_id = version_record.id
    skill.draft_status = "none"
    if skill.status == "draft":
        skill.status = "published"

    # 可选删除草稿分支
    if settings.skill_delete_draft_branch_after_publish:
        try:
            repo.git.push("origin", "--delete", draft_branch)
            skill.draft_branch = None
            skill.draft_commit_sha = None
        except GitCommandError:
            _LOGGER.warning("删除远端草稿分支失败,忽略")

    db.commit()
    db.refresh(version_record)
    return PublishResult(commit_sha=commit_sha, tag=tag_name, merged=merged)


# ---- 同步 ----


def sync_from_remote(db: Session, *, user_id: str, skill_id: int) -> dict[str, Any]:
    """从远端拉 master 与 draft 状态,刷新 sqlite 含文件树 (PRD3 §4.3)。"""
    from app.models.skill_file import SkillFile
    from app.models.skill_version import SkillVersion
    from sqlalchemy import select

    skill = skill_service.get_skill(db, user_id=user_id, skill_id=skill_id)
    if not skill.git_project_id:
        raise BusinessError("Skill 未绑定 Git 仓库。", code="repo_not_bound")
    settings = get_settings()
    with antcode_client.build_client(settings) as client:
        project = client.get_project(skill.git_project_id)
        _apply_project_to_skill(db, skill, project)
        branches = client.list_branches(skill.git_project_id)
        tags = client.list_tags(skill.git_project_id)
    by_name = {b.name: b for b in branches}
    default_branch = resolve_publish_branch(skill)
    master_branch = by_name.get(default_branch)
    if master_branch:
        skill.published_commit_sha = master_branch.commit_sha
    # PRD5 §4.4: 草稿分支状态必须和远端一致
    draft_name = skill.draft_branch or compute_draft_branch(user_id, skill.name)
    draft = by_name.get(draft_name)
    if draft:
        skill.draft_branch = draft_name
        skill.draft_commit_sha = draft.commit_sha
        skill.draft_status = "remote"
    else:
        # 远端没有 draft branch,清空数据库 draft 状态
        skill.draft_branch = None
        skill.draft_commit_sha = None
        skill.draft_status = "none"

    # Sync latest version tag
    latest_tag = tags[0].name if tags else None
    if latest_tag and latest_tag.startswith("v"):
        skill.current_version = latest_tag[1:]

    # Backfill current_version_id from skill_versions if missing
    if not skill.current_version_id and skill.current_version:
        ver = db.scalar(
            select(SkillVersion).where(
                SkillVersion.skill_id == skill.id,
                SkillVersion.version == skill.current_version,
            )
        )
        if ver:
            skill.current_version_id = ver.id

    # Recover file tree from local clone of master
    recovered_files = 0
    try:
        repo = _ensure_clone(skill)
        _apply_git_env(repo, skill)
        repo.git.checkout(default_branch)
        repo.git.reset("--hard", f"origin/{default_branch}")
        repo_dir = Path(repo.working_dir)
        # Clear existing sqlite files and re-sync
        db.query(SkillFile).filter(
            SkillFile.skill_id == skill.id, SkillFile.user_id == user_id
        ).delete(synchronize_session=False)
        db.flush()
        for fpath in repo_dir.rglob("*"):
            if fpath.is_dir():
                continue
            rel = str(fpath.relative_to(repo_dir))
            if rel.startswith(".git"):
                continue
            data = fpath.read_bytes()
            try:
                text = data.decode("utf-8")
                content: str | bytes = text
            except UnicodeDecodeError:
                content = data
            skill_service.write_file(
                db, user_id=user_id, skill=skill, path=rel,
                content=content, skip_skill_md_validation=True,
            )
            recovered_files += 1
    except Exception as e:
        _LOGGER.warning("sync 恢复文件树失败: %s", e)

    db.commit()
    return {
        "project": {
            "id": project.id,
            "path_with_namespace": project.path_with_namespace,
            "web_url": project.web_url,
            "default_branch": project.default_branch,
        },
        "branches": [b.name for b in branches],
        "tags": [t.name for t in tags],
        "draft_branch": skill.draft_branch,
        "draft_commit_sha": skill.draft_commit_sha,
        "published_commit_sha": skill.published_commit_sha,
        "current_version": skill.current_version,
        "recovered_files": recovered_files,
    }
