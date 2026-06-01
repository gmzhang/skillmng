"""Skill 业务服务。

- 所有查询必须带 user_id 过滤 (PRD §4.2)
- 写文件统一通过 _hash_and_store
- Git 操作交给 git_service (M3 加载)
"""
from __future__ import annotations

import hashlib
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models.skill import Skill
from app.models.skill_file import SkillFile
from app.services import validation_service as vs


# ----- Skill CRUD -----


def list_skills(db: Session, *, user_id: str, query: str | None = None, status: str | None = None) -> list[Skill]:
    stmt = select(Skill).where(Skill.user_id == user_id)
    if status:
        stmt = stmt.where(Skill.status == status)
    else:
        stmt = stmt.where(Skill.status != "deleted")
    if query:
        like = f"%{query}%"
        stmt = stmt.where((Skill.name.like(like)) | (Skill.description.like(like)))
    stmt = stmt.order_by(Skill.updated_at.desc())
    return list(db.scalars(stmt).all())


def get_skill(db: Session, *, user_id: str, skill_id: int) -> Skill:
    skill = db.scalar(select(Skill).where(Skill.id == skill_id, Skill.user_id == user_id))
    if skill is None:
        raise NotFoundError("Skill 不存在或无权访问。")
    return skill


def create_skill(
    db: Session,
    *,
    user_id: str,
    name: str,
    description: str,
    argument_hint: str | None = None,
    disable_model_invocation: bool = False,
    user_invocable: bool = True,
    initial_body: str | None = None,
) -> Skill:
    vs.validate_skill_name(name)
    vs.require_description(description)

    skill = Skill(
        user_id=user_id,
        name=name,
        description=description,
        argument_hint=argument_hint,
        disable_model_invocation=disable_model_invocation,
        user_invocable=user_invocable,
        status="draft",
    )
    db.add(skill)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(f"Skill 名称 {name} 已存在。")
    db.refresh(skill)

    # 同时写一份默认 SKILL.md 草稿
    body = (initial_body or "").strip() or _default_body(name, description)
    md = vs.render_skill_md(
        name=name,
        description=description,
        body=body,
        argument_hint=argument_hint,
        disable_model_invocation=disable_model_invocation,
        user_invocable=user_invocable,
    )
    write_file(db, user_id=user_id, skill=skill, path="SKILL.md", content=md)
    return skill


def _default_body(name: str, description: str) -> str:
    return (
        f"# {name}\n\n"
        f"{description}\n\n"
        "## 任务说明\n\n说明本 Skill 完成的任务。\n\n"
        "## 执行步骤\n\n1. ...\n2. ...\n3. ...\n\n"
        "## 输出格式\n\n描述结构化输出。\n"
    )


def update_skill(
    db: Session,
    *,
    user_id: str,
    skill_id: int,
    description: str | None = None,
    argument_hint: str | None = None,
    disable_model_invocation: bool | None = None,
    user_invocable: bool | None = None,
    status: str | None = None,
) -> Skill:
    skill = get_skill(db, user_id=user_id, skill_id=skill_id)
    if description is not None:
        vs.require_description(description)
        skill.description = description
    if argument_hint is not None:
        skill.argument_hint = argument_hint or None
    if disable_model_invocation is not None:
        skill.disable_model_invocation = disable_model_invocation
    if user_invocable is not None:
        skill.user_invocable = user_invocable
    if status is not None:
        if status not in {"draft", "published", "archived", "deleted"}:
            raise ValidationError(f"非法 status:{status}")
        skill.status = status
    db.commit()
    db.refresh(skill)
    return skill


def soft_delete_skill(db: Session, *, user_id: str, skill_id: int) -> None:
    skill = get_skill(db, user_id=user_id, skill_id=skill_id)
    skill.status = "deleted"
    db.commit()


# ----- 文件操作 -----


def list_files(db: Session, *, user_id: str, skill_id: int) -> list[SkillFile]:
    get_skill(db, user_id=user_id, skill_id=skill_id)
    stmt = select(SkillFile).where(
        SkillFile.skill_id == skill_id, SkillFile.user_id == user_id
    ).order_by(SkillFile.path.asc())
    return list(db.scalars(stmt).all())


def get_file(db: Session, *, user_id: str, skill_id: int, path: str) -> SkillFile:
    norm = vs.validate_path(path)
    get_skill(db, user_id=user_id, skill_id=skill_id)
    f = db.scalar(
        select(SkillFile).where(
            SkillFile.skill_id == skill_id,
            SkillFile.user_id == user_id,
            SkillFile.path == norm,
        )
    )
    if f is None:
        raise NotFoundError(f"文件 {norm} 不存在。")
    return f


