"""sqlite 引擎与 Session。

第一阶段使用同步 SQLAlchemy 2.x。FastAPI 路由用 def(线程池),DB 调用走 SessionLocal。
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _ensure_sqlite_dir(database_url: str) -> None:
    """对 sqlite 路径创建父目录。"""
    if not database_url.startswith("sqlite"):
        return
    # 兼容 sqlite:///./data/xxx.db 与 sqlite:////abs/path.db
    rest = database_url.split("sqlite:///", 1)[-1]
    if not rest:
        return
    path = Path(rest)
    path.parent.mkdir(parents=True, exist_ok=True)


def _build_engine() -> Engine:
    settings = get_settings()
    _ensure_sqlite_dir(settings.database_url)
    connect_args: dict = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(
        settings.database_url,
        connect_args=connect_args,
        future=True,
    )


engine: Engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI 依赖:每个请求一个 Session,结束自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
