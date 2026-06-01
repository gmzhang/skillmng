"""Git 版本管理端到端测试 (PRD §17.1.5/6/7/8)。

不绑 remote,纯本地仓库测全闭环。
"""
from __future__ import annotations


def _create(client, name: str = "git-skill"):
    return client.post(
        "/api/skills",
        json={
            "name": name,
            "description": "演示 Git 版本管理。当用户提交版本时使用,触发关键词:demo。",
        },
    )


def test_publish_creates_commit(alice_client):
    sid = _create(alice_client, name="git-publish").json()["id"]
    resp = alice_client.post(
        f"/api/skills/{sid}/versions",
        json={"version": "0.1.0", "summary": "first release", "change_type": "minor"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["version"] == "0.1.0"
    assert len(body["git_commit_sha"]) >= 7

    # 列表能看到
    listed = alice_client.get(f"/api/skills/{sid}/versions").json()
    assert len(listed) == 1


def test_two_versions_diff(alice_client):
    sid = _create(alice_client, name="git-diff").json()["id"]
    v1 = alice_client.post(
        f"/api/skills/{sid}/versions",
        json={"version": "0.1.0", "summary": "v1", "change_type": "minor"},
    ).json()
    # 改 SKILL.md
    files = alice_client.get(f"/api/skills/{sid}/files").json()
    md_path = next(f["path"] for f in files if f["path"] == "SKILL.md")
    cur = alice_client.get(
        f"/api/skills/{sid}/files/content", params={"path": md_path}
    ).json()
    new_content = cur["content"] + "\n\n## 新增章节\n\n更新后的内容\n"
    alice_client.put(
        f"/api/skills/{sid}/files/content",
        json={"path": "SKILL.md", "content": new_content},
    )
    v2 = alice_client.post(
        f"/api/skills/{sid}/versions",
        json={"version": "0.1.1", "summary": "v2", "change_type": "patch"},
    ).json()

    assert v1["git_commit_sha"] != v2["git_commit_sha"]

    diff = alice_client.get(
        f"/api/skills/{sid}/diff",
        params={"from_version_id": v1["id"], "to_version_id": v2["id"]},
    )
    assert diff.status_code == 200
    body = diff.json()
    paths = [e["path"] for e in body["files"]]
    assert "SKILL.md" in paths
    md_entry = next(e for e in body["files"] if e["path"] == "SKILL.md")
    assert md_entry["change"] == "modified"
    assert "新增章节" in md_entry["after"]


def test_restore_creates_new_commit(alice_client):
    sid = _create(alice_client, name="git-restore").json()["id"]
    v1 = alice_client.post(
        f"/api/skills/{sid}/versions",
        json={"version": "0.1.0", "summary": "v1", "change_type": "minor"},
    ).json()
    # 改 + 发 v2
    cur = alice_client.get(
        f"/api/skills/{sid}/files/content", params={"path": "SKILL.md"}
    ).json()
    alice_client.put(
        f"/api/skills/{sid}/files/content",
        json={"path": "SKILL.md", "content": cur["content"] + "\n\n## v2\n"},
    )
    v2 = alice_client.post(
        f"/api/skills/{sid}/versions",
        json={"version": "0.1.1", "summary": "v2", "change_type": "patch"},
    ).json()

    # 恢复 v1
    restore = alice_client.post(
        f"/api/skills/{sid}/versions/{v1['id']}/restore",
        json={"new_version": "0.1.2", "summary": "restore v1"},
    )
    assert restore.status_code == 200, restore.text
    v3 = restore.json()
    assert v3["version"] == "0.1.2"
    assert v3["git_commit_sha"] not in {v1["git_commit_sha"], v2["git_commit_sha"]}

    # v3 内容应该等于 v1 内容
    diff = alice_client.get(
        f"/api/skills/{sid}/diff",
        params={"from_version_id": v1["id"], "to_version_id": v3["id"]},
    ).json()
    assert diff["files"] == []


def test_invalid_semver_rejected(alice_client):
    sid = _create(alice_client, name="bad-semver").json()["id"]
    resp = alice_client.post(
        f"/api/skills/{sid}/versions",
        json={"version": "abc", "summary": "x", "change_type": "patch"},
    )
    assert resp.status_code in (400, 422)


def test_duplicate_version_rejected(alice_client):
    sid = _create(alice_client, name="dup-version").json()["id"]
    alice_client.post(
        f"/api/skills/{sid}/versions",
        json={"version": "0.1.0", "summary": "x", "change_type": "patch"},
    )
    resp = alice_client.post(
        f"/api/skills/{sid}/versions",
        json={"version": "0.1.0", "summary": "y", "change_type": "patch"},
    )
    assert resp.status_code == 409


def test_cross_tenant_versions_forbidden(alice_client, bob_client):
    sid = _create(alice_client, name="alice-versions").json()["id"]
    alice_client.post(
        f"/api/skills/{sid}/versions",
        json={"version": "0.1.0", "summary": "x", "change_type": "patch"},
    )
    resp = bob_client.get(f"/api/skills/{sid}/versions")
    assert resp.status_code == 404
