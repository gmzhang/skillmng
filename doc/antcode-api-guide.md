# AntCode (code.myxiaojin.cn) API 操作指南

> 本文档适用于 Agent 自动化操作 AntCode 仓库和群组。  
> 最后更新：2026-05-26  
> 实测环境：code.myxiaojin.cn（消金 AntCode 实例）

---

## 1. 基础信息

| 项 | 值 |
|---|---|
| **平台** | AntCode（基于 GitLab，大量定制） |
| **实例地址** | `https://code.myxiaojin.cn` |
| **API 基地址** | `https://code.myxiaojin.cn/api/v3/` |
| **认证方式** | `PRIVATE-TOKEN` Header |
| **Token 获取** | 浏览器登录 → `https://code.myxiaojin.cn/profile/personal_access_tokens` → 创建访问令牌（勾选 `api` 权限） |
| **当前 Token** | `<ANTCODE_PRIVATE_TOKEN>`（需从 .env.local 读取,不得写入代码或文档） |
| **当前用户 ID** | `88300363`（username: `zhangguangming.zgm`，花名: 十宁，工号: 299987） |

### ⚠️ 安全提示

> **历史版本曾包含明文 token 示例,该 token 已暴露,必须立即旋转!**
> 旋转步骤:浏览器打开 `https://code.myxiaojin.cn/profile/personal_access_tokens` → 撤销旧 token → 创建新 token → 更新 `.env.local` 中的 `ANTCODE_PRIVATE_TOKEN`。

### ⚠️ 关注意事项

- **必须用 `/api/v3/`**，不是 `/api/v4/`！
- `/api/v4/` 只支持 **GET 查询项目列表和项目详情**，写操作（POST/PUT/DELETE）全部返回 `400 "POST not supported"`
- `/api/v3/` 支持完整的读写操作
- `/webapi/` 需要浏览器 BUC Session Cookie，**PRIVATE-TOKEN 无效**
- 权限等级：`10=Guest` `20=Reporter` `30=Developer` `40=Master/Maintainer` `50=Owner`

---

## 2. API 可用性速查表

| 端点 | GET | POST | PUT | DELETE |
|---|---|---|---|---|
| `/api/v3/projects/` | ⚠️ 未测 | ✅ 创建仓库 | ❌ | ❌ |
| `/api/v3/projects/{id}` | ✅ 项目详情 | — | ✅ 更新项目 | ❌ (405 非管理员) |
| `/api/v3/groups` | — | ✅ 创建群组 | — | ❌ (400) |
| `/api/v3/groups/{id}` | ✅ 群组详情 | — | — | ❌ (400) |
| `/api/v3/groups/{id}/projects` | ✅ 群组下项目 | — | — | — |
| `/api/v3/groups/{id}/members` | ✅ 群组成员 | ❌ (403) | — | — |
| `/api/v3/groups/owned` | ✅ 我拥有的群组 | — | — | — |
| `/api/v3/namespaces/owned` | ✅ 我拥有的命名空间 | — | — | — |
| `/api/v3/projects/{id}/members` | ✅ 项目成员 | ❌ (500) | — | — |
| `/api/v3/projects/{id}/repository/branches` | ✅ 分支列表 | ✅ 创建分支 | — | ✅ 删除分支 |
| `/api/v3/projects/{id}/repository/commits` | ✅ 提交列表 | — | — | — |
| `/api/v3/projects/{id}/repository/tree` | ✅ 文件树 | — | — | — |
| `/api/v3/projects/{id}/repository/files` | — | ✅ 创建文件 | — | — |
| `/api/v3/projects/{id}/repository/blobs/{sha}` | ✅ 文件内容 | — | — | — |
| `/api/v3/projects/{id}/pull_requests` | ✅ MR/PR 列表 | ❌ (400) | — | — |
| `/api/v3/projects/{id}/pull_requests/{iid}` | ✅ MR/PR 详情 | — | ⚠️ 合并(未验证成功) | — |
| `/api/v3/projects/{id}/hooks` | ✅ Webhook 列表 | — | — | — |
| `/api/v3/projects/{id}/keys` | ✅ 部署密钥 | — | — | — |
| `/api/v3/user` | ✅ 当前用户 | — | — | — |
| `/api/v4/projects` | ✅ 项目列表 | ❌ (400) | ❌ | ❌ |
| `/api/v4/projects/{id}` | ✅ 项目详情 | — | ❌ | ❌ |
| `/api/v4/groups` | ❌ (404) | — | — | — |
| `/api/v4/user` | ❌ (404) | — | — | — |
| `/webapi/*` | ❌ 需 BUC Cookie | ❌ 需 BUC Cookie | ❌ 需 BUC Cookie | ❌ 需 BUC Cookie |

