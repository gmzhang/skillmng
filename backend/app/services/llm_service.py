"""LLM service。

支持 Mock 与真实 Anthropic 兼容 API 两种 provider。
真实接入需要:ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN, ANTHROPIC_MODEL。
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.core.config import get_settings
from app.core.errors import BusinessError
from app.services import validation_service as vs

logger = logging.getLogger("app.llm")


# ---------- 输入输出契约 ----------


@dataclass(frozen=True)
class CreateInput:
    skill_name: str
    description: str
    goal: str
    scenario: str = ""
    trigger: str = ""
    target_agent: str = ""
    extra_materials: str = ""
    constraints: str = ""
    include_scripts: bool = True
    include_references: bool = True


@dataclass(frozen=True)
class FileDraft:
    path: str
    content: str


@dataclass(frozen=True)
class CreateOutput:
    skill_md: str
    files: list[FileDraft]
    summary: str
    tests: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class UpdateInput:
    skill_name: str
    current_files: dict[str, str]
    goal: str
    target_version: str | None = None


@dataclass(frozen=True)
class PatchEntry:
    path: str
    change: str  # add / modify / remove
    content: str | None


@dataclass(frozen=True)
class UpdateOutput:
    patches: list[PatchEntry]
    summary: str
    change_type: str  # patch / minor / major
    tests: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


# ---------- Client Protocol ----------


class LLMClient(Protocol):
    def create_skill_draft(self, inp: CreateInput) -> CreateOutput: ...

    def update_skill(self, inp: UpdateInput) -> UpdateOutput: ...


# ---------- Mock Implementation ----------


def _build_description(desc: str, scenario: str, trigger: str) -> str:
    parts = [desc.strip()]
    if scenario.strip() and scenario.strip() not in desc:
        parts.append(f"使用场景:{scenario.strip()}")
    if trigger.strip() and trigger.strip() not in desc:
        parts.append(f"触发关键词:{trigger.strip()}")
    return " ".join(parts).strip()


class MockLLMClient:
    """确定性 Mock,基于模板生成结构化输出。"""

    model_name = "mock"

    def create_skill_draft(self, inp: CreateInput) -> CreateOutput:
        vs.validate_skill_name(inp.skill_name)
        merged_desc = _build_description(inp.description, inp.scenario, inp.trigger)
        if len(merged_desc) < 30:
            merged_desc += " 该 Skill 适合在明确任务范围内被 Agent 自动触发。"
        body = (
            f"# {inp.skill_name}\n\n"
            f"{merged_desc}\n\n"
            "## 任务说明\n\n"
            f"{inp.goal.strip() or '说明 Skill 完成的任务。'}\n\n"
            "## 触发条件\n\n"
            f"- 场景:{inp.scenario.strip() or '(待补充)'}\n"
            f"- 关键词:{inp.trigger.strip() or '(待补充)'}\n"
            f"- 目标 Agent:{inp.target_agent.strip() or '通用'}\n\n"
            "## 执行步骤\n\n"
            "1. 接收用户输入,提取参数 (`$ARGUMENTS`)。\n"
            "2. 校验输入是否满足前置条件。\n"
            "3. 按既定流程执行,可调用 `scripts/` 下脚本完成重复性工作。\n"
            "4. 渲染结构化输出。\n\n"
            "## 输出格式\n\n"
            "| 字段 | 说明 |\n"
            "| --- | --- |\n"
            "| 结果 | 任务结果概述 |\n"
            "| 详情 | 关键步骤记录 |\n\n"
            "## 注意事项\n\n"
            f"- 约束:{inp.constraints.strip() or '保持输出简洁、可被下一个 Agent 消费。'}\n"
            "- 大量参考资料请放在 `references/`,避免污染 `SKILL.md`。\n"
        )

        skill_md = vs.render_skill_md(
            name=inp.skill_name,
            description=merged_desc,
            body=body,
        )

        files: list[FileDraft] = [FileDraft(path="SKILL.md", content=skill_md)]
        if inp.include_scripts:
            files.append(
                FileDraft(
                    path="scripts/run.sh",
                    content=(
                        "#!/usr/bin/env bash\n"
                        "# Mock 脚本占位,由 SKILL.md 引用。\n"
                        f'echo "running {inp.skill_name}"\n'
                    ),
                )
            )
        if inp.include_references:
            files.append(
                FileDraft(
                    path="references/notes.md",
                    content=(
                        f"# {inp.skill_name} 参考资料\n\n"
                        f"用户提供材料:\n\n{inp.extra_materials.strip() or '(无)'}\n"
                    ),
                )
            )

        # 出口校验:确保 SKILL.md 自洽
        vs.validate_skill_md(skill_md, expected_name=inp.skill_name)

        return CreateOutput(
            skill_md=skill_md,
            files=files,
            summary=f"基于目标'{inp.goal[:50]}'生成 {inp.skill_name} 草稿。",
            tests=[
                "用代表性输入运行 Skill,确认执行步骤可顺序完成。",
                "调整 description,确认 Agent 触发表现是否符合预期。",
            ],
            risks=[
                "Mock 输出仅为骨架,真实场景请结合业务再修订。",
            ],
        )

    def update_skill(self, inp: UpdateInput) -> UpdateOutput:
        patches: list[PatchEntry] = []
        goal = inp.goal.strip()

        # 简单策略:在 SKILL.md 末尾追加一节"更新说明",标记 goal。
        if "SKILL.md" in inp.current_files:
            old = inp.current_files["SKILL.md"]
            mark = "<!-- mock-llm-update -->"
            if mark in old:
                # 替换标记块
                new = re.sub(
                    rf"{mark}.*?{mark}",
                    f"{mark}\n\n## 更新说明 (v?)\n\n{goal}\n\n{mark}",
                    old,
                    flags=re.DOTALL,
                )
            else:
                new = (
                    old.rstrip()
                    + f"\n\n{mark}\n\n## 更新说明\n\n{goal}\n\n{mark}\n"
                )
            patches.append(
                PatchEntry(path="SKILL.md", change="modify", content=new)
            )

        # 在 references/ 中追加一条记录
        ref_path = "references/changelog.md"
        existing = inp.current_files.get(ref_path, "")
        if existing:
            new_ref = existing.rstrip() + f"\n\n- {goal}\n"
            change = "modify"
        else:
            new_ref = f"# 变更记录\n\n- {goal}\n"
            change = "add"
        patches.append(PatchEntry(path=ref_path, change=change, content=new_ref))

        return UpdateOutput(
            patches=patches,
            summary=f"按目标'{goal[:50]}'更新 SKILL.md 与 changelog。",
            change_type="patch",
            tests=[
                "审阅 SKILL.md 末尾新增章节是否准确。",
                "运行 Skill 验证更新后行为是否仍可达成原始目标。",
            ],
            risks=["Mock 更新策略简单,真实接入 LLM 后请重新评估。"],
        )


# ---------- Anthropic 兼容客户端 ----------

_SPEC_SUMMARY = """\
## 公司 Skill 规范摘要 (doc/guifan.md + Agent Skills 开放标准)

