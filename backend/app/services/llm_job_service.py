"""LLM 任务编排:把请求落 sqlite,后台跑 LLM,落 output_payload。"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import BusinessError, NotFoundError
from app.core.logging import summarize_for_log
from app.db.session import SessionLocal
from app.models.llm_job import LLMJob
from app.services import llm_service, skill_service
from app.services.llm_service import (
    CreateInput,
    UpdateInput,
    get_llm_client,
)
from app.workers import llm_worker


def _input_summary(payload: dict[str, Any]) -> str:
    out: list[str] = []
    for k, v in payload.items():
        if v is None or v == "":
            continue
        if isinstance(v, bool):
            out.append(f"{k}={v}")
        else:
            out.append(f"{k}={summarize_for_log(str(v), 60)}")
    return "; ".join(out)


# ---------- create ----------


def submit_create_job(
    db: Session,
    *,
    user_id: str,
    payload: dict[str, Any],
) -> LLMJob:
    client = get_llm_client()
    job = LLMJob(
        user_id=user_id,
        skill_id=None,
        job_type="create",
        status="queued",
        model=getattr(client, "model_name", "unknown"),
        input_summary=_input_summary(payload),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    llm_worker.submit(job.id, lambda jid: _run_create_job(jid, payload))
    return job


def _run_create_job(job_id: int, payload: dict[str, Any]) -> None:
    llm_worker.mark_running(job_id)
    client = get_llm_client()
    inp = CreateInput(
        skill_name=payload.get("skill_name", ""),
        description=payload.get("description", ""),
        goal=payload.get("goal", ""),
        scenario=payload.get("scenario", ""),
        trigger=payload.get("trigger", ""),
        target_agent=payload.get("target_agent", ""),
        extra_materials=payload.get("extra_materials", ""),
        constraints=payload.get("constraints", ""),
        include_scripts=bool(payload.get("include_scripts", True)),
        include_references=bool(payload.get("include_references", True)),
    )
    out = client.create_skill_draft(inp)
    llm_worker.mark_succeeded(
        job_id,
        output_summary=out.summary,
        output_payload={
            "skill_md": out.skill_md,
            "files": [asdict(f) for f in out.files],
            "summary": out.summary,
            "tests": list(out.tests),
            "risks": list(out.risks),
            "input": payload,
        },
    )


# ---------- update ----------


def submit_update_job(
    db: Session,
    *,
    user_id: str,
    skill_id: int,
    goal: str,
    target_version: str | None = None,
) -> LLMJob:
    skill = skill_service.get_skill(db, user_id=user_id, skill_id=skill_id)
    files = skill_service.list_files(db, user_id=user_id, skill_id=skill_id)
    current = {
        f.path: (f.content_text or "") for f in files if f.content_type == "text"
    }
    client = get_llm_client()
    job = LLMJob(
        user_id=user_id,
        skill_id=skill_id,
        job_type="update",
        status="queued",
        model=getattr(client, "model_name", "unknown"),
        input_summary=_input_summary(
            {"goal": goal, "target_version": target_version, "skill": skill.name}
        ),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    llm_worker.submit(
        job.id,
        lambda jid: _run_update_job(jid, skill.name, current, goal, target_version),
    )
    return job


def _run_update_job(
    job_id: int,
    skill_name: str,
    current_files: dict[str, str],
    goal: str,
    target_version: str | None,
) -> None:
    llm_worker.mark_running(job_id)
    client = get_llm_client()
    out = client.update_skill(
        UpdateInput(
            skill_name=skill_name,
            current_files=current_files,
            goal=goal,
            target_version=target_version,
        )
    )
    llm_worker.mark_succeeded(
        job_id,
        output_summary=out.summary,
        output_payload={
            "patches": [
                {
                    "path": p.path,
                    "change": p.change,
                    "content": p.content,
                }
                for p in out.patches
            ],
            "summary": out.summary,
            "change_type": out.change_type,
            "tests": list(out.tests),
            "risks": list(out.risks),
            "goal": goal,
            "target_version": target_version,
        },
    )


# ---------- listing / cancel ----------


def list_jobs(db: Session, *, user_id: str, skill_id: int | None = None) -> list[LLMJob]:
    stmt = select(LLMJob).where(LLMJob.user_id == user_id)
    if skill_id is not None:
        stmt = stmt.where(LLMJob.skill_id == skill_id)
    stmt = stmt.order_by(LLMJob.created_at.desc())
    return list(db.scalars(stmt).all())


def get_job(db: Session, *, user_id: str, job_id: int) -> LLMJob:
    job = db.scalar(
        select(LLMJob).where(LLMJob.id == job_id, LLMJob.user_id == user_id)
    )
    if job is None:
        raise NotFoundError("LLM 任务不存在或无权访问。")
    return job


def cancel_job(db: Session, *, user_id: str, job_id: int) -> LLMJob:
    job = get_job(db, user_id=user_id, job_id=job_id)
    if job.status in {"succeeded", "failed", "canceled"}:
        raise BusinessError(
            f"任务已处于终态 {job.status},无法取消。", code="job_already_done"
        )
    job.status = "canceled"
    db.commit()
    db.refresh(job)
    return job


def parse_payload(job: LLMJob) -> dict[str, Any] | None:
    if not job.output_payload:
        return None
    return json.loads(job.output_payload)


# ---------- 草稿分支提交 ----------


def _commit_draft_after_apply(db: Session, *, user_id: str, skill_id: int) -> str | None:
    """LLM 落地后,将 sqlite 文件推送到远端草稿分支。

    PRD6 §4.5: 统一走 antcode_skill_service.commit_draft,
    保证仓库自动创建、draft 分支命名、push 逻辑与手动提交草稿一致。
    """
    import logging

    from app.core.config import get_settings as _get_settings

    _logger = logging.getLogger("app.llm_job")
    settings = _get_settings()

    try:
        from app.services import antcode_skill_service
        result = antcode_skill_service.commit_draft(
            db,
            user_id=user_id,
            skill_id=skill_id,
            author_name=settings.skill_git_author_name,
            author_email=settings.skill_git_author_email,
            summary=f"draft: LLM apply",
        )
        return result.commit_sha
    except Exception as e:
        _logger.warning("LLM apply 后 draft commit 失败 (非阻塞): %s", e)
        return None


# ---------- 应用 LLM 输出到 Skill ----------


def apply_create_output(
    db: Session, *, user_id: str, job_id: int
) -> dict[str, Any]:
    """把 create 任务输出落地为一个新 Skill 草稿。返回 {skill_id}。"""
    from datetime import datetime, timezone

    from app.services import audit_service

    job = get_job(db, user_id=user_id, job_id=job_id)
    if job.job_type != "create":
        raise BusinessError("任务类型不是 create。", code="wrong_job_type")
    if job.status != "succeeded":
        raise BusinessError(f"任务尚未成功 ({job.status})。", code="job_not_succeeded")
    if job.applied_at is not None:
        raise BusinessError(
            "该任务已落地,不可重复落地 (PRD2 §2.7)。", code="job_already_applied"
        )
    payload = parse_payload(job) or {}
    inp = payload.get("input") or {}
    name = inp.get("skill_name") or ""
    description = inp.get("description") or "由 LLM 生成的 Skill 描述。"

    skill = skill_service.create_skill(
        db,
        user_id=user_id,
        name=name,
        description=description,
        initial_body=None,
    )
    if payload.get("skill_md"):
        skill_service.write_file(
            db, user_id=user_id, skill=skill, path="SKILL.md", content=payload["skill_md"]
        )
    for f in payload.get("files", []):
        if f.get("path") == "SKILL.md":
            continue
        skill_service.write_file(
            db,
            user_id=user_id,
            skill=skill,
            path=f["path"],
            content=f.get("content", ""),
        )
    job.skill_id = skill.id
    job.applied_at = datetime.now(timezone.utc)
    db.commit()
    audit_service.record(
        db,
        user_id=user_id,
        action="llm.create.apply",
        skill_id=skill.id,
        llm_job_id=job.id,
        summary=f"name={skill.name}",
    )
    # PRD3 §3.6: LLM 落地后提交到草稿分支
    _commit_draft_after_apply(db, user_id=user_id, skill_id=skill.id)
    return {"skill_id": skill.id}


def apply_update_output(
    db: Session, *, user_id: str, job_id: int
) -> dict[str, Any]:
    """把 update 任务的 patches 写回当前 Skill。"""
    from datetime import datetime, timezone

    from app.services import audit_service

    job = get_job(db, user_id=user_id, job_id=job_id)
    if job.job_type != "update":
        raise BusinessError("任务类型不是 update。", code="wrong_job_type")
    if job.status != "succeeded":
        raise BusinessError(f"任务尚未成功 ({job.status})。", code="job_not_succeeded")
    if job.skill_id is None:
        raise BusinessError("update 任务缺少 skill_id。", code="missing_skill")
    if job.applied_at is not None:
        raise BusinessError(
            "该任务已落地,不可重复落地 (PRD2 §2.7)。", code="job_already_applied"
        )
    payload = parse_payload(job) or {}
    skill = skill_service.get_skill(db, user_id=user_id, skill_id=job.skill_id)
    applied_paths: list[str] = []
    for patch in payload.get("patches", []):
        path = patch.get("path")
        change = patch.get("change")
        content = patch.get("content")
        if not path:
            continue
        if change == "remove":
            try:
                skill_service.delete_file(
                    db, user_id=user_id, skill_id=skill.id, path=path
                )
            except Exception:
                pass
            applied_paths.append(path)
            continue
        skill_service.write_file(
            db, user_id=user_id, skill=skill, path=path, content=content or ""
        )
        applied_paths.append(path)
    job.applied_at = datetime.now(timezone.utc)
    db.commit()
    audit_service.record(
        db,
        user_id=user_id,
        action="llm.update.apply",
        skill_id=skill.id,
        llm_job_id=job.id,
        summary=f"patches={len(applied_paths)}",
    )
    # PRD3 §3.6: LLM 落地后提交到草稿分支
    _commit_draft_after_apply(db, user_id=user_id, skill_id=skill.id)
    return {
        "skill_id": skill.id,
        "applied_paths": applied_paths,
        "change_type": payload.get("change_type", "patch"),
    }


# ---------- 用于 worker 使用,封装 SessionLocal 的便捷查询 ----------


def get_job_standalone(job_id: int) -> LLMJob | None:
    db = SessionLocal()
    try:
        return db.scalar(select(LLMJob).where(LLMJob.id == job_id))
    finally:
        db.close()
