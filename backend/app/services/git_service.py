"""Git 操作服务 (PRD §11)。

设计要点:
- 一个 Skill 对应一个独立 Git 仓库,本地工作目录 {SKILL_GIT_WORKDIR}/{repo_slug}。
- 同一仓库的 Git 写操作通过 threading.Lock 串行化 (PRD §19.3)。
- remote 未绑定时降级为纯本地仓库,publish 不 push。
- GIT_SSH_COMMAND 经环境变量注入,不写硬编码私钥内容。
"""
from __future__ import annotations

import os
import re
import shutil
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from git import GitCommandError, Repo

from app.core.config import get_settings
from app.core.errors import BusinessError

_SAFE_USER_RE = re.compile(r"[^a-z0-9_-]+")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


# ----- 工具函数 -----


def safe_user_id(user_id: str) -> str:
    s = (user_id or "").strip().lower()
    s = _SAFE_USER_RE.sub("-", s)
    return s.strip("-") or "anon"


def compute_repo_name(user_id: str, skill_name: str) -> str:
    return f"{safe_user_id(user_id)}--{skill_name}"


def is_semver(v: str) -> bool:
    return bool(_SEMVER_RE.fullmatch(v or ""))


# ----- 锁 -----

_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_LOCK = threading.Lock()


def _lock_for(repo_path: Path) -> threading.Lock:
    key = str(repo_path.resolve())
    with _LOCKS_LOCK:
        lk = _LOCKS.get(key)
        if lk is None:
            lk = threading.Lock()
            _LOCKS[key] = lk
        return lk


@contextmanager
def repo_guard(repo_path: Path) -> Iterator[None]:
    lk = _lock_for(repo_path)
    lk.acquire()
    try:
        yield
    finally:
        lk.release()


# ----- 环境变量 -----


def _git_env() -> dict[str, str]:
    settings = get_settings()
    env = os.environ.copy()
    if settings.skill_git_ssh_key:
        key_path = settings.skill_git_ssh_key
        env["GIT_SSH_COMMAND"] = (
            f"ssh -i {key_path}"
            f" -o IdentitiesOnly=yes"
            f" -o StrictHostKeyChecking=accept-new"
            f" -o UserKnownHostsFile=/root/.ssh/known_hosts"
        )
    return env


# ----- Repo 生命周期 -----


def repo_path_for(repo_slug: str) -> Path:
    return get_settings().git_workdir_path / repo_slug


def ensure_repo(repo_slug: str, *, remote_url: str | None) -> Path:
    """确保本地仓库存在。

    - 已存在 .git → fetch (有 remote);
    - 不存在 → 有 remote 则 clone;无 remote 则 git init 一个本地仓库。
    """
    settings = get_settings()
    settings.git_workdir_path.mkdir(parents=True, exist_ok=True)
    repo_dir = repo_path_for(repo_slug)
    git_dir = repo_dir / ".git"
    env = _git_env()

    with repo_guard(repo_dir):
        if git_dir.exists():
            repo = Repo(repo_dir)
            if remote_url:
                _ensure_remote(repo, remote_url)
                try:
                    repo.git.update_environment(**env)
                    repo.git.fetch("--all", "--prune")
                except GitCommandError:
                    # fetch 失败不阻断;publish 时再处理
                    pass
            return repo_dir

        repo_dir.mkdir(parents=True, exist_ok=True)
        if remote_url:
            try:
                Repo.clone_from(remote_url, repo_dir, env=env)
            except GitCommandError as e:
                # clone 失败 → 初始化空仓库,记录 remote(后续 publish 再 push)
                if any(repo_dir.iterdir()):
                    shutil.rmtree(repo_dir)
                    repo_dir.mkdir(parents=True, exist_ok=True)
                repo = Repo.init(repo_dir, initial_branch="main")
                _ensure_remote(repo, remote_url)
                # 不抛错,但记日志意识
                _log_warn(f"clone 失败,降级为本地仓库:{e}")
            return repo_dir

        Repo.init(repo_dir, initial_branch="main")
        return repo_dir


def _ensure_remote(repo: Repo, remote_url: str) -> None:
    try:
        origin = repo.remote("origin")
        if origin.url != remote_url:
            origin.set_url(remote_url)
    except ValueError:
        repo.create_remote("origin", remote_url)


def _log_warn(msg: str) -> None:
    import logging

    logging.getLogger("app.git").warning(msg)


# ----- 工作区清理 -----


