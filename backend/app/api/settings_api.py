"""设置页 API (PRD2 §4.4, PRD4 §3.4/3.5)。

第一阶段只读。token 永远掩码。连接测试写入审计日志。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CurrentUserDep, DBDep
from app.core.config import get_settings
from app.services import antcode_client, audit_service
from app.services.llm_service import _detect_api_style

router = APIRouter()


class GitSettings(BaseModel):
    antcode_api_base_url: str
    antcode_group_url: str
    antcode_namespace_id: int
    antcode_token_status: str  # configured | missing
    antcode_token_mask: str
    default_branch: str
    draft_branch_prefix: str
    delete_draft_branch_after_publish: bool
    ssh_key_path: str
    repo_url_template: str
    auto_create_repository: bool
    proxy: dict[str, str]


class LLMSettings(BaseModel):
    provider: str
    base_url: str
    model: str
    timeout_ms: int
    token_configured: bool
    api_style: str  # anthropic | openai-compatible | auto


class SystemLimits(BaseModel):
    max_upload_bytes: int
    max_file_bytes: int
    max_asset_file_bytes: int
    max_files_per_skill: int


class SpecRules(BaseModel):
    enabled_rules: list[str]
    skill_md_rules: list[str]
    path_rules: list[str]


class SettingsOut(BaseModel):
    app_env: str
    git: GitSettings
    llm: LLMSettings
    limits: SystemLimits
    spec: SpecRules


def _proxy_dict() -> dict[str, str]:
    s = get_settings()
    import os
    effective = s.httpx_proxy or ""
    env_https = os.environ.get("https_proxy", os.environ.get("HTTPS_PROXY", ""))
    env_http = os.environ.get("http_proxy", os.environ.get("HTTP_PROXY", ""))
    env_all = os.environ.get("all_proxy", os.environ.get("ALL_PROXY", ""))
    return {
        "https_proxy": s.https_proxy or env_https,
        "http_proxy": s.http_proxy or env_http,
        "all_proxy": s.all_proxy or env_all,
        "effective_proxy": effective or env_https or env_http or env_all,
    }


@router.get("", response_model=SettingsOut)
def get_settings_view(_: CurrentUserDep):
    s = get_settings()
    return SettingsOut(
        app_env=s.app_env,
        git=GitSettings(
            antcode_api_base_url=s.antcode_api_base_url,
            antcode_group_url=s.antcode_group_url,
            antcode_namespace_id=s.antcode_namespace_id,
            antcode_token_status="configured"
            if antcode_client.is_configured(s)
            else "missing",
            antcode_token_mask=antcode_client.mask_token(s.antcode_private_token),
            default_branch=s.skill_default_branch,
            draft_branch_prefix=s.skill_draft_branch_prefix,
            delete_draft_branch_after_publish=s.skill_delete_draft_branch_after_publish,
            ssh_key_path=s.skill_git_ssh_key,
            repo_url_template=s.skill_git_repo_url_template,
            auto_create_repository=bool(s.antcode_private_token),
            proxy=_proxy_dict(),
        ),
        llm=LLMSettings(
            provider=s.llm_provider,
            base_url=s.llm_base_url,
            model=s.llm_model,
            timeout_ms=s.api_timeout_ms,
            token_configured=bool(s.llm_api_key),
            api_style=s.llm_api_style,
        ),
        limits=SystemLimits(
            max_upload_bytes=s.max_upload_bytes,
            max_file_bytes=s.max_file_bytes,
            max_asset_file_bytes=s.max_asset_file_bytes,
            max_files_per_skill=s.max_files_per_skill,
        ),
        spec=SpecRules(
            enabled_rules=[
                "公司规范 doc/guifan.md",
                "Agent Skills 开放标准",
                "PRD1 §13 校验规则",
                "PRD2 §5 单 front matter",
            ],
            skill_md_rules=[
                "文件以 --- 开头,只允许一个 frontmatter 块",
                "name 与 Skill 名称一致",
                "description 必填,推荐含触发关键词",
                "正文不能为空",
            ],
            path_rules=[
                "禁止绝对路径 / .. / 空段 / 控制字符",
                "路径长度 ≤ 240,单段 ≤ 128",
            ],
        ),
    )


class TestResult(BaseModel):
    ok: bool
    message: str
    detail: dict | None = None


@router.post("/test-git", response_model=TestResult)
def test_git(user: CurrentUserDep, db: DBDep):
    s = get_settings()
    tested_at = datetime.now(timezone.utc).isoformat()
    if not antcode_client.is_configured(s):
        result = TestResult(ok=False, message="ANTCODE_PRIVATE_TOKEN 未配置", detail={"tested_at": tested_at})
        audit_service.record(db, user_id=user.user_id, action="settings.antcode.test", summary=result.message)
        return result
    try:
        with antcode_client.build_client(s) as client:
            user_info = client.get_user()
            group = client.get_group(s.antcode_namespace_id)
        proxy_info = _proxy_dict()
        result = TestResult(
            ok=True,
            message=f"连接成功:用户 {user_info.get('username')} / 群组 {group.get('path')}",
            detail={
                "tested_at": tested_at,
                "user_id": user_info.get("id"),
                "username": user_info.get("username"),
                "group_id": group.get("id"),
                "group_path": group.get("path"),
                "proxy_enabled": bool(proxy_info.get("effective_proxy")),
            },
        )
        audit_service.record(db, user_id=user.user_id, action="settings.antcode.test", summary=result.message)
        return result
    except Exception as e:  # noqa: BLE001
        proxy_info = _proxy_dict()
        result = TestResult(ok=False, message=f"AntCode 连接失败:{e}", detail={"tested_at": tested_at, "proxy_enabled": bool(proxy_info.get("effective_proxy"))})
        audit_service.record(db, user_id=user.user_id, action="settings.antcode.test", summary=result.message)
        return result


@router.post("/test-ssh", response_model=TestResult)
def test_ssh(user: CurrentUserDep, db: DBDep):
    """测试 SSH 密钥是否可连接 Git 平台。"""
    import os
    import subprocess

    s = get_settings()
    tested_at = datetime.now(timezone.utc).isoformat()

    key_path = s.skill_git_ssh_key
    if not key_path:
        result = TestResult(ok=False, message="SKILL_GIT_SSH_KEY 未配置", detail={"tested_at": tested_at})
        audit_service.record(db, user_id=user.user_id, action="settings.ssh.test", summary=result.message)
        return result

    if not os.path.isfile(key_path):
        result = TestResult(
            ok=False,
            message=f"SSH 密钥文件不存在: {key_path}",
            detail={"tested_at": tested_at, "key_path": key_path},
        )
        audit_service.record(db, user_id=user.user_id, action="settings.ssh.test", summary=result.message)
        return result

    from urllib.parse import urlparse
    host = urlparse(s.antcode_api_base_url).hostname or "code.myxiaojin.cn"
    ssh_cmd = [
        "ssh", "-T",
        "-i", key_path,
        "-o", "IdentitiesOnly=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=10",
        f"git@{host}",
    ]

    try:
        proc = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = (proc.stdout + proc.stderr).strip()
        if proc.returncode in (0, 1) and ("welcome" in output.lower() or "successfully" in output.lower() or "hello" in output.lower()):
            result = TestResult(
                ok=True,
                message=f"SSH 连接成功: {output[:120]}",
                detail={"tested_at": tested_at, "host": host, "key_path": key_path, "exit_code": proc.returncode},
            )
        else:
            result = TestResult(
                ok=False,
                message=f"SSH 连接失败 (exit {proc.returncode}): {output[:200]}",
                detail={"tested_at": tested_at, "host": host, "key_path": key_path, "exit_code": proc.returncode},
            )
    except subprocess.TimeoutExpired:
        result = TestResult(
            ok=False,
            message=f"SSH 连接超时 (>{15}s)",
            detail={"tested_at": tested_at, "host": host, "key_path": key_path},
        )
    except Exception as e:  # noqa: BLE001
        result = TestResult(
            ok=False,
            message=f"SSH 测试异常: {type(e).__name__}: {e}",
            detail={"tested_at": tested_at, "host": host, "key_path": key_path},
        )

    audit_service.record(db, user_id=user.user_id, action="settings.ssh.test", summary=result.message)
    return result


@router.post("/test-llm", response_model=TestResult)
def test_llm(user: CurrentUserDep, db: DBDep):
    s = get_settings()
    tested_at = datetime.now(timezone.utc).isoformat()

    if s.llm_provider == "mock":
        result = TestResult(
            ok=True,
            message="当前 LLM_PROVIDER=mock,Mock 客户端始终可用。",
            detail={"provider": "mock", "tested_at": tested_at},
        )
        audit_service.record(db, user_id=user.user_id, action="settings.llm.test", summary=result.message)
        return result

    if s.llm_provider == "anthropic":
        token = s.llm_api_key
        if not token:
            result = TestResult(
                ok=False,
                message="LLM API Key 未配置 (ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN)。",
                detail={"tested_at": tested_at, "provider": s.llm_provider},
            )
            audit_service.record(db, user_id=user.user_id, action="settings.llm.test", summary=result.message)
            return result

        import httpx

        base = s.llm_base_url.rstrip("/")
        model = s.llm_model
        is_openai_compat = _detect_api_style(s.llm_api_style, base)
        api_style_label = "openai-compatible" if is_openai_compat else "anthropic"

        if is_openai_compat:
            url = f"{base}/chat/completions"
            if base.endswith("/chat/completions"):
                url = base
            headers = {
                "Authorization": "Bearer ***",
                "Content-Type": "application/json",
            }
            real_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            body = {
                "model": model,
                "max_tokens": 16,
                "messages": [{"role": "user", "content": "ping"}],
            }
        else:
            url = f"{base}/v1/messages"
            if base.endswith("/v1/messages"):
                url = base
            elif base.endswith("/v1"):
                url = f"{base}/messages"
            headers = {
                "x-api-key": "***",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            real_headers = {
                "x-api-key": token,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            body = {
                "model": model,
                "max_tokens": 16,
                "messages": [{"role": "user", "content": "ping"}],
            }

        proxy_info = _proxy_dict()
        base_detail: dict = {
            "tested_at": tested_at,
            "provider": s.llm_provider,
            "model": model,
            "api_style": api_style_label,
            "base_url": base,
            "request_url": url,
            "proxy_enabled": bool(proxy_info.get("effective_proxy")),
        }

        try:
            with httpx.Client(timeout=30, proxy=s.httpx_proxy) as client:
                resp = client.post(url, headers=real_headers, json=body)
            if resp.status_code == 200:
                data = resp.json()
                model = data.get("model", s.llm_model)
                result = TestResult(
                    ok=True,
                    message=f"LLM 连接成功,模型: {model}",
                    detail={**base_detail, "model": model, "status_code": 200},
                )
                audit_service.record(db, user_id=user.user_id, action="settings.llm.test", summary=result.message)
                return result

            base_detail["status_code"] = resp.status_code
            error_msg = f"LLM API 返回 HTTP {resp.status_code}"
            try:
                err_data = resp.json()
                if err_data.get("message"):
                    error_msg = f"LLM API: {err_data['message']}"
                    base_detail["api_message"] = err_data["message"]
                elif err_data.get("error", {}).get("message"):
                    error_msg = f"LLM API: {err_data['error']['message']}"
                    base_detail["api_message"] = err_data["error"]["message"]
            except Exception:
                pass
            result = TestResult(ok=False, message=error_msg, detail=base_detail)
            audit_service.record(db, user_id=user.user_id, action="settings.llm.test", summary=result.message)
            return result
        except Exception as e:  # noqa: BLE001
            result = TestResult(
                ok=False,
                message=f"LLM 连接失败: {type(e).__name__}",
                detail={**base_detail, "error_type": type(e).__name__},
            )
            audit_service.record(db, user_id=user.user_id, action="settings.llm.test", summary=result.message)
            return result

    result = TestResult(
        ok=False,
        message=f"不支持的 LLM_PROVIDER={s.llm_provider}。",
        detail={"tested_at": tested_at, "provider": s.llm_provider},
    )
    audit_service.record(db, user_id=user.user_id, action="settings.llm.test", summary=result.message)
    return result


@router.post("/reload", response_model=TestResult)
def reload_settings(_: CurrentUserDep):
    """清空 Settings lru_cache,下次请求重新读取 .env。"""
    get_settings.cache_clear()
    return TestResult(ok=True, message="已清空配置缓存,下次请求将重新读取 .env。")
