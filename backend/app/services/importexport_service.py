"""导入导出服务 (PRD §7.7 / §17.2.1)。

zip 安全:
- 不允许 ../、绝对路径、控制字符。
- 单文件 / 总大小 / 文件数 上限。
- 必须包含 SKILL.md。
- SKILL.md frontmatter 必须合法。
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.models.skill import Skill
from app.services import skill_service, validation_service as vs


@dataclass(frozen=True)
class ImportResult:
    skill_id: int
    name: str
    file_count: int


def import_zip(
    db: Session,
    *,
    user_id: str,
    data: bytes,
    max_total_bytes: int,
    max_file_bytes: int,
    max_asset_bytes: int,
    max_files: int,
) -> ImportResult:
    """从 zip 字节流导入一个 Skill。"""
    if len(data) > max_total_bytes:
        raise ValidationError(
            f"压缩包超过 {max_total_bytes} bytes。", code="upload_too_large"
        )

    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValidationError("zip 文件损坏或不是合法的 zip。", code="bad_zip")

    members = [m for m in zf.infolist() if not m.is_dir()]
    if not members:
        raise ValidationError("zip 中没有文件。", code="empty_zip")
    if len(members) > max_files:
        raise ValidationError(
            f"zip 中文件数 {len(members)} 超出 {max_files}。", code="too_many_files"
        )

    # 兼容某些 zip 的顶层包装目录:若所有路径同一前缀,则去掉
    raw_paths = [m.filename for m in members]
    common_prefix = _detect_common_dir(raw_paths)

    files: dict[str, bytes] = {}
    skill_md_content: str | None = None
    for member in members:
        raw_path = member.filename
        # 提前阻断绝对路径与 .. — 即便后续 normalize 能消解,也要拒绝(PRD §17.2.1)
        if raw_path.startswith("/") or raw_path.startswith("\\") or ".." in raw_path.replace("\\", "/").split("/"):
            raise ValidationError(
                f"zip 中含非法路径:{raw_path}", code="invalid_path"
            )

        rel = raw_path
        if common_prefix and rel.startswith(common_prefix):
            rel = rel[len(common_prefix):]
        if not rel:
            continue

        norm = vs.validate_path(rel)
        content = zf.read(member)
        vs.validate_file_size(
            norm, len(content), max_default=max_file_bytes, max_asset=max_asset_bytes
        )

        files[norm] = content
        if norm == "SKILL.md":
            try:
                skill_md_content = content.decode("utf-8")
            except UnicodeDecodeError:
                raise ValidationError("SKILL.md 必须是 UTF-8 文本。", code="invalid_skill_md")

    if skill_md_content is None:
        raise ValidationError("zip 中缺少 SKILL.md。", code="missing_skill_md")

    parsed = vs.validate_skill_md(skill_md_content)  # 允许 frontmatter name 与 zip 文件中不冲突;后续以 frontmatter 为准
    name = parsed.frontmatter.name

    skill = skill_service.create_skill(
        db,
        user_id=user_id,
        name=name,
        description=parsed.frontmatter.description,
        argument_hint=parsed.frontmatter.argument_hint,
        disable_model_invocation=parsed.frontmatter.disable_model_invocation,
        user_invocable=parsed.frontmatter.user_invocable,
    )

    # 覆盖 SKILL.md + 写其它文件
    for path, content in files.items():
        try:
            text = content.decode("utf-8")
            payload: str | bytes = text
        except UnicodeDecodeError:
            payload = content
        skill_service.write_file(
            db,
            user_id=user_id,
            skill=skill,
            path=path,
            content=payload,
            max_default=max_file_bytes,
            max_asset=max_asset_bytes,
            max_files=max_files,
        )

    return ImportResult(skill_id=skill.id, name=skill.name, file_count=len(files))


def _detect_common_dir(paths: list[str]) -> str:
    """若所有路径都以同一目录(可多层)为前缀,返回该前缀(含尾部斜杠);否则返回 ''。

    例:
    - ["pkg/SKILL.md", "pkg/scripts/run.sh"] → "pkg/"
    - ["a/b/SKILL.md", "a/b/scripts/run.sh"] → "a/b/"
    - ["SKILL.md", "scripts/run.sh"] → ""
    """
    if not paths:
        return ""
    cleaned = [p.replace("\\", "/").lstrip("./") for p in paths]
    parts_list = [p.split("/") for p in cleaned]
    # 只比较目录段(最后一段是文件名,不参与公共前缀)
    common: list[str] = []
    for segments in zip(*[p[:-1] for p in parts_list]):
        if len(set(segments)) == 1:
            common.append(segments[0])
        else:
            break
    if not common:
        return ""
    return "/".join(common) + "/"


def import_skill_md(
    db: Session, *, user_id: str, content: str
) -> ImportResult:
    """粘贴一段 SKILL.md 文本导入。"""
    parsed = vs.validate_skill_md(content)
    skill = skill_service.create_skill(
        db,
        user_id=user_id,
        name=parsed.frontmatter.name,
        description=parsed.frontmatter.description,
        argument_hint=parsed.frontmatter.argument_hint,
        disable_model_invocation=parsed.frontmatter.disable_model_invocation,
        user_invocable=parsed.frontmatter.user_invocable,
    )
    skill_service.write_file(
        db, user_id=user_id, skill=skill, path="SKILL.md", content=content
    )
    return ImportResult(skill_id=skill.id, name=skill.name, file_count=1)


# ---------- 导出 ----------


def export_zip_current(
    db: Session, *, user_id: str, skill_id: int
) -> bytes:
    """导出当前草稿(sqlite 中的文件)。"""
    files = skill_service.list_files(db, user_id=user_id, skill_id=skill_id)
    materialized = skill_service.materialize_files_for_publish(files)
    return _zip_dict(materialized)


def export_zip_version(
    db: Session, *, user_id: str, skill_id: int, version_id: int
) -> bytes:
    """导出指定版本(从 Git 取)。"""
    from app.services import git_service, version_service

    skill: Skill = skill_service.get_skill(db, user_id=user_id, skill_id=skill_id)
    version = version_service.get_version(
        db, user_id=user_id, skill_id=skill_id, version_id=version_id
    )
    repo_slug = skill.git_repo_name or git_service.compute_repo_name(user_id, skill.name)
    paths = git_service.list_files_at(repo_slug, version.git_commit_sha)
    materialized = {
        p: git_service.get_file_at(repo_slug, version.git_commit_sha, p) for p in paths
    }
    return _zip_dict(materialized)


def _zip_dict(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, data in files.items():
            zf.writestr(path, data)
    return buf.getvalue()
