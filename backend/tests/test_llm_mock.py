"""LLM Mock 端到端测试。"""
from __future__ import annotations

import pytest

from app.workers import llm_worker


@pytest.fixture(autouse=True)
def _sync_worker():
    llm_worker.set_sync_for_test(True)
    yield
    llm_worker.set_sync_for_test(False)


def test_create_job_and_apply(alice_client):
    resp = alice_client.post(
        "/api/llm/skill-drafts",
        json={
            "skill_name": "llm-draft",
            "description": "由 LLM 辅助创建的演示 Skill,触发关键词:demo。",
            "goal": "把一段日志摘要为关键事件。",
            "scenario": "用户提供原始日志后",
            "trigger": "summarize, log",
            "include_scripts": True,
            "include_references": True,
        },
    )
    assert resp.status_code == 202, resp.text
    job_id = resp.json()["id"]

    detail = alice_client.get(f"/api/llm/jobs/{job_id}").json()
    assert detail["status"] == "succeeded", detail
    payload = detail["output_payload"]
    assert payload["skill_md"].startswith("---")
    assert any(f["path"] == "scripts/run.sh" for f in payload["files"])

    # apply 落地
    apply_resp = alice_client.post(f"/api/llm/jobs/{job_id}/apply")
    assert apply_resp.status_code == 200, apply_resp.text
    skill_id = apply_resp.json()["skill_id"]

    files = alice_client.get(f"/api/skills/{skill_id}/files").json()
    paths = {f["path"] for f in files}
    assert "SKILL.md" in paths
    assert "scripts/run.sh" in paths
    assert "references/notes.md" in paths


def test_update_job_and_apply(alice_client):
    # 先建 Skill
    sid = (
        alice_client.post(
            "/api/skills",
            json={
                "name": "llm-update",
                "description": "演示 LLM 辅助更新,触发关键词:update demo。",
            },
        )
        .json()["id"]
    )
    # 提交 update 任务
    resp = alice_client.post(
        "/api/llm/skill-updates",
        json={
            "skill_id": sid,
            "goal": "在 SKILL.md 末尾补充输入校验小节",
        },
    )
    assert resp.status_code == 202, resp.text
    job_id = resp.json()["id"]
    detail = alice_client.get(f"/api/llm/jobs/{job_id}").json()
    assert detail["status"] == "succeeded"

    # apply
    apply_resp = alice_client.post(f"/api/llm/jobs/{job_id}/apply")
    assert apply_resp.status_code == 200
    paths = apply_resp.json()["applied_paths"]
    assert "SKILL.md" in paths
    assert "references/changelog.md" in paths

    # 验证 SKILL.md 真的被改了
    md = alice_client.get(
        f"/api/skills/{sid}/files/content", params={"path": "SKILL.md"}
    ).json()
    assert "输入校验" in md["content"]


def test_job_isolation(alice_client, bob_client):
    sid = alice_client.post(
        "/api/skills",
        json={"name": "alice-llm", "description": "演示触发关键词:demo。"},
    ).json()["id"]
    alice_client.post(
        "/api/llm/skill-updates",
        json={"skill_id": sid, "goal": "x"},
    )
    listed_alice = alice_client.get("/api/llm/jobs").json()
    listed_bob = bob_client.get("/api/llm/jobs").json()
    assert len(listed_alice) >= 1
    assert listed_bob == []


def test_cancel_terminal_job_rejected(alice_client):
    resp = alice_client.post(
        "/api/llm/skill-drafts",
        json={
            "skill_name": "no-cancel",
            "description": "演示无法取消已成功任务,触发关键词:demo。",
            "goal": "g",
        },
    ).json()
    job_id = resp["id"]
    # 同步模式下任务已成功,cancel 应被拒
    cancel = alice_client.post(f"/api/llm/jobs/{job_id}/cancel")
    assert cancel.status_code in (400, 409)
