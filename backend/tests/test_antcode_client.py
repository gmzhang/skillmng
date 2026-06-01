"""AntCode client 单元测试(mock httpx)。"""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from app.services import antcode_client
from app.services.antcode_client import AntCodeClient, AntCodeError, mask_token


def _make_client_with_transport(transport: httpx.MockTransport) -> AntCodeClient:
    c = AntCodeClient(base_url="https://example.test/api/v3", token="t0kEnSecret")
    c._client.close()
    c._client = httpx.Client(
        base_url="https://example.test/api/v3",
        timeout=5.0,
        headers={"PRIVATE-TOKEN": "t0kEnSecret"},
        transport=transport,
    )
    return c


def test_mask_token_short_and_long():
    assert mask_token("") == ""
    assert mask_token("abc") == "***"
    assert mask_token("abcdefghij") == "abc***hij"


def test_create_project_posts_to_v3_trailing_slash():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = request.read().decode()
        return httpx.Response(
            201,
            json={
                "id": 42,
                "name": "demo",
                "path": "demo",
                "path_with_namespace": "xiaojin-skills/demo",
                "http_url_to_repo": "https://example.test/xiaojin-skills/demo.git",
                "ssh_url_to_repo": "git@example.test:t/xiaojin-skills/demo.git",
                "web_url": "https://example.test/xiaojin-skills/demo",
                "default_branch": "master",
            },
        )

    transport = httpx.MockTransport(handler)
    with _make_client_with_transport(transport) as c:
        project = c.create_project(
            name="demo", path="demo", namespace_id=354800126
        )

    assert captured["method"] == "POST"
    # 路径必须以 /projects/ 结尾(尾斜杠)— PRD2/antcode-guide §5.1
    assert captured["url"].endswith("/projects/")
    assert '"namespace_id":354800126' in captured["body"].replace(" ", "")
    assert project.id == 42
    assert project.path_with_namespace == "xiaojin-skills/demo"


def test_create_branch_uses_branch_name_param():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.read().decode()
        return httpx.Response(
            201, json={"name": "draft/alice/x", "commit": {"id": "abc123"}}
        )

    transport = httpx.MockTransport(handler)
    with _make_client_with_transport(transport) as c:
        branch = c.create_branch(7, branch_name="draft/alice/x", ref="master")

    # AntCode 用 branch_name(不是 branch)
    assert '"branch_name"' in captured["body"]
    assert '"branch"' not in captured["body"].replace('"branch_name"', "")
    assert branch.name == "draft/alice/x"
    assert branch.commit_sha == "abc123"


def test_get_branch_404_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "404 Branch Not Found"})

    transport = httpx.MockTransport(handler)
    with _make_client_with_transport(transport) as c:
        assert c.get_branch(7, "nope") is None


def test_error_status_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    transport = httpx.MockTransport(handler)
    with _make_client_with_transport(transport) as c:
        with pytest.raises(AntCodeError):
            c.get_user()


def test_token_missing_raises_business_error():
    with patch.object(
        antcode_client, "get_settings", return_value=type("S", (), {"antcode_private_token": "", "antcode_api_base_url": "x"})()
    ):
        with pytest.raises(Exception):
            antcode_client.build_client()