1. SKILL.md 是核心入口文件,必须有且仅有一个 YAML frontmatter (--- 包裹)。
2. frontmatter 必填字段: name (小写字母数字短横线,3-64字符), description (功能说明+使用场景+关键词)。
3. frontmatter 可选字段: argument-hint, disable-model-invocation (boolean), user-invocable (boolean)。
4. description 是 Agent 发现 Skill 的主要依据,应写清触发场景与适用条件。
5. 指令内容 (frontmatter 之后) 建议包含: Skill 标题、任务说明、执行步骤、输出格式、示例。
6. 支持 $ARGUMENTS 接收完整参数, $0/$1/$2 按位置参数。
7. 大量参考资料放 references/ 目录,可执行脚本放 scripts/ 目录,资源文件放 assets/ 目录。
8. 文件使用 UTF-8,文件名必须为大写 SKILL.md。
9. Skill 应避免过宽泛,围绕明确任务或领域能力。
10. path 必须安全: 相对路径、无 ..、无绝对路径、无控制字符、长度 ≤ 240。
"""

_CREATE_SYSTEM = f"""\
你是 Skill 资深架构师。基于用户输入产出一个符合公司 Skill 规范的 Skill 草稿。

{_SPEC_SUMMARY}

## 输出要求

你必须且只能输出一个 JSON 对象,不要输出任何其他文本、代码块标记或解释。

