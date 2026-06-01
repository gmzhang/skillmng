"""GET /api/me — 当前用户信息。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DBDep
from app.models.audit_log import AuditLog
from app.models.llm_job import LLMJob
from app.models.skill import Skill
from app.models.skill_version import SkillVersion

router = APIRouter()


class MeOut(BaseModel):
    user_id: str
    user_name: str | None = None
    user_email: str | None = None


@router.get("/me", response_model=MeOut)
def get_me(user: CurrentUserDep) -> MeOut:
    return MeOut(user_id=user.user_id, user_name=user.user_name, user_email=user.user_email)


class StatsOut(BaseModel):
    skill_total: int
    skill_draft: int
    skill_published: int
    skill_archived: int
    skill_deleted: int
    version_total: int
    llm_running: int
    llm_total: int
    recent_skills: list[dict]
    recent_versions: list[dict]
    recent_audits: list[dict]


@router.get("/workbench/stats", response_model=StatsOut)
def workbench_stats(user: CurrentUserDep, db: DBDep) -> StatsOut:
    status_rows = db.execute(
        select(Skill.status, func.count(Skill.id))
        .where(Skill.user_id == user.user_id, Skill.status != "deleted")
        .group_by(Skill.status)
    ).all()
    by_status = {s: c for s, c in status_rows}
    total = sum(by_status.values())

    version_total = (
        db.scalar(
            select(func.count(SkillVersion.id)).where(SkillVersion.user_id == user.user_id)
        )
        or 0
    )
    llm_total = (
        db.scalar(select(func.count(LLMJob.id)).where(LLMJob.user_id == user.user_id))
        or 0
    )
    llm_running = (
        db.scalar(
            select(func.count(LLMJob.id))
            .where(LLMJob.user_id == user.user_id)
            .where(LLMJob.status.in_(("queued", "running")))
        )
        or 0
    )

    recent_skills_rows = db.scalars(
        select(Skill)
        .where(Skill.user_id == user.user_id)
        .where(Skill.status != "deleted")
        .order_by(Skill.updated_at.desc())
        .limit(5)
    ).all()
    recent_skills = [
        {
            "id": s.id,
            "name": s.name,
            "status": s.status,
            "current_version": s.current_version,
            "updated_at": _iso(s.updated_at),
        }
        for s in recent_skills_rows
    ]

    recent_versions_rows = db.scalars(
        select(SkillVersion)
        .where(SkillVersion.user_id == user.user_id)
        .order_by(SkillVersion.created_at.desc())
        .limit(5)
    ).all()
    skill_name_map: dict[int, str] = {}
    if recent_versions_rows:
        sids = list({v.skill_id for v in recent_versions_rows})
        for s in db.scalars(select(Skill).where(Skill.id.in_(sids))).all():
            skill_name_map[s.id] = s.name
    recent_versions = [
        {
            "id": v.id,
            "skill_id": v.skill_id,
            "skill_name": skill_name_map.get(v.skill_id),
            "version": v.version,
            "git_commit_sha": v.git_commit_sha,
            "created_at": _iso(v.created_at),
        }
        for v in recent_versions_rows
    ]

    recent_audits_rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.user_id == user.user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(8)
    ).all()
    recent_audits = [
        {
            "id": a.id,
            "action": a.action,
            "skill_id": a.skill_id,
            "version_id": a.version_id,
            "summary": a.summary,
            "created_at": _iso(a.created_at),
        }
        for a in recent_audits_rows
    ]

    return StatsOut(
        skill_total=total,
        skill_draft=by_status.get("draft", 0),
        skill_published=by_status.get("published", 0),
        skill_archived=by_status.get("archived", 0),
        skill_deleted=by_status.get("deleted", 0),
        version_total=version_total,
        llm_running=llm_running,
        llm_total=llm_total,
        recent_skills=recent_skills,
        recent_versions=recent_versions,
        recent_audits=recent_audits,
    )


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None