---

## 3. 认证

### 3.1 Personal Access Token

所有 API 请求通过 `PRIVATE-TOKEN` Header 认证：

```bash
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/user"
```

### 3.2 创建新 Token

1. 浏览器打开 `https://code.myxiaojin.cn/profile/personal_access_tokens`
2. BUC 登录
3. 点击「创建令牌」
4. 勾选权限范围（至少 `api`）
5. 设置过期时间
6. 复制生成的 Token（**只显示一次**）

### 3.3 用户信息

```bash
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/user"
```

响应示例：
```json
{
  "id": 88300363,
  "username": "zhangguangming.zgm",
  "name": "十宁",
  "email": "zhangguangming.zgm@antgroup.com",
  "extern_uid": "299987",
  "department": "蚂蚁消金-信息科技部-信贷平台",
  "can_create_group": true,
  "can_create_project": null,
  "avatar_url": "https://work.antfinancial-corp.com/photo/299987.80x80.jpg"
}
```

---

## 4. 群组操作

### 4.1 获取我拥有的群组

```bash
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/groups/owned"
```

响应：每个群组包含 `id`、`name`、`path`、`description`、`public`、`web_url` 等字段。

### 4.2 获取群组详情

```bash
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/groups/{group_id}"
```

### 4.3 获取群组下的项目列表

```bash
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/groups/{group_id}/projects"
```

### 4.4 获取群组成员

```bash
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/groups/{group_id}/members"
```

### 4.5 创建群组

```bash
curl -s -X POST -H "PRIVATE-TOKEN: $TOKEN" \
  -H "Content-Type: application/json" \
  "https://code.myxiaojin.cn/api/v3/groups" \
  -d '{
    "name": "群组名称",
    "path": "group-path",
    "description": "群组描述",
    "visibility_level": 0
  }'
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | ✅ | 群组显示名称 |
| `path` | string | ✅ | 群组路径（URL 用） |
| `description` | string | ❌ | 群组描述 |
| `visibility_level` | int | ❌ | 0=private, 10=internal, 20=public |

### 4.6 删除群组

> ❌ **不支持** — DELETE `/api/v3/groups/{id}` 返回 `400 "DELETE not supported"`

### 4.7 已知群组

| 群组 | ID | 路径 | 描述 |
|---|---|---|---|
| openclaw | 349500383 | openclaw | — |
| xiaojin-skills | 354800126 | xiaojin-skills | 消金skill库 |

---

## 5. 仓库操作

### 5.1 创建仓库（在群组下）

```bash
curl -s -X POST -H "PRIVATE-TOKEN: $TOKEN" \
  -H "Content-Type: application/json" \
  "https://code.myxiaojin.cn/api/v3/projects/" \
  -d '{
    "name": "仓库名称",
    "path": "repo-path",
    "namespace_id": 354800126,
    "visibility": "private",
    "initialize_with_readme": true
  }'
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | ✅ | 仓库显示名称 |
| `path` | string | ✅ | 仓库路径（URL 用，建议与 name 一致） |
| `namespace_id` | int | ✅ | 群组 ID（从 `groups/owned` 获取） |
| `visibility` | string | ❌ | `private` / `internal` / `public`，默认 `private` |
| `description` | string | ❌ | 仓库描述 |
| `initialize_with_readme` | bool | ❌ | 是否初始化 README |

响应示例：
```json
{
  "id": 327200665,
  "name": "test",
  "path_with_namespace": "xiaojin-skills/test",
  "http_url_to_repo": "https://code.myxiaojin.cn/xiaojin-skills/test.git",
  "ssh_url_to_repo": "git@code.myxiaojin.cn:cqcfd7cn/xiaojin-skills/test.git",
  "namespace": {
    "id": 354800126,
    "path": "xiaojin-skills"
  }
}
```

### 5.2 获取项目详情

```bash
# 按 ID
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/projects/{project_id}"

# 按 path_with_namespace（URL 编码）
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/projects/xiaojin-skills%2Ftest"
```

### 5.3 搜索项目

```bash
# v3 搜索
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/projects?search=关键词&per_page=20"

# v4 搜索（仅支持 GET）
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v4/projects?search=关键词&per_page=20"
```

### 5.4 更新项目

