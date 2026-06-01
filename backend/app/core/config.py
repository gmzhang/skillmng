"""应用配置。

所有可调参数集中在 Settings 中,通过环境变量或 .env 文件注入。
PRD §15 列出了完整字段;敏感字段不得写入日志。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    """运行时配置。"""

    model_config = SettingsConfigDict(
        # 顺序:仓库根 .env → 仓库根 .env.local → backend/.env → backend/.env.local
        # 后者覆盖前者;.env.local 永远不进 git。
        env_file=(
            str(_REPO_ROOT / ".env"),
            str(_REPO_ROOT / ".env.local"),
            str(_BACKEND_DIR / ".env"),
            str(_BACKEND_DIR / ".env.local"),
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用
    app_env: str = "local"
    database_url: str = "sqlite:///./data/skillmng.sqlite3"

    # Cookie 字段名
    cookie_user_id_key: str = "user_id"
    cookie_user_name_key: str = "user_name"
    cookie_user_email_key: str = "user_email"

    # 本地开发兜底身份:Cookie 缺失时使用。空字符串 = 不兜底(测试 / 生产)
    mock_user_id: str = ""
    mock_user_name: str = ""
    mock_user_email: str = ""

    # Git 托管
    skill_git_group_url: str = ""
    skill_git_repo_url_template: str = ""
    skill_git_workdir: str = "./data/git/skill-repos"
    skill_git_ssh_key: str = ""
    skill_git_api_token: str = ""
    skill_git_author_name: str = "zhangguangming"
    skill_git_author_email: str = "zhangguangming.zgm@antgroup.com"
    skill_create_tags: bool = True

    # AntCode API (code.myxiaojin.cn / api/v3)
    antcode_api_base_url: str = "https://code.myxiaojin.cn/api/v3"
    antcode_group_url: str = "https://code.myxiaojin.cn/groups/xiaojin-skills"
    antcode_namespace_id: int = 354800126
    antcode_private_token: str = ""
    skill_default_branch: str = "master"
    skill_draft_branch_prefix: str = "draft"
    skill_delete_draft_branch_after_publish: bool = False

    # Proxy
    https_proxy: str = ""
    http_proxy: str = ""
    all_proxy: str = ""

    # LLM — SKILL_LLM_* 优先,fallback 到 ANTHROPIC_* (但后者会被 Claude Code 覆盖)
    llm_provider: str = "mock"
    llm_api_style: str = "auto"  # auto | anthropic | openai-compatible
    skill_llm_base_url: str = ""
    skill_llm_api_key: str = ""
    skill_llm_model: str = ""
    disable_prompt_caching: int = 0
    anthropic_base_url: str = ""
    anthropic_api_key: str = ""
    anthropic_auth_token: str = ""
    anthropic_model: str = "qwen3.6-plus"
    anthropic_default_haiku_model: str = "claude-opus-4-6"
    anthropic_default_haiku_model_name: str = "claude-opus-4-6"
    anthropic_default_opus_model: str = "claude-opus-4-6"
    anthropic_default_opus_model_name: str = "claude-opus-4-6"
    anthropic_default_sonnet_model: str = "claude-opus-4-6"
    anthropic_default_sonnet_model_name: str = "claude-opus-4-6"
    api_timeout_ms: int = 3_000_000
    claude_code_disable_experimental_betas: int = 1
    claude_code_disable_nonessential_traffic: int = 1
    disable_autoupdater: int = 1

    # 上传上限
    max_upload_bytes: int = 20 * 1024 * 1024
    max_file_bytes: int = 2 * 1024 * 1024
    max_asset_file_bytes: int = 10 * 1024 * 1024
    max_files_per_skill: int = 500

    # CORS allow origin (前端 dev)
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @property
    def git_workdir_path(self) -> Path:
        return Path(self.skill_git_workdir).resolve()

    @property
    def httpx_proxy(self) -> str | None:
        """Return proxy URL for httpx outbound calls (HTTPS preferred)."""
        return self.https_proxy or self.http_proxy or self.all_proxy or None

    @property
    def llm_api_key(self) -> str:
        """Effective LLM API key. SKILL_LLM_API_KEY > ANTHROPIC_API_KEY > ANTHROPIC_AUTH_TOKEN."""
        return self.skill_llm_api_key or self.anthropic_api_key or self.anthropic_auth_token

    @property
    def llm_base_url(self) -> str:
        """Effective LLM base URL. SKILL_LLM_BASE_URL > ANTHROPIC_BASE_URL."""
        return self.skill_llm_base_url or self.anthropic_base_url

    @property
    def llm_model(self) -> str:
        """Effective LLM model. SKILL_LLM_MODEL > ANTHROPIC_MODEL."""
        return self.skill_llm_model or self.anthropic_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
