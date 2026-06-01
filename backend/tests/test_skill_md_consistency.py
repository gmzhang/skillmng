"""SKILL.md 单 / 多 frontmatter 校验测试 (PRD2 §5)。"""
from __future__ import annotations

import pytest

from app.core.errors import ValidationError
from app.services.validation_service import (
    autofix_double_frontmatter,
    evaluate_skill_md,
    has_multiple_frontmatter,
    validate_skill_md,
)


SINGLE_FM = """---
name: my-skill
description: 演示单 front matter,触发关键词:demo,使用场景:测试。
---

# my-skill

正文内容。
"""

DOUBLE_FM = """---
name: my-skill
description: 第一段。触发关键词:demo,使用场景:测试。
---

# 标题

---
name: my-skill
description: 第二段重复 front matter。
---

剩余正文。
"""


def test_single_frontmatter_passes():
    parsed = validate_skill_md(SINGLE_FM, expected_name="my-skill")
    assert parsed.frontmatter.name == "my-skill"


def test_double_frontmatter_rejected_by_validate():
    assert has_multiple_frontmatter(DOUBLE_FM)
    with pytest.raises(ValidationError):
        validate_skill_md(DOUBLE_FM, expected_name="my-skill")


def test_autofix_removes_second_block():
    fixed = autofix_double_frontmatter(DOUBLE_FM)
    assert not has_multiple_frontmatter(fixed)
    parsed = validate_skill_md(fixed, expected_name="my-skill")
    assert parsed.frontmatter.name == "my-skill"
    assert "剩余正文" in fixed
    # 第二段 frontmatter 已被丢弃,不应再出现"第二段"
    assert "第二段" not in fixed


def test_evaluate_returns_status():
    report = evaluate_skill_md(SINGLE_FM, expected_name="my-skill")
    assert report.status in ("valid", "warning")
    report2 = evaluate_skill_md(DOUBLE_FM, expected_name="my-skill")
    assert report2.status == "error"
    assert any("front matter" in e or "frontmatter" in e for e in report2.errors)


def test_write_skill_md_with_double_fm_blocked(alice_client):
    sid = alice_client.post(
        "/api/skills",
        json={
            "name": "fm-guard",
            "description": "演示双 front matter 拦截,触发关键词:guard。",
        },
    ).json()["id"]
    resp = alice_client.put(
        f"/api/skills/{sid}/files/content",
        json={"path": "SKILL.md", "content": DOUBLE_FM.replace("my-skill", "fm-guard")},
    )
    assert resp.status_code == 422


def test_fix_endpoint_splits_double_fm(alice_client):
    sid = alice_client.post(
        "/api/skills",
        json={
            "name": "fm-fix",
            "description": "演示自动拆分双 front matter,触发关键词:fix。",
        },
    ).json()["id"]
    # 绕过 PUT 校验:通过 fix endpoint 修复前先得制造双 FM,只能直接改 db
    from app.models.skill_file import SkillFile
    from sqlalchemy import select

    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        f = db.scalar(
            select(SkillFile).where(SkillFile.skill_id == sid, SkillFile.path == "SKILL.md")
        )
        f.content_text = DOUBLE_FM.replace("my-skill", "fm-fix")
        db.commit()
    finally:
        db.close()

    resp = alice_client.post(f"/api/skills/{sid}/skill-md/fix")
    assert resp.status_code == 200
    body = resp.json()
    assert body["fixed"] is True
    # 验证状态恢复 valid / warning
    v = alice_client.get(f"/api/skills/{sid}/validation").json()
    assert v["status"] in ("valid", "warning")


def test_validation_endpoint(alice_client):
    sid = alice_client.post(
        "/api/skills",
        json={
            "name": "vstat",
            "description": "演示校验状态返回,使用场景:测试,触发关键词:validate。",
        },
    ).json()["id"]
    resp = alice_client.get(f"/api/skills/{sid}/validation")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("valid", "warning")