```bash
curl -s -X PUT -H "PRIVATE-TOKEN: $TOKEN" \
  -H "Content-Type: application/json" \
  "https://code.myxiaojin.cn/api/v3/projects/{project_id}" \
  -d '{
    "description": "新的描述",
    "visibility": "internal"
  }'
```

### 5.5 删除项目

> ⚠️ **非管理员不可用** — 返回 `405 "Delete project is invalid as api for non admin"`

需要管理员权限或通过 Web UI 操作。

---

## 6. 仓库内容操作

### 6.1 获取文件树

```bash
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/projects/{project_id}/repository/tree?ref=main&path=docs"
```

| 参数 | 说明 |
|---|---|
| `ref` | 分支名或 commit SHA |
| `path` | 子目录路径（可选） |

响应：
```json
[
  {"id": "sha...", "mode": "040000", "name": "docs", "path": "docs", "type": "tree"},
  {"id": "sha...", "mode": "100644", "name": "README.md", "path": "README.md", "type": "blob"}
]
```

### 6.2 读取文件内容

```bash
# 方式 1：通过 blob SHA（从 tree API 获取 SHA）
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/projects/{project_id}/repository/blobs/{blob_sha}?filepath=README.md"

# 方式 2：通过 HEAD + filepath
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/projects/{project_id}/repository/blobs/HEAD?filepath=README.md"
```

> ⚠️ `/api/v3/projects/{id}/repository/files/{path}` 和 `/api/v3/.../files/{path}/raw` 均返回 404，**不可用**。  
> ✅ 使用 `blobs/HEAD?filepath=xxx` 方式读取文件内容。

### 6.3 创建文件（通过 API）

```bash
CONTENT=$(python3 -c "import base64;print(base64.b64encode(b'文件内容\n').decode())")

curl -s -X POST -H "PRIVATE-TOKEN: $TOKEN" \
  -H "Content-Type: application/json" \
  "https://code.myxiaojin.cn/api/v3/projects/{project_id}/repository/files" \
  -d "{
    \"file_path\": \"新文件.md\",
    \"branch_name\": \"main\",
    \"content\": \"$CONTENT\",
    \"commit_message\": \"Add 新文件.md\"
  }"
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file_path` | string | ✅ | 文件路径 |
| `branch_name` | string | ✅ | 目标分支（注意：不是 `branch`，是 `branch_name`） |
| `content` | string | ✅ | Base64 编码的文件内容 |
| `commit_message` | string | ✅ | 提交信息 |

> ⚠️ 参数名是 `branch_name` 不是 `branch`（标准 GitLab API 用 `branch`，AntCode 用 `branch_name`）。

### 6.4 获取提交列表

```bash
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/projects/{project_id}/repository/commits?ref=main"
```

---

## 7. 分支操作

### 7.1 列出分支

```bash
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/projects/{project_id}/repository/branches"
```

### 7.2 创建分支

```bash
curl -s -X POST -H "PRIVATE-TOKEN: $TOKEN" \
  -H "Content-Type: application/json" \
  "https://code.myxiaojin.cn/api/v3/projects/{project_id}/repository/branches" \
  -d '{
    "branch_name": "feature/new-feature",
    "ref": "main"
  }'
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `branch_name` | string | ✅ | 新分支名（注意：不是 `branch`，是 `branch_name`） |
| `ref` | string | ✅ | 基于的分支或 SHA |

### 7.3 删除分支

```bash
curl -s -X DELETE -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/projects/{project_id}/repository/branches/{branch_name}"
```

> ✅ 已验证可正常工作。

---

## 8. 合并请求 (Pull Request) 操作

### 8.1 列出 PR

```bash
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/projects/{project_id}/pull_requests?state=opened"
```

> ⚠️ AntCode 用 `pull_requests`，不是 `merge_requests`。

### 8.2 获取 PR 详情

```bash
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/projects/{project_id}/pull_requests/{iid}"
```

### 8.3 创建 PR

> ❌ **POST 不支持** — `POST /api/v3/projects/{id}/pull_requests` 返回 `400 "POST not supported"`

需要通过 Web UI 或 `/webapi/` 端点（需 BUC Cookie）创建 PR。

### 8.4 合并 PR

> ⚠️ 未验证成功 — `PUT .../pull_requests/{iid}/merge` 和 `PUT .../pull_requests/{iid}` 均返回空响应（`state: None`）。

可能的解决方案：
- 通过 Web UI 合并
- 通过 BUC Cookie 调用 `/webapi/` 端点

---

## 9. 成员操作

### 9.1 获取项目成员

```bash
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/projects/{project_id}/members"
```

### 9.2 获取群组成员

```bash
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/groups/{group_id}/members"
```

### 9.3 添加成员

> ❌ **POST 返回 500（项目）或 403（群组）** — 可能需要更高级别权限或管理员权限。

---

## 10. Git 操作

### 10.1 HTTPS 克隆

```bash
git clone https://code.myxiaojin.cn/{group_path}/{repo_path}.git
```

凭据会从 macOS Keychain 自动读取（`security find-internet-password -s code.myxiaojin.cn`）。

### 10.2 SSH 克隆

```bash
git clone git@code.myxiaojin.cn:cqcfd7cn/{group_path}/{repo_path}.git
```

> ⚠️ SSH URL 中包含 tenant path `cqcfd7cn`，与 HTTPS URL 不同。

### 10.3 完整的 Git 推送流程

```bash
git clone https://code.myxiaojin.cn/xiaojin-skills/test.git
cd test
git config user.email "zhangguangming.zgm@antgroup.com"
git config user.name "十宁"
# 添加/修改文件
git add -A
git commit -m "Your commit message"
git push
```

---

## 11. 速查：最常用操作

### 在群组下创建仓库

```bash
# 1. 获取群组 ID
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://code.myxiaojin.cn/api/v3/groups/owned"

