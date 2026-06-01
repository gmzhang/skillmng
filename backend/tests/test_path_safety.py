"""路径安全测试 (PRD §13.2 / §17.2.1)。"""
from __future__ import annotations

import pytest

from app.core.errors import ValidationError
from app.services.validation_service import validate_path


def test_normal_relative_path_ok():
    assert validate_path("scripts/run.sh") == "scripts/run.sh"
    assert validate_path("./SKILL.md") == "SKILL.md"


def test_absolute_path_rejected():
    with pytest.raises(ValidationError):
        validate_path("/etc/passwd")
    with pytest.raises(ValidationError):
        validate_path("\\Windows\\System32")
    with pytest.raises(ValidationError):
        validate_path("C:\\Windows")


def test_dotdot_rejected():
    with pytest.raises(ValidationError):
        validate_path("../etc/passwd")
    with pytest.raises(ValidationError):
        validate_path("scripts/../../etc")


def test_empty_path_rejected():
    with pytest.raises(ValidationError):
        validate_path("")
    with pytest.raises(ValidationError):
        validate_path("   ")
    with pytest.raises(ValidationError):
        validate_path("./")


def test_control_chars_rejected():
    with pytest.raises(ValidationError):
        validate_path("a/b\x00c")


def test_too_long_path_rejected():
    with pytest.raises(ValidationError):
        validate_path("a/" + ("b" * 250))


def test_too_long_segment_rejected():
    with pytest.raises(ValidationError):
        validate_path("a/" + ("b" * 130))