JSON 结构:
{{
  "summary": "1-3 句创建说明",
  "files": [
    {{"path": "SKILL.md", "content": "完整 SKILL.md 内容"}},
    {{"path": "scripts/run.sh", "content": "脚本内容"}}
  ],
  "tests": ["测试建议1", "测试建议2"],
  "risks": ["风险提示1"]
}}

约束:
- files 数组必须包含 SKILL.md。
- SKILL.md content 必须是完整文件内容(包含 frontmatter)。
- path 必须通过路径安全校验(相对路径、无 ..、无控制字符)。
- 不允许输出真实 token、密钥、内部 cookie。
- SKILL.md 只能有一个 frontmatter 块。
- description 按"功能说明 + 使用场景 + 关键词"组织。
"""

_UPDATE_SYSTEM = f"""\
你是 Skill 维护工程师,基于当前 Skill 文件树与用户的修改目标输出更新 patch。

{_SPEC_SUMMARY}

## 输出要求

你必须且只能输出一个 JSON 对象,不要输出任何其他文本、代码块标记或解释。

JSON 结构:
{{
  "summary": "更新摘要",
  "change_type": "patch",
  "patches": [
    {{"path": "SKILL.md", "change": "modify", "content": "完整新内容"}}
  ],
  "tests": ["测试建议"],
  "risks": ["风险提示"]
}}

约束:
- patches[].change 只允许: add, modify, remove。
- change=remove 时 content 为 null。
- change=add/modify 时 content 必须是完整文件内容。
- change_type 只允许: patch, minor, major。
- SKILL.md 的 content 必须包含完整 frontmatter + 正文。
- 不允许修改 SKILL.md 的 name 字段为与当前 Skill 不一致的值。
- path 必须安全(相对路径、无 ..、无控制字符)。
"""

_JSON_REPAIR_MSG = "你上次的输出不是合法 JSON。请重新输出,只输出纯 JSON 对象,不要加代码块标记或其他文字。"


def _extract_json(text: str) -> str:
    """从 LLM 输出中提取 JSON,处理代码块包裹等情况。"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        start = 1
        end = len(lines)
        for i in range(1, len(lines)):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[start:end]).strip()
    return text


def _parse_json_output(text: str) -> dict[str, Any]:
    """解析 LLM JSON 输出,失败时尝试提取。"""
    raw = _extract_json(text)
    return json.loads(raw)


def _detect_api_style(style: str, base_url: str) -> bool:
    """Return True if OpenAI-compatible, False if native Anthropic."""
    style = style.strip().lower()
    if style == "openai-compatible":
        return True
    if style == "anthropic":
        return False
    # auto: detect from URL
    return "compatible" in base_url or "dashscope" in base_url or "openai" in base_url