# 2. 创建仓库
curl -s -X POST -H "PRIVATE-TOKEN: $TOKEN" \
  -H "Content-Type: application/json" \
  "https://code.myxiaojin.cn/api/v3/projects/" \
  -d '{
    "name": "新仓库",
    "path": "new-repo",
    "namespace_id": 354800126,
    "visibility": "private"
  }'
```

### 创建分支 + 推送文件 + 创建 PR

```bash
# 创建分支
curl -s -X POST -H "PRIVATE-TOKEN: $TOKEN" \
  -H "Content-Type: application/json" \
  "https://code.myxiaojin.cn/api/v3/projects/{id}/repository/branches" \
  -d '{"branch_name": "feature/xxx", "ref": "main"}'

# 在分支上创建文件
CONTENT=$(python3 -c "import base64;print(base64.b64encode(b'内容\n').decode())")
curl -s -X POST -H "PRIVATE-TOKEN: $TOKEN" \
  -H "Content-Type: application/json" \
  "https://code.myxiaojin.cn/api/v3/projects/{id}/repository/files" \
  -d "{\"file_path\": \"new-file.md\", \"branch_name\": \"feature/xxx\", \"content\": \"$CONTENT\", \"commit_message\": \"Add file\"}"

# 创建 PR → ❌ API 不支持，需通过 Web UI
```

---

## 12. 与标准 GitLab API 的差异

| 标准 GitLab API | AntCode 实际情况 | 说明 |
|---|---|---|
| `POST /api/v4/projects` | ❌ 400 "POST not supported" | 创建仓库必须用 `/api/v3/projects/` |
| `GET /api/v4/groups` | ❌ 404 | 用 `/api/v3/groups/owned` |
| `GET /api/v4/namespaces` | ❌ 404 | 用 `/api/v3/namespaces/owned` |
| `GET /api/v4/user` | ❌ 404 | 用 `/api/v3/user` |
| `merge_requests` | `pull_requests` | 端点名不同 |
| `branch` 参数 | `branch_name` | 参数名不同 |
| `DELETE /api/v3/groups/{id}` | ❌ 400 | 不支持删除群组 |
| `DELETE /api/v3/projects/{id}` | ❌ 405 | 非管理员无法删除项目 |
| `POST /api/v3/.../pull_requests` | ❌ 400 | 不支持通过 API 创建 PR |
| `/api/v3/.../repository/files/{path}` | ❌ 404 | 用 `blobs/HEAD?filepath=xxx` |
| `fork` 项目 | ❌ 400 | 不支持通过 API fork |
| `/webapi/*` | ❌ 需要 BUC Cookie | PRIVATE-TOKEN 无效 |

---

## 13. 错误码参考

| HTTP 状态码 | 含义 |
|---|---|
| `200` | 成功 |
| `400` | 请求方法不支持或参数错误 |
| `401` | 未认证（Token 无效或过期） |
| `403` | 权限不足 |
| `404` | 端点不存在 |
| `405` | 方法不允许（如非管理员删除项目） |
| `500` | 服务器错误（如添加成员失败） |