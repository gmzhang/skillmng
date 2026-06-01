"""租户隔离最小测试 (PRD §17.1.10)。"""
from __future__ import annotations


def test_missing_cookie_returns_401(client):
    """没有 Cookie 时 /api/me 必须 401。"""
    resp = client.get("/api/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "unauthorized"


def test_alice_sees_alice(alice_client):
    resp = alice_client.get("/api/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == "alice"
    assert body["user_name"] == "Alice"
    assert body["user_email"] == "alice@example.com"


def test_bob_sees_bob(bob_client):
    resp = bob_client.get("/api/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == "bob"
    assert body["user_name"] == "Bob"


def test_body_user_id_is_ignored(alice_client):
    """前端传 body/query 中的 user_id 不能影响租户。"""
    resp = alice_client.get("/api/me?user_id=bob")
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "alice"