def _clean_working_dir(repo_dir: Path) -> None:
    """清空仓库工作区中除 .git 外的所有文件与目录。"""
    for child in repo_dir.iterdir():
        if child.name == ".git":
            continue
        if child.is_file():
            child.unlink()
        else:
            shutil.rmtree(child)


def _write_files(repo_dir: Path, files: dict[str, bytes]) -> None:
    """将 path → bytes 映射写入工作区。"""
    for path, data in files.items():
        target = repo_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


# ----- 发布 -----


@dataclass(frozen=True)
class PublishResult:
    commit_sha: str
    tag: str | None
    pushed: bool
    push_error: str | None = None


def publish_version(
    repo_slug: str,
    *,
    files: dict[str, bytes],
    version: str,
    summary: str,
    skill_name: str,
    author_name: str,
    author_email: str,
    remote_url: str | None,
    create_tag: bool = False,
) -> PublishResult:
    """把 files 写入仓库并 commit。返回 commit SHA。"""
    if not is_semver(version):
        raise BusinessError(f"非法语义化版本号:{version}", code="invalid_version")

    repo_dir = ensure_repo(repo_slug, remote_url=remote_url)
    env = _git_env()

    with repo_guard(repo_dir):
        repo = Repo(repo_dir)
        # Ensure we are on master/main branch for the publish commit
        settings = get_settings()
        target_branch = settings.skill_default_branch
        try:
            repo.git.checkout("-B", target_branch, f"origin/{target_branch}")
        except GitCommandError:
            try:
                repo.git.checkout(target_branch)
            except GitCommandError:
                try:
                    repo.git.checkout("--orphan", target_branch)
                except GitCommandError:
                    pass

        _clean_working_dir(repo_dir)
        _write_files(repo_dir, files)

        repo.git.add(A=True)

        # 配置 author
        repo.git.update_environment(
            GIT_AUTHOR_NAME=author_name,
            GIT_AUTHOR_EMAIL=author_email,
            GIT_COMMITTER_NAME=author_name,
            GIT_COMMITTER_EMAIL=author_email,
            **env,
        )

        message = f"release: {skill_name} v{version}\n\n{summary}".strip() + "\n"
        try:
            repo.git.commit("-m", message, "--allow-empty")
        except GitCommandError as e:
            raise BusinessError(f"git commit 失败:{e}", code="git_commit_failed")

        commit_sha = repo.head.commit.hexsha

        tag_name: str | None = None
        if create_tag:
            tag_name = f"v{version}"
            if tag_name in [t.name for t in repo.tags]:
                from app.core.errors import ConflictError
                raise ConflictError(
                    f"Tag {tag_name} 已存在,版本冲突。请使用新版本号。",
                )
            try:
                repo.create_tag(tag_name, message=f"release {version}")
            except GitCommandError as e:
                raise BusinessError(f"git tag 失败:{e}", code="git_tag_failed")

        pushed = False
        push_error: str | None = None
        if remote_url:
            try:
                repo.git.push("origin", f"HEAD:refs/heads/{target_branch}")
                if tag_name:
                    repo.git.push("origin", tag_name)
                pushed = True
            except GitCommandError:
                try:
                    repo.git.fetch("origin")
                    repo.git.push("origin", f"HEAD:refs/heads/{target_branch}")
                    if tag_name:
                        repo.git.push("origin", tag_name)
                    pushed = True
                except GitCommandError as e:
                    push_error = str(e).split("\n")[0][:200]
                    _log_warn(f"push 失败,保留本地 commit:{e}")
                    pushed = False
        elif not remote_url:
            push_error = "未绑定 Git 远程仓库,无法推送"

        return PublishResult(commit_sha=commit_sha, tag=tag_name, pushed=pushed, push_error=push_error)


# ----- 草稿分支 -----


@dataclass(frozen=True)
class DraftCommitResult:
    commit_sha: str
    branch: str
    pushed: bool


