"""pytest 全局 fixture。

每次测试用临时 sqlite 与临时 git workdir,避免污染 ./data。
通过 monkeypatch 在 import app 之前覆盖环境变量,使 Settings 与 engine 使用临时位置。
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _patch_env(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """会话级:把数据库与 Git workdir 重定向到临时目录。"""
    tmp_root: Path = tmp_path_factory.mktemp("skillmng")
    db_file = tmp_root / "test.sqlite3"
    git_dir = tmp_root / "git"
    git_dir.mkdir(parents=True, exist_ok=True)

    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    os.environ["SKILL_GIT_WORKDIR"] = str(git_dir)
    os.environ["APP_ENV"] = "test"
    os.environ["LLM_PROVIDER"] = "mock"
    # 测试必须显式带 cookie,关闭 mock 兜底
    os.environ["MOCK_USER_ID"] = ""
    os.environ["MOCK_USER_NAME"] = ""
    os.environ["MOCK_USER_EMAIL"] = ""
    # 测试不走 AntCode API 和代理
    os.environ["ANTCODE_PRIVATE_TOKEN"] = ""
    for key in ("https_proxy", "http_proxy", "all_proxy", "HTTPS_PROXY", "HTTP_PROXY"):
        os.environ.pop(key, None)

    # 清空 Settings 缓存,避免被仓库根 .env 中的真实值锁定
    from app.core.config import get_settings as _gs

    _gs.cache_clear()

    yield


@pytest.fixture(scope="session")
def _engine(_patch_env):
    """初始化全部表(等价 alembic upgrade head)。"""
    from app.db.base import Base
    from app.db.session import engine
    from app import models  # noqa: F401  确保模型注册到 metadata

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def app(_engine):
    """每个测试拿到一个干净 FastAPI app。"""
    from app.main import create_app

    return create_app()


@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def alice_client(client):
    """带 Cookie alice 的客户端。"""
    client.cookies.set("user_id", "alice")
    client.cookies.set("user_name", "Alice")
    client.cookies.set("user_email", "alice@example.com")
    yield client


@pytest.fixture()
def bob_client(app):
    """另一个独立 TestClient,带 Cookie bob,用于跨租户测试。"""
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        c.cookies.set("user_id", "bob")
        c.cookies.set("user_name", "Bob")
        yield c


@pytest.fixture()
def db_session(_engine):
    """裸 Session,供需要直接操作 ORM 的测试用。"""
    from app.db.session import SessionLocal

    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
