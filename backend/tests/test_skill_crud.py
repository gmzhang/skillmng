"""Skill CRUD + 文件操作 + 跨租户隔离测试 (PRD §17.1)。"""
from __future__ import annotations


def _create(client, name: str = "demo-skill", description: str = "示例 Skill,用于演示创建流程,触发关键词:demo。"):
    return client.post(
        "/api/skills",
        json={"name": name, "description": description},
    )


def test_create_and_get_skill(alice_client):
    resp = _create(alice_client)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "demo-skill"
    assert body["status"] == "draft"
    sid = body["id"]

    resp2 = alice_client.get(f"/api/skills/{sid}")
    assert resp2.status_code == 200


def test_invalid_name_rejected(alice_client):
    resp = alice_client.post("/api/skills", json={"name": "BAD", "description": "x" * 80})
    assert resp.status_code in (422, 400)


def test_duplicate_name_conflict(alice_client):
    _create(alice_client)
    resp = _create(alice_client)
    assert resp.status_code == 409


def test_cross_tenant_isolation(alice_client, bob_client):
    """Alice 创建的 Skill,Bob 看不到也访问不到。"""
    resp = _create(alice_client, name="alice-only")
    sid = resp.json()["id"]

    listed = bob_client.get("/api/skills").json()
    assert all(s["id"] != sid for s in listed)

    resp2 = bob_client.get(f"/api/skills/{sid}")
    assert resp2.status_code == 404

    resp3 = bob_client.delete(f"/api/skills/{sid}")
    assert resp3.status_code == 404


def test_skill_md_auto_created(alice_client):
    sid = _create(alice_client, name="auto-md").json()["id"]
    files = alice_client.get(f"/api/skills/{sid}/files").json()
    paths = [f["path"] for f in files]
    assert "SKILL.md" in paths


def test_write_and_read_file(alice_client):
    sid = _create(alice_client, name="write-read").json()["id"]
    resp = alice_client.put(
        f"/api/skills/{sid}/files/content",
        json={"path": "scripts/run.sh", "content": "#!/usr/bin/env bash\necho hello\n"},
    )
    assert resp.status_code == 200, resp.text
    resp2 = alice_client.get(f"/api/skills/{sid}/files/content?path=scripts/run.sh")
    assert resp2.status_code == 200
    assert "hello" in resp2.json()["content"]


def test_dotdot_path_rejected_via_api(alice_client):
    sid = _create(alice_client, name="path-safe").json()["id"]
    resp = alice_client.put(
        f"/api/skills/{sid}/files/content",
        json={"path": "../evil.txt", "content": "x"},
    )
    assert resp.status_code == 422


def test_delete_skill_md_forbidden(alice_client):
    sid = _create(alice_client, name="md-protect").json()["id"]
    resp = alice_client.delete(f"/api/skills/{sid}/files/content?path=SKILL.md")
    assert resp.status_code == 422


def test_soft_delete_keeps_record(alice_client):
    sid = _create(alice_client, name="soft-delete").json()["id"]
    resp = alice_client.delete(f"/api/skills/{sid}")
    assert resp.status_code == 204
    # 详情仍可读(软删除),但 status 变更
    resp2 = alice_client.get(f"/api/skills/{sid}")
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "deleted"


def test_repository_bind(alice_client):
    sid = _create(alice_client, name="bind-repo").json()["id"]
    resp = alice_client.patch(
        f"/api/skills/{sid}/repository",
        json={"git_remote_url": "git@code.example.com:group/x.git"},
    )
    assert resp.status_code == 200
    assert resp.json()["git_remote_url"] == "git@code.example.com:group/x.git"
