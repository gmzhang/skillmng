"""AntCode (code.myxiaojin.cn) API 客户端。

AntCode 使用 /api/v3/(基于 GitLab,接口名/参数有偏差),认证用 PRIVATE-TOKEN header。
关键 AntCode 差异参见 doc/antcode-api-guide.md:
- 创建项目: POST /projects/  (尾斜杠必须)
- 创建分支: POST /projects/{id}/repository/branches  参数 branch_name(不是 branch)
- 创建文件: POST /projects/{id}/repository/files    参数 branch_name(不是 branch)
- 读文件:  GET  /projects/{id}/repository/blobs/HEAD?filepath=...
- PR/合并通过 API 不可靠;P3 改走本地 clone + git merge + push。

token 不入日志(httpx 默认不打印 header 即可);本模块的所有方法都通过 settings 读 token。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import BusinessError

_LOGGER = logging.getLogger("app.antcode")


class AntCodeError(BusinessError):
    """AntCode API 调用错误。"""

    code = "antcode_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 502,
        antcode_status: int | None = None,
        body: str | None = None,
    ):
        super().__init__(message, code="antcode_error", status_code=status_code)
        self.antcode_status = antcode_status
        self.body = body


@dataclass(frozen=True)
class AntCodeProject:
    id: int
    name: str
    path: str
    path_with_namespace: str
    http_url_to_repo: str
    ssh_url_to_repo: str
    web_url: str
    default_branch: str | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class AntCodeBranch:
    name: str
    commit_sha: str | None
    raw: dict[str, Any]


def _summarize_response(resp: httpx.Response, limit: int = 200) -> str:
    text = resp.text or ""
    if len(text) > limit:
        text = text[:limit] + "..."
    return f"HTTP {resp.status_code} {resp.request.method} {resp.request.url.path} :: {text}"


class AntCodeClient:
    """轻量 AntCode REST 客户端。"""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        timeout: float = 20.0,
        proxy: str | None = None,
    ):
        if not token:
            raise BusinessError(
                "ANTCODE_PRIVATE_TOKEN 未配置,无法访问 AntCode API。",
                code="antcode_token_missing",
            )
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            headers={
                "PRIVATE-TOKEN": token,
                "Accept": "application/json",
            },
            proxy=proxy or None,
        )

    # ---- 上下文管理 ----

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "AntCodeClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ---- 内部 ----

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        try:
            resp = self._client.request(method, path, json=json, params=params)
        except httpx.RequestError as e:
            raise AntCodeError(
                f"无法连接 AntCode: {type(e).__name__}",
                status_code=503,
            )
        if resp.status_code >= 400:
            _LOGGER.warning("antcode call failed: %s", _summarize_response(resp))
            raise AntCodeError(
                f"AntCode 返回 {resp.status_code}",
                antcode_status=resp.status_code,
                body=resp.text[:500] if resp.text else None,
            )
        return resp

    def _json(self, resp: httpx.Response) -> Any:
        try:
            return resp.json()
        except ValueError as e:
            raise AntCodeError(f"AntCode 返回非 JSON: {e}") from e

    # ---- API ----

    def get_user(self) -> dict[str, Any]:
        return self._json(self._request("GET", "/user"))

    def get_group(self, group_id: int) -> dict[str, Any]:
        return self._json(self._request("GET", f"/groups/{group_id}"))

    def list_group_projects(
        self, group_id: int, *, search: str | None = None, per_page: int = 100
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"per_page": per_page}
        if search:
            params["search"] = search
        return self._json(
            self._request("GET", f"/groups/{group_id}/projects", params=params)
        )

    def get_project(self, project_id: int) -> AntCodeProject:
        data = self._json(self._request("GET", f"/projects/{project_id}"))
        return self._project_from(data)

    def get_project_by_path(self, path_with_namespace: str) -> AntCodeProject:
        encoded = quote(path_with_namespace, safe="")
        data = self._json(self._request("GET", f"/projects/{encoded}"))
        return self._project_from(data)

    def create_project(
        self,
        *,
        name: str,
        path: str,
        namespace_id: int,
        description: str | None = None,
        visibility: str = "private",
        initialize_with_readme: bool = True,
    ) -> AntCodeProject:
        body: dict[str, Any] = {
            "name": name,
            "path": path,
            "namespace_id": namespace_id,
            "visibility": visibility,
            "initialize_with_readme": initialize_with_readme,
        }
        if description:
            body["description"] = description
        # /projects/ 的尾斜杠是必要的(参见 antcode-api-guide.md §5.1)
        data = self._json(self._request("POST", "/projects/", json=body))
        return self._project_from(data)

    def list_branches(self, project_id: int) -> list[AntCodeBranch]:
        data = self._json(
            self._request("GET", f"/projects/{project_id}/repository/branches")
        )
        return [self._branch_from(b) for b in data]

    def get_branch(self, project_id: int, branch_name: str) -> AntCodeBranch | None:
        encoded = quote(branch_name, safe="")
        try:
            data = self._json(
                self._request(
                    "GET",
                    f"/projects/{project_id}/repository/branches/{encoded}",
                )
            )
        except AntCodeError as e:
            if e.antcode_status == 404:
                return None
            raise
        return self._branch_from(data)

    def create_branch(
        self,
        project_id: int,
        *,
        branch_name: str,
        ref: str,
    ) -> AntCodeBranch:
        data = self._json(
            self._request(
                "POST",
                f"/projects/{project_id}/repository/branches",
                json={"branch_name": branch_name, "ref": ref},
            )
        )
        return self._branch_from(data)

    def delete_branch(self, project_id: int, branch_name: str) -> None:
        encoded = quote(branch_name, safe="")
        self._request(
            "DELETE",
            f"/projects/{project_id}/repository/branches/{encoded}",
        )

    def list_tags(self, project_id: int) -> list[AntCodeBranch]:
        data = self._json(
            self._request("GET", f"/projects/{project_id}/repository/tags")
        )
        return [
            AntCodeBranch(
                name=t.get("name", ""),
                commit_sha=t.get("commit", {}).get("id"),
                raw=t,
            )
            for t in data
        ]

    def list_tree(
        self, project_id: int, *, ref: str, path: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"ref": ref}
        if path:
            params["path"] = path
        return self._json(
            self._request(
                "GET", f"/projects/{project_id}/repository/tree", params=params
            )
        )

    def list_commits(
        self, project_id: int, *, ref: str, per_page: int = 20
    ) -> list[dict[str, Any]]:
        return self._json(
            self._request(
                "GET",
                f"/projects/{project_id}/repository/commits",
                params={"ref": ref, "per_page": per_page},
            )
        )

    def get_branch_head_sha(self, project_id: int, branch_name: str) -> str | None:
        branch = self.get_branch(project_id, branch_name)
        return branch.commit_sha if branch else None

    # ---- 适配 ----

    def _project_from(self, data: dict[str, Any]) -> AntCodeProject:
        return AntCodeProject(
            id=int(data["id"]),
            name=data.get("name", ""),
            path=data.get("path", ""),
            path_with_namespace=data.get("path_with_namespace", ""),
            http_url_to_repo=data.get("http_url_to_repo", ""),
            ssh_url_to_repo=data.get("ssh_url_to_repo", ""),
            web_url=data.get("web_url", ""),
            default_branch=data.get("default_branch"),
            raw=data,
        )

    @staticmethod
    def _branch_from(data: dict[str, Any]) -> AntCodeBranch:
        commit = data.get("commit") or {}
        return AntCodeBranch(
            name=data.get("name", ""),
            commit_sha=commit.get("id") or commit.get("sha"),
            raw=data,
        )


def build_client(settings: Settings | None = None) -> AntCodeClient:
    """工厂:用全局 Settings 创建一个 client。"""
    settings = settings or get_settings()
    return AntCodeClient(
        base_url=settings.antcode_api_base_url,
        token=settings.antcode_private_token,
        proxy=settings.httpx_proxy,
    )


def is_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(settings.antcode_private_token.strip())


def mask_token(token: str | None) -> str:
    """token 掩码,用于设置页展示。"""
    if not token:
        return ""
    s = token.strip()
    if len(s) <= 6:
        return "***"
    return s[:3] + "***" + s[-3:]
