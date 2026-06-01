"""PRD7 端到端实测问题修复 — 后端测试。

覆盖 §9.1:
1. sync_from_remote 不污染 default_branch
2. 已污染数据自动修复
3. AntCode workflow 两版本 diff
4. diff 异常结构化错误
5. resolve_publish_branch 始终返回 master
"""
from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from git import Repo
from sqlalchemy import select

from app.models.skill import Skill


# ---- fixtures ----


@pytest.fixture()
def _fake_antcode_configured():
    with patch("app.services.antcode_client.is_configured", return_value=True):
        yield


@pytest.fixture()
def bare_remote(tmp_path: Path):
    bare_dir = tmp_path / "remote.git"
    Repo.init(bare_dir, bare=True)
    return bare_dir


@pytest.fixture()
def skill_with_repo(alice_client, bare_remote, db_session, _fake_antcode_configured):
    """创建 Skill 并绑定到 bare remote。"""
    import secrets

    name = f"prd7-{secrets.token_hex(3)}"
    resp = alice_client.post(
        "/api/skills",
        json={"name": name, "description": f"PRD7 test. trigger: {name}"},
    )
    assert resp.status_code == 201, resp.text
    skill = resp.json()
    sid = skill["id"]

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


# ---- §9.1.1: sync 不污染 default_branch ----


def test_apply_project_rejects_draft_default_branch(db_session, _fake_antcode_configured):
    """_apply_project_to_skill 对 draft/ 开头的 default_branch 保留 master。"""
    from app.services.antcode_skill_service import _apply_project_to_skill
    from app.services.antcode_client import AntCodeProject

    skill = Skill(
        name="test-branch-reject",
        description="test",
        user_id="alice",
        default_branch="master",
    )
    db_session.add(skill)
    db_session.commit()

    project = AntCodeProject(
        id=12345,
        name="test-branch-reject",
        path="test-branch-reject",
        path_with_namespace="test/test-branch-reject",
        http_url_to_repo="https://code.example.com/test/test-branch-reject.git",
        ssh_url_to_repo="",
        web_url="https://code.example.com/test/test-branch-reject",
        default_branch="draft/alice/test-branch-reject",
        raw={},
    )

    _apply_project_to_skill(db_session, skill, project)
    assert skill.default_branch == "master"


def test_apply_project_empty_default_branch(db_session, _fake_antcode_configured):
    """_apply_project_to_skill 对空 default_branch 使用 settings 默认值。"""
    from app.services.antcode_skill_service import _apply_project_to_skill
    from app.services.antcode_client import AntCodeProject

    skill = Skill(
        name="test-empty-branch",
        description="test",
        user_id="alice",
        default_branch="master",
    )
    db_session.add(skill)
    db_session.commit()

    project = AntCodeProject(
        id=12346,
        name="test-empty-branch",
        path="test-empty-branch",
        path_with_namespace="test/test-empty-branch",
        http_url_to_repo="https://code.example.com/test/test-empty-branch.git",
        ssh_url_to_repo="",
        web_url="https://code.example.com/test/test-empty-branch",
        default_branch="",
        raw={},
    )

    _apply_project_to_skill(db_session, skill, project)
    assert skill.default_branch == "master"


# ---- §9.1.2: 已污染数据修复 ----


def test_polluted_default_branch_auto_fixed(db_session, _fake_antcode_configured):
    """_apply_project_to_skill 修复已被污染成 draft/ 的 default_branch。"""
    from app.services.antcode_skill_service import _apply_project_to_skill
    from app.services.antcode_client import AntCodeProject

    skill = Skill(
        name="test-polluted",
        description="test",
        user_id="alice",
        default_branch="draft/alice/test-polluted",
    )
    db_session.add(skill)
    db_session.commit()

    project = AntCodeProject(
        id=12347,
        name="test-polluted",
        path="test-polluted",
        path_with_namespace="test/test-polluted",
        http_url_to_repo="https://code.example.com/test/test-polluted.git",
        ssh_url_to_repo="",
        web_url="https://code.example.com/test/test-polluted",
        default_branch="main",
        raw={},
    )

    _apply_project_to_skill(db_session, skill, project)
    assert skill.default_branch == "main"


# ---- §9.1.5: resolve_publish_branch ----


def test_resolve_publish_branch_always_master():
    from app.services.antcode_skill_service import resolve_publish_branch

    skill = MagicMock(spec=Skill)
    skill.default_branch = "draft/alice/test"
    assert resolve_publish_branch(skill) == "master"

    assert resolve_publish_branch(None) == "master"
    assert resolve_publish_branch() == "master"


# ---- §9.1.3: AntCode workflow 两版本 diff ----


