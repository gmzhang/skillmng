"""校验服务。

集中处理 SKILL.md 校验、文件路径安全、Skill 名称、文件大小 (PRD §13)。
所有需要校验路径的地方都必须经过 validate_path。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

from app.core.errors import ValidationError

# Skill 名称:小写字母数字短横线,3-64 (PRD §7.4)
SKILL_NAME_RE = re.compile(r"^[a-z0-9-]{3,64}$")

# 路径安全 (PRD §13.2)
MAX_PATH_LEN = 240
MAX_SEGMENT_LEN = 128
ABS_PATH_RE = re.compile(r"^[/\\]")
WINDOWS_DRIVE_RE = re.compile(r"^[a-zA-Z]:")
CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


def validate_skill_name(name: str) -> None:
    """名称必填、3-64、仅 [a-z0-9-]。"""
    if not name:
        raise ValidationError("Skill 名称不能为空。", code="invalid_skill_name")
    if not SKILL_NAME_RE.fullmatch(name):
        raise ValidationError(
            "Skill 名称仅允许 [a-z0-9-],长度 3-64。",
            code="invalid_skill_name",
        )


@dataclass(frozen=True)
class DescriptionQuality:
    too_short: bool
    too_long: bool
    has_trigger_keyword: bool


def evaluate_description(description: str) -> DescriptionQuality:
    """描述质量提示;不阻塞,仅返回信号。"""
    desc = (description or "").strip()
    triggers = (
        "when", "use when", "trigger", "mentioned", "asks", "needs", "use",
        "使用", "场景", "触发", "调用", "适用于", "当用户", "用户提到",
        "提到", "要求", "需要", "URL", "链接",
    )
    return DescriptionQuality(
        too_short=len(desc) < 50,
        too_long=len(desc) > 500,
        has_trigger_keyword=any(t in desc.lower() for t in triggers),
    )


def require_description(description: str) -> None:
    if not description or not description.strip():
        raise ValidationError("description 不能为空。", code="invalid_description")


def validate_path(path: str) -> str:
    """规范化校验文件路径。返回规范化后的相对路径(POSIX 风格)。

    禁止:绝对路径、`..`、空、控制字符、超长。
    """
    if not path or not path.strip():
        raise ValidationError("path 不能为空。", code="invalid_path")
    if CONTROL_CHARS_RE.search(path):
        raise ValidationError("path 不允许包含控制字符。", code="invalid_path")
    if ABS_PATH_RE.match(path) or WINDOWS_DRIVE_RE.match(path):
        raise ValidationError("path 不允许绝对路径。", code="invalid_path")
    if len(path) > MAX_PATH_LEN:
        raise ValidationError(
            f"path 超过最大长度 {MAX_PATH_LEN}。", code="invalid_path"
        )
    # 统一为 posix
    norm = path.replace("\\", "/").strip("/")
    parts = norm.split("/")
    cleaned: list[str] = []
    for seg in parts:
        if seg == "" or seg == ".":
            continue
        if seg == "..":
            raise ValidationError("path 不允许包含 '..'。", code="invalid_path")
        if len(seg) > MAX_SEGMENT_LEN:
            raise ValidationError(
                f"path 单段超过 {MAX_SEGMENT_LEN}。", code="invalid_path"
            )
        cleaned.append(seg)
    if not cleaned:
        raise ValidationError("path 规范化后为空。", code="invalid_path")
    return "/".join(cleaned)


def validate_file_size(path: str, size: int, *, max_default: int, max_asset: int) -> None:
    """assets/ 下放宽到 max_asset,其它走 max_default。"""
    norm = validate_path(path)
    limit = max_asset if norm.startswith("assets/") else max_default
    if size > limit:
        raise ValidationError(
            f"文件 {norm} 大小 {size} 超出限制 {limit}。",
            code="file_too_large",
        )


@dataclass(frozen=True)
class SkillMdFrontmatter:
    name: str
    description: str
    argument_hint: str | None
    disable_model_invocation: bool
    user_invocable: bool


@dataclass(frozen=True)
class SkillMdParsed:
    frontmatter: SkillMdFrontmatter
    body: str
    raw_frontmatter: dict[str, Any]


_FM_DELIM = "---"


def parse_skill_md(content: str) -> SkillMdParsed:
    """解析 SKILL.md。frontmatter 必须以 `---\\n...\\n---` 包裹。"""
    if not content or not content.strip():
        raise ValidationError("SKILL.md 内容为空。", code="invalid_skill_md")

    text = content.lstrip("﻿")  # 去 BOM
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FM_DELIM:
        raise ValidationError(
            "SKILL.md 必须以 YAML frontmatter 开头(--- 包裹)。",
            code="invalid_skill_md",
        )

    end_idx: int | None = None
    for i in range(1, len(lines)):
        if lines[i].strip() == _FM_DELIM:
            end_idx = i
            break
    if end_idx is None:
        raise ValidationError(
            "未找到 frontmatter 结束符 ---。", code="invalid_skill_md"
        )

    fm_text = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :]).strip()
    if not body:
        raise ValidationError("SKILL.md 正文不能为空。", code="invalid_skill_md")

    try:
        raw = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        raise ValidationError(f"frontmatter YAML 解析失败:{e}", code="invalid_skill_md")
    if not isinstance(raw, dict):
        raise ValidationError("frontmatter 必须是对象。", code="invalid_skill_md")

    name = str(raw.get("name") or "").strip()
    description = str(raw.get("description") or "").strip()
    if not name:
        raise ValidationError("frontmatter 缺少 name。", code="invalid_skill_md")
    if not description:
        raise ValidationError("frontmatter 缺少 description。", code="invalid_skill_md")

    argument_hint = raw.get("argument-hint")
    if argument_hint is not None and not isinstance(argument_hint, str):
        raise ValidationError("argument-hint 必须是字符串。", code="invalid_skill_md")

    dmi = raw.get("disable-model-invocation", False)
    if not isinstance(dmi, bool):
        raise ValidationError(
            "disable-model-invocation 必须是布尔值。", code="invalid_skill_md"
        )

    ui = raw.get("user-invocable", True)
    if not isinstance(ui, bool):
        raise ValidationError("user-invocable 必须是布尔值。", code="invalid_skill_md")

    return SkillMdParsed(
        frontmatter=SkillMdFrontmatter(
            name=name,
            description=description,
            argument_hint=argument_hint,
            disable_model_invocation=dmi,
            user_invocable=ui,
        ),
        body=body,
        raw_frontmatter=raw,
    )


def validate_skill_md(content: str, *, expected_name: str | None = None) -> SkillMdParsed:
    """完整校验 SKILL.md。expected_name 非空时校验一致 (PRD §13.1)。"""
    if has_multiple_frontmatter(content):
        raise ValidationError(
            "检测到多个 YAML front matter,SKILL.md 只允许一个 frontmatter 块。",
            code="duplicate_frontmatter",
        )
    parsed = parse_skill_md(content)
    validate_skill_name(parsed.frontmatter.name)
    if expected_name is not None and parsed.frontmatter.name != expected_name:
        raise ValidationError(
            f"frontmatter 中的 name={parsed.frontmatter.name} 与 Skill 名称 {expected_name} 不一致。",
            code="invalid_skill_md",
        )
    return parsed


def render_skill_md(
    *,
    name: str,
    description: str,
    body: str,
    argument_hint: str | None = None,
    disable_model_invocation: bool = False,
    user_invocable: bool = True,
) -> str:
    """从结构化字段渲染 SKILL.md。"""
    fm: dict[str, Any] = {"name": name, "description": description}
    if argument_hint:
        fm["argument-hint"] = argument_hint
    if disable_model_invocation:
        fm["disable-model-invocation"] = True
    if user_invocable is False:
        fm["user-invocable"] = False
    fm_text = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{fm_text}\n---\n\n{body.strip()}\n"


# ---- 双 front matter 检测与修复 (PRD2 §5) ----


def _find_frontmatter_blocks(content: str) -> list[tuple[int, int]]:
    """扫描所有 `---\\n...\\n---` 块,返回 (start_line, end_line) 索引。

    起始行必须是孤立的 `---`(允许尾随空格);结束行同样要求。
    只检测能成对的块。
    """
    lines = content.lstrip("﻿").splitlines()
    blocks: list[tuple[int, int]] = []
    i = 0
    n = len(lines)
    while i < n:
        if lines[i].strip() == _FM_DELIM:
            for j in range(i + 1, n):
                if lines[j].strip() == _FM_DELIM:
                    blocks.append((i, j))
                    i = j + 1
                    break
            else:
                break
        else:
            i += 1
    return blocks


def has_multiple_frontmatter(content: str) -> bool:
    """正文中是否含至少 2 个完整 front matter 块。"""
    return len(_find_frontmatter_blocks(content)) >= 2


def autofix_double_frontmatter(content: str) -> str:
    """保留第一个 front matter,后续 front matter 块整体丢弃(包含定界符)。

    保留正文中其它内容。
    """
    blocks = _find_frontmatter_blocks(content)
    if len(blocks) < 2:
        return content
    lines = content.lstrip("﻿").splitlines()
    # blocks[0] 保留;blocks[1:] 全部丢弃
    drop = set()
    for start, end in blocks[1:]:
        for k in range(start, end + 1):
            drop.add(k)
    kept = [ln for idx, ln in enumerate(lines) if idx not in drop]
    return "\n".join(kept).rstrip() + "\n"


@dataclass(frozen=True)
class ValidationReport:
    """SKILL.md 校验报告。"""

    status: str  # valid / warning / error
    errors: list[str]
    warnings: list[str]


def evaluate_skill_md(
    content: str, *, expected_name: str | None = None
) -> ValidationReport:
    """非抛出版校验。errors 非空 → error;否则 warnings 非空 → warning;都空 → valid。"""
    errors: list[str] = []
    warnings: list[str] = []

    if not content or not content.strip():
        errors.append("SKILL.md 内容为空。")
        return ValidationReport(status="error", errors=errors, warnings=warnings)

    if has_multiple_frontmatter(content):
        errors.append(
            "检测到多个 YAML front matter,SKILL.md 只允许一个 frontmatter 块。"
        )

    try:
        parsed = parse_skill_md(content)
        if expected_name is not None and parsed.frontmatter.name != expected_name:
            errors.append(
                f"frontmatter 中 name={parsed.frontmatter.name} 与 Skill 名称 "
                f"{expected_name} 不一致。"
            )
        quality = evaluate_description(parsed.frontmatter.description)
        if quality.too_short:
            warnings.append(
                "description 较短,建议至少 50 字符并包含触发场景。"
            )
        if quality.too_long:
            warnings.append("description 较长,建议精简到 500 字符以内。")
        if not quality.has_trigger_keyword:
            warnings.append(
                "description 未包含明显的触发关键词(场景/触发/使用 等)。"
            )
    except ValidationError as e:
        errors.append(e.message)

    if errors:
        return ValidationReport(status="error", errors=errors, warnings=warnings)
    if warnings:
        return ValidationReport(status="warning", errors=[], warnings=warnings)
    return ValidationReport(status="valid", errors=[], warnings=[])