def write_file(
    db: Session,
    *,
    user_id: str,
    skill: Skill,
    path: str,
    content: str | bytes,
    max_default: int | None = None,
    max_asset: int | None = None,
    max_files: int | None = None,
    skip_skill_md_validation: bool = False,
) -> SkillFile:
    """新建或覆盖文件。

    - 文本走 content_text,二进制走 content_blob。
    - 全部计算 sha256 与 size 用于审计。
    - 当 path == "SKILL.md" 且 content 是文本时,强制校验 frontmatter 与 name 一致 (PRD2 §5)。
      skip_skill_md_validation=True 用于内部 restore / 修复流程,绕过该校验。
    """
    norm = vs.validate_path(path)

    if isinstance(content, str):
        data = content.encode("utf-8")
        content_type = "text"
        text_value: str | None = content
        blob_value: bytes | None = None
    else:
        data = bytes(content)
        content_type = "binary"
        text_value = None
        blob_value = data

    if norm == "SKILL.md" and content_type == "text" and not skip_skill_md_validation:
        # 强制 SKILL.md 校验,见 PRD2 §5
        vs.validate_skill_md(text_value or "", expected_name=skill.name)

    if max_default is not None and max_asset is not None:
        vs.validate_file_size(norm, len(data), max_default=max_default, max_asset=max_asset)

    f = db.scalar(
        select(SkillFile).where(
            SkillFile.skill_id == skill.id,
            SkillFile.user_id == user_id,
            SkillFile.path == norm,
        )
    )
    is_new = f is None
    if is_new:
        f = SkillFile(skill_id=skill.id, user_id=user_id, path=norm)
        db.add(f)

    if is_new and max_files is not None:
        # 新增前再校验一次总数
        stmt = select(SkillFile).where(SkillFile.skill_id == skill.id)
        existing = len(list(db.scalars(stmt).all()))
        if existing >= max_files:
            raise ValidationError(
                f"Skill 文件数量已达上限 {max_files}。", code="too_many_files"
            )

    assert f is not None
    f.content_text = text_value
    f.content_blob = blob_value
    f.content_type = content_type
    f.size = len(data)
    f.sha256 = hashlib.sha256(data).hexdigest()
    db.commit()
    db.refresh(f)
    return f


def delete_file(db: Session, *, user_id: str, skill_id: int, path: str) -> None:
    f = get_file(db, user_id=user_id, skill_id=skill_id, path=path)
    if f.path == "SKILL.md":
        raise ValidationError("SKILL.md 不能删除,可编辑覆盖。", code="cannot_delete_skill_md")
    db.delete(f)
    db.commit()


def materialize_files_for_publish(files: Iterable[SkillFile]) -> dict[str, bytes]:
    """把 sqlite 中的草稿文件转成 path → bytes 的 dict,供 Git 写入。"""
    out: dict[str, bytes] = {}
    for f in files:
        if f.content_type == "binary" and f.content_blob is not None:
            out[f.path] = f.content_blob
        else:
            out[f.path] = (f.content_text or "").encode("utf-8")
    return out


def fix_skill_md(db: Session, *, user_id: str, skill_id: int) -> dict:
    """自动拆分双 front matter (PRD2 §5)。返回 {fixed, before, after}。"""
    skill = get_skill(db, user_id=user_id, skill_id=skill_id)
    f = db.scalar(
        select(SkillFile).where(
            SkillFile.skill_id == skill.id,
            SkillFile.user_id == user_id,
            SkillFile.path == "SKILL.md",
        )
    )
    if f is None or f.content_type != "text":
        raise NotFoundError("SKILL.md 不存在或非文本。")
    before = f.content_text or ""
    if not vs.has_multiple_frontmatter(before):
        return {"fixed": False, "before": before, "after": before}
    after = vs.autofix_double_frontmatter(before)
    write_file(
        db,
        user_id=user_id,
        skill=skill,
        path="SKILL.md",
        content=after,
        skip_skill_md_validation=True,
    )
    return {"fixed": True, "before": before, "after": after}


def get_validation_status(db: Session, *, user_id: str, skill_id: int) -> dict:
    """返回 {status, errors, warnings},供 DTO / 前端 提示。"""
    skill = get_skill(db, user_id=user_id, skill_id=skill_id)
    f = db.scalar(
        select(SkillFile).where(
            SkillFile.skill_id == skill.id,
            SkillFile.user_id == user_id,
            SkillFile.path == "SKILL.md",
        )
    )
    if f is None or f.content_type != "text":
        return {"status": "error", "errors": ["缺少 SKILL.md"], "warnings": []}
    report = vs.evaluate_skill_md(f.content_text or "", expected_name=skill.name)
    return {
        "status": report.status,
        "errors": list(report.errors),
        "warnings": list(report.warnings),
    }