def commit_draft(
    repo_slug: str,
    *,
    files: dict[str, bytes],
    branch: str,
    message: str,
    author_name: str,
    author_email: str,
    remote_url: str | None,
) -> DraftCommitResult:
    """将文件提交到草稿分支并推送远端。"""
    repo_dir = ensure_repo(repo_slug, remote_url=remote_url)
    env = _git_env()

    with repo_guard(repo_dir):
        repo = Repo(repo_dir)
        repo.git.update_environment(**env)

        # 创建或切换到草稿分支
        if branch in repo.heads:
            repo.heads[branch].checkout()
        else:
            # 基于当前 HEAD 或 origin/master 创建
            base = None
            try:
                base = repo.commit("origin/master")
            except Exception:
                try:
                    base = repo.head.commit
                except Exception:
                    pass
            if base:
                repo.create_head(branch, base).checkout()
            else:
                repo.git.checkout("-b", branch)

        _clean_working_dir(repo_dir)
        _write_files(repo_dir, files)

        repo.git.add(A=True)

        repo.git.update_environment(
            GIT_AUTHOR_NAME=author_name,
            GIT_AUTHOR_EMAIL=author_email,
            GIT_COMMITTER_NAME=author_name,
            GIT_COMMITTER_EMAIL=author_email,
            **env,
        )

        try:
            repo.git.commit("-m", message, "--allow-empty")
        except GitCommandError as e:
            raise BusinessError(f"草稿 commit 失败:{e}", code="git_commit_failed")

        commit_sha = repo.head.commit.hexsha

        pushed = False
        if remote_url:
            try:
                repo.git.push("origin", f"{branch}:{branch}", "--force")
                pushed = True
            except GitCommandError as e:
                _log_warn(f"草稿 push 失败:{e}")

        # 切回默认分支
        try:
            default = get_settings().skill_default_branch
            if default in repo.heads:
                repo.heads[default].checkout()
        except Exception:
            pass

        return DraftCommitResult(commit_sha=commit_sha, branch=branch, pushed=pushed)


# ----- 读取与 diff -----


def list_files_at(repo_slug: str, sha: str) -> list[str]:
    repo_dir = repo_path_for(repo_slug)
    repo = Repo(repo_dir)
    tree = repo.commit(sha).tree
    paths: list[str] = []

    def _walk(t):
        for blob in t.blobs:
            paths.append(blob.path)
        for sub in t.trees:
            _walk(sub)

    _walk(tree)
    return sorted(paths)


def get_file_at(repo_slug: str, sha: str, path: str) -> bytes:
    repo = Repo(repo_path_for(repo_slug))
    tree = repo.commit(sha).tree
    blob = tree / path
    return blob.data_stream.read()


@dataclass(frozen=True)
class FileDiffEntry:
    path: str
    change: str  # added / removed / modified
    before: str | None
    after: str | None


def diff_versions(repo_slug: str, sha_a: str, sha_b: str) -> list[FileDiffEntry]:
    """按文件返回结构化 diff (UTF-8 文本)。二进制按"二进制变更"提示。"""
    repo = Repo(repo_path_for(repo_slug))
    commit_a = repo.commit(sha_a)
    commit_b = repo.commit(sha_b)

    a_tree = commit_a.tree
    b_tree = commit_b.tree

    def _collect(tree, prefix: str = "") -> dict[str, bytes]:
        out: dict[str, bytes] = {}
        for blob in tree.blobs:
            out[f"{prefix}{blob.name}"] = blob.data_stream.read()
        for sub in tree.trees:
            out.update(_collect(sub, f"{prefix}{sub.name}/"))
        return out

    a_files = _collect(a_tree)
    b_files = _collect(b_tree)

    paths = sorted(set(a_files.keys()) | set(b_files.keys()))
    entries: list[FileDiffEntry] = []
    for p in paths:
        before = a_files.get(p)
        after = b_files.get(p)
        if before is None and after is not None:
            entries.append(
                FileDiffEntry(
                    path=p,
                    change="added",
                    before=None,
                    after=_decode_text(after),
                )
            )
        elif before is not None and after is None:
            entries.append(
                FileDiffEntry(
                    path=p,
                    change="removed",
                    before=_decode_text(before),
                    after=None,
                )
            )
        elif before != after:
            entries.append(
                FileDiffEntry(
                    path=p,
                    change="modified",
                    before=_decode_text(before),
                    after=_decode_text(after),
                )
            )
    return entries


def _decode_text(b: bytes | None) -> str:
    if b is None:
        return ""
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return f"<binary {len(b)} bytes>"


# ----- restore -----


def restore_to_files(repo_slug: str, sha: str) -> dict[str, bytes]:
    """读取目标 commit 全量文件,供调用方再发布一个新版本。

    PRD §7.6:恢复版本不是重写历史,而是基于目标历史版本内容创建一个新 commit。
    """
    paths = list_files_at(repo_slug, sha)
    return {p: get_file_at(repo_slug, sha, p) for p in paths}
