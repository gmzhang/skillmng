"""SKILL.md frontmatter 与内容校验测试 (PRD §13.1)。"""
from __future__ import annotations

import pytest

from app.core.errors import ValidationError
from app.services.validation_service import (
    parse_skill_md,
    render_skill_md,
    validate_skill_md,
    validate_skill_name,
)


def test_valid_skill_md_parses():
    md = """---
name: my-skill
description: 一个完整的描述说明,包含触发场景和关键词。
argument-hint: "[file]"
disable-model-invocation: false
user-invocable: true
---

# my-skill

主体内容。
"""
    parsed = validate_skill_md(md, expected_name="my-skill")
    assert parsed.frontmatter.name == "my-skill"
    assert parsed.frontmatter.argument_hint == "[file]"
    assert parsed.frontmatter.disable_model_invocation is False
    assert parsed.frontmatter.user_invocable is True
    assert "主体" in parsed.body


def test_missing_frontmatter_rejected():
    md = "# 无 frontmatter\n\nbody"
    with pytest.raises(ValidationError):
        validate_skill_md(md)


def test_unclosed_frontmatter_rejected():
    md = "---\nname: x\n\nbody"
    with pytest.raises(ValidationError):
        validate_skill_md(md)


def test_missing_name_rejected():
    md = "---\ndescription: x\n---\nbody"
    with pytest.raises(ValidationError):
        validate_skill_md(md)


def test_empty_body_rejected():
    md = "---\nname: my-skill\ndescription: ok\n---\n\n   \n"
    with pytest.raises(ValidationError):
        validate_skill_md(md)


def test_name_mismatch_rejected():
    md = "---\nname: a-skill\ndescription: ok\n---\nbody"
    with pytest.raises(ValidationError):
        validate_skill_md(md, expected_name="another-skill")


def test_disable_model_invocation_must_be_bool():
    md = "---\nname: my-skill\ndescription: ok\ndisable-model-invocation: maybe\n---\nbody"
    with pytest.raises(ValidationError):
        validate_skill_md(md)


def test_skill_name_regex():
    validate_skill_name("ok-skill")
    validate_skill_name("a1-b2")
    with pytest.raises(ValidationError):
        validate_skill_name("AB")
    with pytest.raises(ValidationError):
        validate_skill_name("ab")  # 太短
    with pytest.raises(ValidationError):
        validate_skill_name("a_b")
    with pytest.raises(ValidationError):
        validate_skill_name("a" * 65)


def test_render_round_trip():
    md = render_skill_md(
        name="round-trip",
        description="round trip 描述",
        body="# round-trip\n\nbody",
        argument_hint="[x]",
    )
    parsed = parse_skill_md(md)
    assert parsed.frontmatter.name == "round-trip"
    assert parsed.frontmatter.argument_hint == "[x]"
