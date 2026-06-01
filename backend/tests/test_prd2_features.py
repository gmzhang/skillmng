"""设置页 + 工作台统计 API 测试 (PRD2 §4.4 / §2.1)。"""
from __future__ import annotations


def test_settings_returns_token_status(alice_client):
    resp = alice_client.get("/api/settings")
    assert resp.status_code == 200
    body = resp.json()
    # git token 掩码仍存在
    assert "antcode_token_mask" in body["git"]
    mask = body["git"]["antcode_token_mask"]
    if body["git"]["antcode_token_status"] == "configured":
        assert "***" in mask
    # llm token 只返回 boolean,不返回掩码 (PRD3 §3.7)
    assert "token_configured" in body["llm"]
    assert isinstance(body["llm"]["token_configured"], bool)
    assert "token_mask" not in body["llm"]
    # 限制字段非零
    assert body["limits"]["max_upload_bytes"] > 0


def test_settings_reload(alice_client):
    resp = alice_client.post("/api/settings/reload")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_test_llm_mock_provider(alice_client):
    resp = alice_client.post("/api/settings/test-llm")
    assert resp.status_code == 200
    body = resp.json()
    # 测试环境 LLM_PROVIDER=mock
    assert body["ok"] is True
    assert body["detail"]["provider"] == "mock"


def test_workbench_stats(alice_client):
    # 先建 1 个 Skill
    alice_client.post(
        "/api/skills",
        json={
            "name": "stats-skill",
            "description": "演示工作台统计,触发关键词:stats,使用场景:测试。",
        },
    )
    resp = alice_client.get("/api/workbench/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["skill_total"] >= 1
    assert body["skill_draft"] >= 1
    assert isinstance(body["recent_skills"], list)
    assert isinstance(body["recent_audits"], list)


def test_audit_includes_action_label_and_skill_name(alice_client):
    sid = alice_client.post(
        "/api/skills",
        json={
            "name": "audit-enrich",
            "description": "演示审计扩展,触发关键词:audit,使用场景:测试。",
        },
    ).json()["id"]
    resp = alice_client.get("/api/audit-logs", params={"skill_id": sid})
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    first = items[0]
    assert first["skill_name"] == "audit-enrich"
    assert first["action_label"]  # 非空


def test_llm_job_includes_patches_and_skill_name(alice_client):
    from app.workers import llm_worker

    llm_worker.set_sync_for_test(True)
    try:
        sid = alice_client.post(
            "/api/skills",
            json={
                "name": "llm-dto",
                "description": "演示 LLM DTO 扩展,触发关键词:dto,使用场景:测试。",
            },
        ).json()["id"]
        job = alice_client.post(
            "/api/llm/skill-updates",
            json={"skill_id": sid, "goal": "补充示例"},
        ).json()
        # 同步 worker → 已成功
        detail = alice_client.get(f"/api/llm/jobs/{job['id']}").json()
        assert detail["skill_name"] == "llm-dto"
        assert isinstance(detail["patches"], list)
        assert detail["applied_at"] is None
        # patch-diff endpoint
        diff = alice_client.get(f"/api/llm/jobs/{job['id']}/patch-diff").json()
        assert diff["already_applied"] is False
        assert len(diff["files"]) >= 1
        # 落地
        apply_resp = alice_client.post(f"/api/llm/jobs/{job['id']}/apply")
        assert apply_resp.status_code == 200
        # 第二次落地 → 拒绝
        second = alice_client.post(f"/api/llm/jobs/{job['id']}/apply")
        assert second.status_code in (400, 409)
        detail2 = alice_client.get(f"/api/llm/jobs/{job['id']}").json()
        assert detail2["applied_at"] is not None
    finally:
        llm_worker.set_sync_for_test(False)


def test_skill_list_includes_validation_and_git_bound(alice_client):
    alice_client.post(
        "/api/skills",
        json={
            "name": "list-dto",
            "description": "演示列表 DTO,触发关键词:list,使用场景:测试。",
        },
    )
    items = alice_client.get("/api/skills").json()
    assert items, "应至少有一个 Skill"
    first = next(s for s in items if s["name"] == "list-dto")
    assert "validation_status" in first
    assert "git_bound" in first
    assert first["git_bound"] is False