class AnthropicLLMClient:
    """LLM HTTP 客户端,支持 Anthropic Messages API 和 OpenAI-compatible API (PRD3 §3.3)。"""

    def __init__(self) -> None:
        s = get_settings()
        self.base_url = s.llm_base_url.rstrip("/")
        self.token = s.llm_api_key
        self.model = s.llm_model
        self.timeout = s.api_timeout_ms / 1000.0
        self.model_name = self.model
        self._proxy = s.httpx_proxy
        self._is_openai_compat = _detect_api_style(s.llm_api_style, self.base_url)

    def _call(self, *, system: str, user_msg: str, retry_on_json_fail: bool = True) -> dict[str, Any]:
        if not self.token:
            raise BusinessError("LLM API Key 未配置 (ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN)。", code="llm_token_missing")

        messages = self._build_messages(system, user_msg)
        resp_text = self._do_request(messages)

        try:
            return _parse_json_output(resp_text)
        except (json.JSONDecodeError, ValueError) as first_err:
            if not retry_on_json_fail:
                raise BusinessError(
                    f"LLM 输出非法 JSON (已重试): {str(first_err)[:200]}",
                    code="llm_json_parse_failed",
                )
            logger.warning("LLM JSON 解析失败,尝试自动修复: %s", str(first_err)[:100])
            messages.append({"role": "assistant", "content": resp_text})
            messages.append({"role": "user", "content": _JSON_REPAIR_MSG})
            resp_text2 = self._do_request(messages)
            try:
                return _parse_json_output(resp_text2)
            except (json.JSONDecodeError, ValueError) as e:
                raise BusinessError(
                    f"LLM 输出 JSON 修复失败: {str(e)[:200]}",
                    code="llm_json_parse_failed",
                )

    def _build_messages(self, system: str, user_msg: str) -> list[dict[str, str]]:
        """构建消息列表,OpenAI 格式统一使用 system role。"""
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ]

    def _do_request(self, messages: list[dict[str, str]]) -> str:
        if self._is_openai_compat:
            return self._do_openai_request(messages)
        return self._do_anthropic_request(messages)

    def _do_openai_request(self, messages: list[dict[str, str]]) -> str:
        """OpenAI Chat Completions 格式 (DashScope / OpenAI-compatible)。"""
        url = f"{self.base_url}/chat/completions"
        if self.base_url.endswith("/chat/completions"):
            url = self.base_url

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": messages,
        }

        try:
            with httpx.Client(timeout=self.timeout, proxy=self._proxy) as client:
                resp = client.post(url, headers=headers, json=body)
        except httpx.TimeoutException:
            raise BusinessError("LLM 请求超时。", code="llm_timeout")
        except httpx.RequestError as e:
            raise BusinessError(f"LLM 请求网络错误: {type(e).__name__}", code="llm_network_error")

        if resp.status_code != 200:
            self._handle_error(resp)

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise BusinessError("LLM 返回空 choices。", code="llm_empty_response")
        return choices[0].get("message", {}).get("content", "")

    def _do_anthropic_request(self, messages: list[dict[str, str]]) -> str:
        """Anthropic Messages API 格式。"""
        url = f"{self.base_url}/v1/messages"
        if self.base_url.endswith("/v1/messages"):
            url = self.base_url
        elif self.base_url.endswith("/v1"):
            url = f"{self.base_url}/messages"

        # Anthropic 格式: system 单独字段,messages 只含 user/assistant
        system_msg = ""
        api_messages: list[dict[str, str]] = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                api_messages.append(m)

        headers = {
            "x-api-key": self.token,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 8192,
            "system": system_msg,
            "messages": api_messages,
        }

        try:
            with httpx.Client(timeout=self.timeout, proxy=self._proxy) as client:
                resp = client.post(url, headers=headers, json=body)
        except httpx.TimeoutException:
            raise BusinessError("LLM 请求超时。", code="llm_timeout")
        except httpx.RequestError as e:
            raise BusinessError(f"LLM 请求网络错误: {type(e).__name__}", code="llm_network_error")

        if resp.status_code != 200:
            self._handle_error(resp)

        data = resp.json()
        content_blocks = data.get("content", [])
        if not content_blocks:
            raise BusinessError("LLM 返回空 content。", code="llm_empty_response")
        return content_blocks[0].get("text", "")

    def _handle_error(self, resp: httpx.Response) -> None:
        detail = resp.text[:300] if resp.text else "(empty)"
        logger.error("LLM API 返回 %d: %s", resp.status_code, detail)
        err_msg = f"LLM API 错误 (HTTP {resp.status_code})"
        try:
            err_data = resp.json()
            if err_data.get("message"):
                err_msg = f"LLM API: {err_data['message']}"
            elif err_data.get("error", {}).get("message"):
                err_msg = f"LLM API: {err_data['error']['message']}"
        except Exception:
            pass
        raise BusinessError(err_msg, code="llm_api_error")

    def create_skill_draft(self, inp: CreateInput) -> CreateOutput:
        vs.validate_skill_name(inp.skill_name)

        user_msg_parts = [
            f"Skill 名称: {inp.skill_name}",
            f"描述: {inp.description}",
            f"目标: {inp.goal}",
        ]
        if inp.scenario:
            user_msg_parts.append(f"使用场景: {inp.scenario}")
        if inp.trigger:
            user_msg_parts.append(f"触发关键词: {inp.trigger}")
        if inp.target_agent:
            user_msg_parts.append(f"目标 Agent: {inp.target_agent}")
        if inp.extra_materials:
            user_msg_parts.append(f"参考材料:\n{inp.extra_materials}")
        if inp.constraints:
            user_msg_parts.append(f"约束条件: {inp.constraints}")
        if inp.include_scripts:
            user_msg_parts.append("请包含 scripts/ 示例脚本。")
        if inp.include_references:
            user_msg_parts.append("请包含 references/ 参考资料占位。")

        result = self._call(system=_CREATE_SYSTEM, user_msg="\n".join(user_msg_parts))

        files_raw = result.get("files", [])
        files: list[FileDraft] = []
        skill_md_content = ""
        for f in files_raw:
            path = f.get("path", "")
            content = f.get("content", "")
            vs.validate_path(path)
            files.append(FileDraft(path=path, content=content))
            if path == "SKILL.md":
                skill_md_content = content

        if not skill_md_content:
            raise BusinessError("LLM 输出缺少 SKILL.md。", code="llm_missing_skill_md")

        vs.validate_skill_md(skill_md_content, expected_name=inp.skill_name)

        return CreateOutput(
            skill_md=skill_md_content,
            files=files,
            summary=result.get("summary", "LLM 生成完成。"),
            tests=result.get("tests", []),
            risks=result.get("risks", []),
        )

    def update_skill(self, inp: UpdateInput) -> UpdateOutput:
        user_msg_parts = [
            f"Skill 名称: {inp.skill_name}",
            f"修改目标: {inp.goal}",
        ]
        if inp.target_version:
            user_msg_parts.append(f"目标版本: {inp.target_version}")
        user_msg_parts.append("\n当前文件树:")
        for path, content in inp.current_files.items():
            user_msg_parts.append(f"\n--- {path} ---\n{content[:3000]}")

        result = self._call(system=_UPDATE_SYSTEM, user_msg="\n".join(user_msg_parts))

        patches_raw = result.get("patches", [])
        patches: list[PatchEntry] = []
        for p in patches_raw:
            path = p.get("path", "")
            change = p.get("change", "modify")
            content = p.get("content")
            if change not in ("add", "modify", "remove"):
                change = "modify"
            vs.validate_path(path)
            patches.append(PatchEntry(path=path, change=change, content=content))

        change_type = result.get("change_type", "patch")
        if change_type not in ("patch", "minor", "major"):
            change_type = "patch"

        return UpdateOutput(
            patches=patches,
            summary=result.get("summary", "LLM 更新完成。"),
            change_type=change_type,
            tests=result.get("tests", []),
            risks=result.get("risks", []),
        )


# ---------- Factory ----------


def get_llm_client() -> LLMClient:
    provider = get_settings().llm_provider.lower()
    if provider == "mock":
        return MockLLMClient()
    if provider == "anthropic":
        return AnthropicLLMClient()
    raise BusinessError(
        f"不支持的 LLM_PROVIDER={provider},可选: mock, anthropic。",
        code="llm_provider_unsupported",
    )
