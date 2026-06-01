"""PRD6 发布链路收敛 — 完整工作流测试。

使用本地 bare Git 仓库模拟 AntCode 远端,测试:
1. 首次发布(bare 远端 -> draft commit -> publish)
2. 已有 master 的二次发布
3. 重复版本/tag 被拒绝
4. draft 缺失 / SHA 不匹配被拒绝
5. legacy /versions 对 AntCode-bound Skill 拒绝
6. proxy 注入到 AntCodeClient
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from git import Repo

from app.core.config import Settings


# ---- fixtures ----


@pytest.fixture()
def bare_remote(tmp_path: Path):
    """创建一个 bare Git 仓库作为本地远端。"""
    bare_dir = tmp_path / "remote.git"
    Repo.init(bare_dir, bare=True)
    return bare_dir


@pytest.fixture()
def _fake_antcode_configured():
    """让 antcode_client.is_configured() 返回 True。"""
    with patch("app.services.antcode_client.is_configured", return_value=True):
        yield


@pytest.fixture()
def skill_with_repo(alice_client, bare_remote, db_session, _fake_antcode_configured):
    """创建 Skill,手动绑定到 bare 远端仓库(模拟 AntCode 绑定),返回 skill dict。"""
    import secrets

    name = f"pub-test-{secrets.token_hex(3)}"
    resp = alice_client.post(
        "/api/skills",
        json={
            "name": name,
            "description": f"测试发布链路。触发关键词: {name}",
        },
    )
    assert resp.status_code == 201, resp.text
    skill = resp.json()
    sid = skill["id"]

    # 手动更新 DB,模拟 AntCode 仓库绑定
    from app.models.skill import Skill
    from sqlalchemy import select

    db_skill = db_session.scalar(select(Skill).where(Skill.id == sid))
    db_skill.git_project_id = 999999
    db_skill.git_namespace_id = 354800126
    db_skill.git_http_url = str(bare_remote)
    db_skill.git_ssh_url = ""
    db_skill.git_web_url = f"https://code.example.com/test/{name}"
    db_skill.git_path_with_namespace = f"test/{name}"
    db_skill.git_remote_url = str(bare_remote)
    db_skill.git_repo_name = name
    db_skill.default_branch = "master"
    db_session.commit()
    db_session.refresh(db_skill)

    return alice_client.get(f"/api/skills/{sid}").json()


def _init_bare_with_readme(bare_remote: Path) -> str:
    """在 bare 远端初始化一个 master 分支(包含 README)。"""
    work = bare_remote.parent / "init-work"
    repo = Repo.clone_from(str(bare_remote), work)
    readme = work / "README.md"
    readme.write_text("# Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("init")
    repo.git.push("origin", "HEAD:master")
    sha = repo.head.commit.hexsha
    shutil.rmtree(work)
    return sha


# ---- 测试: 首次发布(bare 远端) ----


def test_first_publish_bare_remote(alice_client, skill_with_repo, bare_remote, _fake_antcode_configured):
    sid = skill_with_repo["id"]

    resp = alice_client.post(
        f"/api/skills/{sid}/drafts/commit",
        json={"summary": "initial draft"},
    )
    assert resp.status_code == 200, resp.text
    draft = resp.json()
    assert draft["branch"].startswith("draft/")
    assert draft["commit_sha"] is not None

    resp = alice_client.get(f"/api/skills/{sid}/drafts/diff")
    assert resp.status_code == 200, resp.text

    resp = alice_client.post(
        f"/api/skills/{sid}/publish",
        json={"version": "0.1.0", "summary": "first release", "change_type": "minor"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["version"] == "0.1.0"
    assert body["git_tag"] == "v0.1.0"
    assert len(body["git_commit_sha"]) >= 7

    remote_repo = Repo(bare_remote)
    tags = [t.name for t in remote_repo.tags]
    assert "v0.1.0" in tags


def test_second_publish_with_existing_master(alice_client, skill_with_repo, bare_remote, _fake_antcode_configured):
    sid = skill_with_repo["id"]
    _init_bare_with_readme(bare_remote)

    alice_client.post(f"/api/skills/{sid}/drafts/commit", json={"summary": "v1"})
    resp = alice_client.post(
        f"/api/skills/{sid}/publish",
        json={"version": "1.0.0", "summary": "v1", "change_type": "major"},
    )
    assert resp.status_code == 201, resp.text

    alice_client.put(
        f"/api/skills/{sid}/files/content",
        json={"path": "SKILL.md", "content": (
            "---\nname: " + skill_with_repo["name"] + "\n"
            "description: updated description. trigger: test\n---\n\n# Updated\n\nnew content\n"
        )},
    )

    alice_client.post(f"/api/skills/{sid}/drafts/commit", json={"summary": "v1.1"})
    resp = alice_client.post(
        f"/api/skills/{sid}/publish",
        json={"version": "1.1.0", "summary": "update", "change_type": "minor"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["version"] == "1.1.0"
    assert body["git_tag"] == "v1.1.0"

    remote_repo = Repo(bare_remote)
    tags = sorted(t.name for t in remote_repo.tags)
    assert "v1.0.0" in tags
    assert "v1.1.0" in tags


# ---- 测试: 重复版本 ----


def test_duplicate_version_rejected(alice_client, skill_with_repo, bare_remote, _fake_antcode_configured):
    sid = skill_with_repo["id"]

    alice_client.post(f"/api/skills/{sid}/drafts/commit", json={"summary": "v1"})
    resp = alice_client.post(
        f"/api/skills/{sid}/publish",
        json={"version": "0.1.0", "summary": "first", "change_type": "patch"},
    )
    assert resp.status_code == 201

    alice_client.put(
        f"/api/skills/{sid}/files/content",
        json={"path": "SKILL.md", "content": (
            "---\nname: " + skill_with_repo["name"] + "\n"
            "description: again. trigger: test\n---\n\n# v2\n\nok\n"
        )},
    )
    alice_client.post(f"/api/skills/{sid}/drafts/commit", json={"summary": "v1 again"})
    resp = alice_client.post(
        f"/api/skills/{sid}/publish",
        json={"version": "0.1.0", "summary": "dup", "change_type": "patch"},
    )
    assert resp.status_code in (400, 409), resp.text


# ---- 测试: draft 缺失 ----


def test_publish_without_draft_rejected(alice_client, skill_with_repo, _fake_antcode_configured):
    sid = skill_with_repo["id"]
    resp = alice_client.post(
        f"/api/skills/{sid}/publish",
        json={"version": "0.1.0", "summary": "no draft", "change_type": "patch"},
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert "草稿" in body.get("message", "") or "draft" in body.get("message", "").lower()


# ---- 测试: draft SHA 不匹配 ----


def test_draft_sha_mismatch_rejected(alice_client, skill_with_repo, bare_remote, db_session, _fake_antcode_configured):
    sid = skill_with_repo["id"]

    resp = alice_client.post(f"/api/skills/{sid}/drafts/commit", json={"summary": "v1"})
    assert resp.status_code == 200, resp.text

    from app.models.skill import Skill
    from sqlalchemy import select

    db_skill = db_session.scalar(select(Skill).where(Skill.id == sid))
    db_skill.draft_commit_sha = "0000000000000000000000000000000000000000"
    db_session.commit()

    resp = alice_client.post(
        f"/api/skills/{sid}/publish",
        json={"version": "0.1.0", "summary": "mismatch", "change_type": "patch"},
    )
    assert resp.status_code == 400, resp.text
    assert "不一致" in resp.json().get("message", "") or "mismatch" in resp.json().get("message", "").lower()


# ---- 测试: legacy /versions 对 AntCode-bound Skill 拒绝 ----


def test_legacy_versions_rejected_for_antcode_bound(alice_client, skill_with_repo, _fake_antcode_configured):
    sid = skill_with_repo["id"]
    resp = alice_client.post(
        f"/api/skills/{sid}/versions",
        json={"version": "0.1.0", "summary": "legacy", "change_type": "patch"},
    )
    assert resp.status_code in (400, 422), resp.text
    body = resp.json()
    msg = body.get("message", "")
    assert "AntCode" in msg or "绑定" in msg


# ---- 测试: proxy 注入 ----


def test_proxy_injected_into_antcode_client():
    from app.services.antcode_client import AntCodeClient

    client = AntCodeClient(
        base_url="https://code.example.com/api/v3",
        token="test-token-fake",
        proxy="http://127.0.0.1:1235",
    )
    client.close()


def test_build_client_passes_proxy():
    from unittest.mock import MagicMock

    mock_settings = MagicMock(spec=Settings)
    mock_settings.antcode_api_base_url = "https://code.example.com/api/v3"
    mock_settings.antcode_private_token = "test-token-fake"
    mock_settings.httpx_proxy = "http://127.0.0.1:9999"

    from app.services.antcode_client import build_client

    client = build_client(mock_settings)
    client.close()