def test_two_version_diff(alice_client, skill_with_repo, bare_remote, _fake_antcode_configured):
    """发布两个版本后,diff API 返回 SKILL.md modified。"""
    sid = skill_with_repo["id"]

    # 首次发布
    resp = alice_client.post(
        f"/api/skills/{sid}/drafts/commit",
        json={"summary": "v0.1.0 draft"},
    )
    assert resp.status_code == 200, resp.text

    resp = alice_client.post(
        f"/api/skills/{sid}/publish",
        json={"version": "0.1.0", "summary": "first", "change_type": "patch"},
    )
    assert resp.status_code == 201, resp.text
    v1 = resp.json()

    # 修改 SKILL.md
    resp_update = alice_client.put(
        f"/api/skills/{sid}/files/content",
        json={
            "path": "SKILL.md",
            "content": (
                "---\nname: " + skill_with_repo["name"] + "\n"
                "description: \"updated for v0.1.1\"\n---\n\n# Updated\n\nnew content for v0.1.1\n"
            ),
        },
    )
    assert resp_update.status_code == 200, resp_update.text

    # 二次发布
    alice_client.post(
        f"/api/skills/{sid}/drafts/commit",
        json={"summary": "v0.1.1 draft"},
    )
    resp = alice_client.post(
        f"/api/skills/{sid}/publish",
        json={"version": "0.1.1", "summary": "update", "change_type": "patch"},
    )
    assert resp.status_code == 201, resp.text
    v2 = resp.json()

    # diff
    resp = alice_client.get(
        f"/api/skills/{sid}/diff",
        params={"from_version_id": v1["id"], "to_version_id": v2["id"]},
    )
    assert resp.status_code == 200, resp.text
    diff = resp.json()
    paths = [f["path"] for f in diff["files"]]
    assert "SKILL.md" in paths
    skill_md_entry = next(f for f in diff["files"] if f["path"] == "SKILL.md")
    assert skill_md_entry["change"] == "modified"


# ---- §9.1.4: diff 异常结构化错误 ----


def test_diff_missing_commit_returns_structured_error(
    alice_client, skill_with_repo, bare_remote, db_session, _fake_antcode_configured
):
    """diff 中 commit 不存在时返回结构化业务错误,不是裸 500。"""
    sid = skill_with_repo["id"]

    # 发布一个版本先
    alice_client.post(
        f"/api/skills/{sid}/drafts/commit",
        json={"summary": "draft"},
    )
    resp = alice_client.post(
        f"/api/skills/{sid}/publish",
        json={"version": "0.1.0", "summary": "first", "change_type": "patch"},
    )
    assert resp.status_code == 201
    v1 = resp.json()

    # 创建一个假版本记录,使用不存在的 commit SHA
    from app.models.skill_version import SkillVersion

    fake_version = SkillVersion(
        skill_id=sid,
        user_id="alice",
        version="0.0.0",
        change_type="patch",
        summary="fake",
        git_commit_sha="0000000000000000000000000000000000000000",
        git_tag="v0.0.0",
        author_name="test",
        author_email="test@test.com",
    )
    db_session.add(fake_version)
    db_session.commit()
    db_session.refresh(fake_version)

    resp = alice_client.get(
        f"/api/skills/{sid}/diff",
        params={"from_version_id": fake_version.id, "to_version_id": v1["id"]},
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["code"] == "git_diff_failed"
    assert "diff" in body["message"].lower() or "失败" in body["message"]


def test_diff_legacy_versions_still_works(alice_client, _fake_antcode_configured):
    """Legacy /versions 发布的版本仍可 diff (不绑定 AntCode)。"""
    import secrets

    name = f"legacy-{secrets.token_hex(3)}"
    resp = alice_client.post(
        "/api/skills",
        json={"name": name, "description": f"legacy test. trigger: {name}"},
    )
    assert resp.status_code == 201
    sid = resp.json()["id"]

    # 写入 SKILL.md
    resp = alice_client.put(
        f"/api/skills/{sid}/files/content",
        json={
            "path": "SKILL.md",
            "content": f"---\nname: {name}\ndescription: \"legacy test\"\n---\n\n# Initial\n\ncontent\n",
        },
    )
    assert resp.status_code == 200, resp.text

    # Legacy publish v1
    resp = alice_client.post(
        f"/api/skills/{sid}/versions",
        json={"version": "0.1.0", "summary": "v1", "change_type": "patch"},
    )
    assert resp.status_code == 201
    v1 = resp.json()

    # Modify and publish v2
    resp = alice_client.put(
        f"/api/skills/{sid}/files/content",
        json={
            "path": "SKILL.md",
            "content": f"---\nname: {name}\ndescription: \"updated legacy\"\n---\n\n# Updated\n\nnew\n",
        },
    )
    assert resp.status_code == 200, resp.text
    resp = alice_client.post(
        f"/api/skills/{sid}/versions",
        json={"version": "0.1.1", "summary": "v2", "change_type": "patch"},
    )
    assert resp.status_code == 201
    v2 = resp.json()

    # diff should work
    resp = alice_client.get(
        f"/api/skills/{sid}/diff",
        params={"from_version_id": v1["id"], "to_version_id": v2["id"]},
    )
    assert resp.status_code == 200, resp.text
    diff = resp.json()
    paths = [f["path"] for f in diff["files"]]
    assert "SKILL.md" in paths
