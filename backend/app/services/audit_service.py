"""审计日志服务 (PRD §7.8 / §9.6)。"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import summarize_for_log
from app.models.audit_log import AuditLog


def record(
    db: Session,
    *,
    user_id: str,
    action: str,
    skill_id: int | None = None,
    version_id: int | None = None,
    summary: str | None = None,
    ip: str | None = None,
    llm_job_id: int | None = None,
    git_commit_sha: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """写一条审计;summary 自动截断为摘要。"""
    metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
    log = AuditLog(
        user_id=user_id,
        skill_id=skill_id,
        version_id=version_id,
        action=action,
        summary=summarize_for_log(summary),
        ip=ip,
        llm_job_id=llm_job_id,
        git_commit_sha=git_commit_sha,
        metadata_json=metadata_json,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
