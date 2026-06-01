"""LLM 任务后台执行器。

设计要点:
- ThreadPoolExecutor 跑后台,不阻塞 API。
- DB 直接 commit,因此每个 worker 任务必须自己开 SessionLocal。
- 测试期可以注入同步执行模式 (set_sync_for_test) 便于断言。
"""
from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from sqlalchemy import select

from app.core.logging import summarize_for_log
from app.db.session import SessionLocal
from app.models.llm_job import LLMJob

_LOGGER = logging.getLogger("app.llm.worker")

# 默认 2 个并发,足以演示;真实环境再调整。
_executor = ThreadPoolExecutor(
    max_workers=int(os.environ.get("LLM_WORKER_MAX", "2")),
    thread_name_prefix="llm-worker",
)
_SYNC_FOR_TEST = False


def set_sync_for_test(enabled: bool) -> None:
    global _SYNC_FOR_TEST
    _SYNC_FOR_TEST = enabled


def submit(job_id: int, fn: Callable[[int], None]) -> None:
    """提交后台任务。测试时同步执行。"""
    if _SYNC_FOR_TEST:
        fn(job_id)
        return
    _executor.submit(_run_safely, fn, job_id)


def _run_safely(fn: Callable[[int], None], job_id: int) -> None:
    try:
        fn(job_id)
    except Exception as e:  # noqa: BLE001
        _LOGGER.exception("LLM job %s failed", job_id)
        _mark_failed(job_id, str(e))


def _mark_failed(job_id: int, msg: str) -> None:
    db = SessionLocal()
    try:
        job = db.scalar(select(LLMJob).where(LLMJob.id == job_id))
        if job is None:
            return
        job.status = "failed"
        job.error_message = summarize_for_log(msg)
        db.commit()
    finally:
        db.close()


def mark_running(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.scalar(select(LLMJob).where(LLMJob.id == job_id))
        if job is None:
            return
        job.status = "running"
        db.commit()
    finally:
        db.close()


def mark_succeeded(
    job_id: int, *, output_summary: str, output_payload: dict
) -> None:
    db = SessionLocal()
    try:
        job = db.scalar(select(LLMJob).where(LLMJob.id == job_id))
        if job is None:
            return
        job.status = "succeeded"
        job.output_summary = summarize_for_log(output_summary)
        job.output_payload = json.dumps(output_payload, ensure_ascii=False)
        db.commit()
    finally:
        db.close()


def shutdown() -> None:
    _executor.shutdown(wait=False, cancel_futures=True)
