"""端到端 smoke test (PRD §14.3 / §17.1)。

严格按 §14.3 9 步运行,断言每步可达。
LLM 用 mock,Git 用本地仓库(无 remote)。
"""
from __future__ import annotations

import io
import zipfile

import pytest

from app.workers import llm_worker


@pytest.fixture(autouse=True)
def _sync_llm():
    llm_worker.set_sync_for_test(True)
    yield
    llm_worker.set_sync_for_test(False)


def test_smoke_full_flow(alice_client):
    # 1. 设置测试 Cookie user_id=alice (fixture 已设置)
    me = alice_client.get("/api/me").json()
    assert me["user_id"] == "alice"

    # 2. 创建 Skill
    skill = alice_client.post(
        "/api/skills",
        json={
            "name": "smoke-skill",
            "description": "smoke 测试 Skill,使用场景:验证完整流程,触发关键词:smoke。",
        },
    ).json()
    sid = skill["id"]

    # 3. 编辑 SKILL.md
    cur = alice_client.get(
        f"/api/skills/{sid}/files/content", params={"path": "SKILL.md"}
    ).json()
    new_md = cur["content"].rstrip() + "\n\n## 新章节\n\n初始内容\n"
    write = alice_client.put(
        f"/api/skills/{sid}/files/content",
        json={"path": "SKILL.md", "content": new_md},
    )
    assert write.status_code == 200

    # 4. 发布 0.1.0
    v1 = alice_client.post(
        f"/api/skills/{sid}/versions",
        json={"version": "0.1.0", "summary": "first", "change_type": "minor"},
    )
    assert v1.status_code == 201, v1.text
    v1_data = v1.json()

    # 5. 查看版本历史
    listed = alice_client.get(f"/api/skills/{sid}/versions").json()
    assert len(listed) == 1

    # 6. 触发 LLM mock 更新
    job = alice_client.post(
        "/api/llm/skill-updates",
        json={"skill_id": sid, "goal": "为 SKILL.md 增加输入校验小节"},
    ).json()
    # 同步模式下任务已成功
    job_detail = alice_client.get(f"/api/llm/jobs/{job['id']}").json()
    assert job_detail["status"] == "succeeded"
    # 落地 patches
    apply_resp = alice_client.post(f"/api/llm/jobs/{job['id']}/apply")
    assert apply_resp.status_code == 200

    # 7. 发布 0.1.1
    v2 = alice_client.post(
        f"/api/skills/{sid}/versions",
        json={"version": "0.1.1", "summary": "after llm", "change_type": "patch"},
    )
    assert v2.status_code == 201
    v2_data = v2.json()

    # 8. 对比两个版本
    diff = alice_client.get(
        f"/api/skills/{sid}/diff",
        params={"from_version_id": v1_data["id"], "to_version_id": v2_data["id"]},
    ).json()
    assert any(f["path"] == "SKILL.md" for f in diff["files"])

    # 9. 导出 zip
    zip_resp = alice_client.get(f"/api/skills/{sid}/export.zip")
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"
    buf = io.BytesIO(zip_resp.content)
    with zipfile.ZipFile(buf) as zf:
        names = set(zf.namelist())
        assert "SKILL.md" in names

    # 额外:审计日志已记录
    audits = alice_client.get("/api/audit-logs").json()
    actions = {a["action"] for a in audits}
    assert {
        "skill.create",
        "skill.file.write",
        "skill.version.publish",
        "llm.update.submit",
        "llm.update.apply",
    } <= actions


def test_audit_only_visible_to_owner(alice_client, bob_client):
    """PRD §17.2.2 — bob 看不到 alice 的审计。"""
    alice_client.post(
        "/api/skills",
        json={"name": "audit-leak", "description": "审计隔离测试,触发关键词:demo。"},
    )
    alice_logs = alice_client.get("/api/audit-logs").json()
    bob_logs = bob_client.get("/api/audit-logs").json()
    assert any(l["action"] == "skill.create" for l in alice_logs)
    assert all(l["user_id"] != "alice" for l in bob_logs)
