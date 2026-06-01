"""LLM 任务 API (PRD §10.5)。"""
from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DBDep, get_client_ip
from app.models.llm_job import LLMJob
from app.models.skill import Skill
from app.schemas.llm import (
    ApplyResult,
    CreateDraftBody,
    LLMJobDetail,
    LLMJobOut,
    UpdateBody,
)
from app.services import audit_service, llm_job_service

router = APIRouter()


def _enrich(db, job: LLMJob) -> LLMJobOut:
    """填充 PRD2 §4.2 要求的字段。"""
    payload = llm_job_service.parse_payload(job) or {}
    out = LLMJobOut.model_validate(job)
    if job.skill_id:
        s = db.scalar(select(Skill).where(Skill.id == job.skill_id))
        if s is not None:
            out.skill_name = s.name
    out.patches = payload.get("patches") or [
        {"path": f.get("path"), "change": "add"}
        for f in (payload.get("files") or [])
    ]
    out.tests = payload.get("tests") or []
    out.risks = payload.get("risks") or []
    return out


def _to_detail(db, job) -> LLMJobDetail:
    base = _enrich(db, job).model_dump()
    base["output_payload"] = llm_job_service.parse_payload(job)
    return LLMJobDetail(**base)


@router.post("/skill-drafts", response_model=LLMJobOut, status_code=202)
def submit_create(
    body: CreateDraftBody,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    job = llm_job_service.submit_create_job(
        db, user_id=user.user_id, payload=body.model_dump()
    )
    audit_service.record(
        db,
        user_id=user.user_id,
        action="llm.create.submit",
        llm_job_id=job.id,
        summary=f"name={body.skill_name}",
        ip=get_client_ip(request),
    )
    return _enrich(db, job)


@router.post("/skill-updates", response_model=LLMJobOut, status_code=202)
def submit_update(
    body: UpdateBody,
    user: CurrentUserDep,
    db: DBDep,
    request: Request,
):
    job = llm_job_service.submit_update_job(
        db,
        user_id=user.user_id,
        skill_id=body.skill_id,
        goal=body.goal,
        target_version=body.target_version,
    )
    audit_service.record(
        db,
        user_id=user.user_id,
        action="llm.update.submit",
        llm_job_id=job.id,
        skill_id=body.skill_id,
        summary=body.goal[:120],
        ip=get_client_ip(request),
    )
    return _enrich(db, job)


@router.get("/jobs", response_model=list[LLMJobOut])
def list_jobs(
    user: CurrentUserDep,
    db: DBDep,
    skill_id: int | None = None,
):
    jobs = llm_job_service.list_jobs(db, user_id=user.user_id, skill_id=skill_id)
    return [_enrich(db, j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=LLMJobDetail)
def get_job(job_id: int, user: CurrentUserDep, db: DBDep):
    job = llm_job_service.get_job(db, user_id=user.user_id, job_id=job_id)
    return _to_detail(db, job)


@router.post("/jobs/{job_id}/cancel", response_model=LLMJobOut)
def cancel_job(job_id: int, user: CurrentUserDep, db: DBDep, request: Request):
    job = llm_job_service.cancel_job(db, user_id=user.user_id, job_id=job_id)
    audit_service.record(
        db,
        user_id=user.user_id,
        action="llm.job.cancel",
        llm_job_id=job.id,
        ip=get_client_ip(request),
    )
    return _enrich(db, job)


@router.post("/jobs/{job_id}/apply", response_model=ApplyResult)
def apply_job(job_id: int, user: CurrentUserDep, db: DBDep):
    """把 LLM 成果落地为 Skill 草稿(create)或写回当前 Skill(update)。"""
    job = llm_job_service.get_job(db, user_id=user.user_id, job_id=job_id)
    if job.job_type == "create":
        result = llm_job_service.apply_create_output(
            db, user_id=user.user_id, job_id=job_id
        )
    else:
        result = llm_job_service.apply_update_output(
            db, user_id=user.user_id, job_id=job_id
        )
    return ApplyResult(**result)


@router.get("/jobs/{job_id}/patch-diff")
def get_patch_diff(job_id: int, user: CurrentUserDep, db: DBDep):
    """返回该 update job 的 patch 与现有文件的 diff,供落地前预览 (PRD2 §2.7)。"""
    from app.models.skill_file import SkillFile

    job = llm_job_service.get_job(db, user_id=user.user_id, job_id=job_id)
    payload = llm_job_service.parse_payload(job) or {}
    diff: list[dict] = []
    if job.job_type == "update" and job.skill_id:
        rows = db.scalars(
            select(SkillFile).where(SkillFile.skill_id == job.skill_id)
        ).all()
        current = {r.path: (r.content_text or "") for r in rows if r.content_type == "text"}
        for p in payload.get("patches") or []:
            path = p.get("path")
            change = p.get("change")
            after = p.get("content")
            if change == "remove":
                diff.append(
                    {"path": path, "change": "removed", "before": current.get(path, ""), "after": ""}
                )
            elif path in current:
                diff.append(
                    {"path": path, "change": "modified", "before": current.get(path, ""), "after": after or ""}
                )
            else:
                diff.append(
                    {"path": path, "change": "added", "before": "", "after": after or ""}
                )
    elif job.job_type == "create":
        for f in payload.get("files") or []:
            diff.append(
                {
                    "path": f.get("path"),
                    "change": "added",
                    "before": "",
                    "after": f.get("content", ""),
                }
            )
    return {"job_id": job.id, "files": diff, "already_applied": job.applied_at is not None}
