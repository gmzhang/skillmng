# Skill 管理系统需求规格说明书

版本：v0.1  
日期：2026-05-25  
目标读者：产品、设计、前端 Agent、后端 Agent、测试 Agent、运维 Agent

## 1. 背景与目标

Skill 是面向 Agent 的可复用能力包，通常以一个目录承载，核心入口是 `SKILL.md`，并可按需包含 `scripts/`、`references/`、`assets/` 等资源。Skill 的价值在于把稳定流程、领域知识、工具调用方式和执行约束封装起来，让 Agent 在合适的任务中通过描述触发并渐进加载详细内容。

本项目要建设一个 Skill 管理系统，支持多租户隔离、Skill 创建、Skill 更新、LLM 辅助优化、多版本管理、Git 托管、审核与发布。系统第一阶段以 sqlite 降低部署复杂度，以 Python3 后端和流行 TypeScript 前端框架实现。

### 1.1 参考资料

公开资料应作为第一阶段 Skill 规范和 LLM 提示工程的基础输入：

- Claude Code Skills 文档：<https://code.claude.com/docs/en/skills>
- Anthropic Skill Creator：<https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md>
- Anthropic Frontend Design Skill：<https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md>
- Eigent Skill Creator 页面：<https://www.eigent.ai/ja/skills/coding-agents-and-ides/skill-creator>
- Gemini CLI Creating Skills：<https://geminicli.com/docs/cli/creating-skills/>
- Agent Skills 社区：<https://agentskills.io/home>

公司 Skill 规范已沉淀在本仓库 [doc/guifan.md](/Users/zhangguangming/Desktop/work/code/skillmng/doc/guifan.md)，其要求优先级高于公开资料。系统设计仍需预留“组织级规范扩展层”，便于后续继续合并内网规范。

## 2. 产品范围

### 2.1 第一阶段必须交付

1. 用户进入系统时默认已登录，后端从 Cookie 读取 `user_id`，并以 `user_id` 作为租户隔离依据。
2. Skill 列表、详情、创建、更新、删除、版本查看、版本对比、版本恢复。
3. LLM 辅助创建 Skill：用户输入目标、场景、约束、示例材料，系统生成符合规范的 Skill 草稿。
4. LLM 辅助更新 Skill：用户输入修改目标或上传已有 Skill，系统给出结构化 diff 与优化说明。
5. Skill 文件管理：支持 `SKILL.md`、`scripts/`、`references/`、`assets/` 的展示、编辑、上传、下载。
6. Git 版本管理：一个 Skill 对应一个独立代码仓库，所有 Skill 仓库统一归属到公司内部 Git group，并通过 commit/tag/branch 记录版本。
7. sqlite 持久化：保存用户、Skill 元数据、版本索引、操作记录、LLM 任务记录。
8. 基础权限：用户只能看到和操作自己租户下的 Skill。
9. 基础审计：记录创建、更新、删除、生成、发布、恢复等操作。
10. 可本地启动，提供清晰的 `.env.example` 和启动说明。

### 2.2 第一阶段不做

1. 不接入复杂企业 SSO，只从 Cookie 获取 `user_id`。
2. 不实现跨用户协作编辑。
3. 不实现在线代码沙箱执行 Skill 脚本。
4. 不把公司内网规范写死进代码，只预留规则插件接口。
5. 不在仓库中提交真实 LLM token、SSH 私钥或任何敏感凭证。

## 3. 关键概念

### 3.1 Skill

一个 Skill 是一个目录，至少包含：

```text
skill-name/
  SKILL.md
```

可选包含：

```text
skill-name/
  scripts/
  references/
  assets/
  examples/
  tests/
```

`SKILL.md` 必须包含 YAML front matter：

```yaml
---
name: skill-name
description: One concise trigger-oriented description.
argument-hint: "[optional-argument]"
disable-model-invocation: false
user-invocable: true
---
```

`name` 应短小、唯一、可读，推荐使用 kebab-case。  
`description` 是 Agent 选择 Skill 的关键触发信息，必须说明“什么时候使用这个 Skill”，而不是泛泛描述文件内容。

Front matter 字段要求：

- `name`：必填，作为 `/skill-name` 调用命令，只允许小写字母、数字、连字符，最长 64 个字符。
- `description`：必填，按“功能说明 + 使用场景 + 关键词”编写，支持中英双语。
- `argument-hint`：可选，显示在命令补全中，例如 `[filename]`。
- `disable-model-invocation`：可选布尔值，若为 `true`，表示禁止 AI 自动调用，仅允许手动触发。
- `user-invocable`：可选布尔值，控制是否在 `/` 菜单中显示。

### 3.2 Skill 版本

系统中的版本分为两层：

- Git 版本：由 Git commit SHA 作为真实不可篡改版本。
- 产品版本：由系统生成的语义化版本号，例如 `0.1.0`、`0.2.0`、`1.0.0`，并映射到 Git commit SHA。

第一阶段要求：

- 每次发布 Skill 版本必须创建 Git commit。
- 允许为稳定版本创建 Git tag，tag 格式为 `v{version}`，因为每个 Skill 已经是独立仓库。
- sqlite 中保存版本索引，便于快速查询和 UI 展示。

## 4. 用户与租户

### 4.1 登录假设

默认页面进入时已经登录。后端从 Cookie 读取：

- `user_id`：必需，租户隔离主键。
- `user_name`：可选，用于展示。
- `user_email`：可选，用于 Git author 或审计展示。

若缺少 `user_id`：

- API 返回 `401 Unauthorized`。
- 前端展示“无法识别登录用户”的错误页，不提供匿名模式。

### 4.2 多租户隔离

所有 API 查询必须带上从 Cookie 解析出的 `user_id` 过滤条件。前端传入的 `user_id` 不可信，后端不得使用请求 body 或 query 中的 `user_id` 作为租户依据。

Git group 下每个 Skill 独立仓库，仓库内推荐目录结构：

```text
{skill_repo}/
  SKILL.md
  scripts/
  references/
  assets/
  examples/
  tests/
```

多租户隔离不再依赖 Git 仓库内的租户目录，而是依赖 sqlite 元数据中的 `user_id` 与 Skill 仓库映射。路径仍必须做安全校验，禁止 `../`、绝对路径、空字节和不可见控制字符。

## 5. 技术栈要求

### 5.1 前端

必须使用流行 TypeScript 技术栈。推荐：

- React + TypeScript + Vite。
- TanStack Query 处理 API 状态。
- React Router 处理页面路由。
- Monaco Editor 或 CodeMirror 处理 Markdown/YAML/代码编辑。
- Tailwind CSS 或成熟组件库处理基础 UI。

前端设计应参考 Anthropic frontend-design Skill 的原则：真实可用的工作台优先，不做营销式落地页；界面安静、密度适中、易扫描；工具按钮使用图标和 tooltip；状态、空态、错误态完整。

### 5.2 后端

必须使用 Python3。推荐：

- FastAPI。
- Pydantic v2。
- SQLAlchemy 2.x。
- Alembic。
- sqlite。
- GitPython 或原生 `git` CLI 封装。
- httpx 调用 LLM API。

### 5.3 数据库

第一阶段使用 sqlite，文件默认：

```text
./data/skillmng.sqlite3
```

后续需能平滑迁移到 PostgreSQL，因此 ORM 层不要使用 sqlite 专属特性作为核心逻辑。

### 5.4 Git Group 与 Skill 仓库

Skill 内容托管到公司内部 Git group：

```text
https://code.myxiaojin.cn/groups/xiaojin-skills
```

期望结果：一个 Skill 就是一个独立代码仓库。系统需要维护 Skill 与仓库的映射关系。

本地操作必须使用：

```text
/Users/zhangguangming/.ssh
```

实现要求：

- 后端启动时检查本地仓库根目录是否存在，不存在则创建。
- Skill 首次发布时，在 Git group 下创建或绑定独立仓库。
- 若配置了 Git 平台 API token，则系统可自动创建仓库；否则允许管理员先手动创建仓库，再在系统中绑定 remote URL。
- 仓库存在于本地则 fetch，不存在则 clone。
- 每个 Skill 仓库使用独立本地目录，避免不同 Skill 发布时互相影响。
- 所有网络命令默认支持代理环境变量：

```bash
export https_proxy=http://127.0.0.1:1235
export http_proxy=http://127.0.0.1:1235
export all_proxy=socks5://127.0.0.1:1234
```

推荐本地路径：

```text
./data/git/skill-repos/{repo_slug}
```

SSH 调用应通过环境变量配置，不要硬编码私钥文件内容：

```bash
GIT_SSH_COMMAND="ssh -i /Users/zhangguangming/.ssh/id_rsa -o IdentitiesOnly=yes"
```

实际私钥文件名应可通过环境变量覆盖。

## 6. LLM 集成要求

### 6.1 配置

系统必须支持通过环境变量读取 LLM 配置。不得把真实 token 提交到仓库。

`.env.example` 应包含：

```bash
DISABLE_PROMPT_CACHING=0
ANTHROPIC_BASE_URL=https://idealab.alibaba-inc.com/api/anthropic
ANTHROPIC_AUTH_TOKEN=replace-with-your-token
ANTHROPIC_MODEL=claude-opus-4-6
ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-6
ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-opus-4-6
ANTHROPIC_DEFAULT_SONNET_MODEL=claude-opus-4-6
CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1
DISABLE_AUTOUPDATER=1
API_TIMEOUT_MS=3000000
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

后端需要提供统一 LLM client，支持：

- 超时配置。
- 重试。
- 错误记录。
- 请求和响应摘要审计。
- 禁止记录完整敏感输入和 token。

### 6.2 LLM 创建 Skill 工作流

输入：

- Skill 目标。
- 使用场景。
- 触发条件。
- 目标 Agent 类型。
- 用户提供的参考材料。
- 希望包含的脚本、参考资料、示例和测试。
- 约束条件，例如语言、风格、禁止事项、公司规范。

流程：

1. 系统整理用户输入。
2. 注入公开 Skill 创建规范摘要。
3. 如果将来配置了公司内网规范，则追加组织级约束。
4. LLM 生成 Skill 设计方案，包括目录结构、`SKILL.md`、可选文件建议。
5. 系统校验 front matter、文件名、目录安全、description 质量。
6. 若校验失败，自动要求 LLM 修复一次。
7. 前端展示草稿、校验结果和可编辑文件树。
8. 用户确认后保存为草稿或发布为版本。

输出：

- 文件树。
- `SKILL.md`。
- 创建说明。
- 测试建议。
- 风险提示。

### 6.3 LLM 更新 Skill 工作流

输入：

- 当前 Skill 版本。
- 用户修改目标。
- 可选参考材料。
- 可选目标版本号。

流程：

1. 后端读取当前 Skill 文件树。
2. LLM 分析当前 Skill 的结构、触发描述、渐进加载和可维护性问题。
3. LLM 生成更新方案和 patch。
4. 系统对 patch 做路径与格式校验。
5. 前端展示 diff，用户可逐文件接受或编辑。
6. 用户确认后生成新版本 commit。

输出：

- 更新摘要。
- 文件 diff。
- 版本升级建议：patch/minor/major。
- 测试提示。

### 6.4 内置规范摘要

第一阶段内置的规范摘要必须覆盖：

1. `SKILL.md` 是核心入口，front matter 的 `name` 和 `description` 是 Agent 发现 Skill 的主要依据。
2. `description` 应写清触发场景和适用条件。
3. 公司规范要求 `description` 按“功能说明 + 使用场景 + 关键词”组织，必要时支持中英双语。
4. 支持 `argument-hint`、`disable-model-invocation`、`user-invocable` 三个可选字段。
5. 指令内容建议包含 Skill 标题、任务说明、执行步骤、输出格式、示例。
6. 支持 `$ARGUMENTS` 接收完整参数，也支持 `$0`、`$1`、`$2` 等位置参数。
7. 大量资料不要全部塞进 `SKILL.md`，应放进 `references/`，通过渐进加载降低上下文成本。
8. 可执行或重复性流程优先放进 `scripts/`，由 `SKILL.md` 简洁说明何时运行。
9. 资源文件放进 `assets/`。
10. 创建 Skill 后应使用代表性任务进行测试，并根据 Agent 表现迭代描述、流程和文件组织。
11. Skill 应避免过宽泛，最好围绕明确任务或领域能力。
12. 文件内容应使用 UTF-8 编码，文件名必须为大写 `SKILL.md`，内容应可读、可维护、低歧义。

## 7. 功能需求

### 7.1 首页/工作台

进入系统后默认展示 Skill 工作台：

- 顶部展示当前用户信息。
- 左侧或顶部导航：Skill 列表、创建、LLM 任务、设置、审计日志。
- 主区域展示最近更新的 Skill、草稿、最近发布版本、LLM 生成状态。

空态：

- 没有 Skill 时，展示“创建 Skill”和“导入 Skill”两个主操作。

### 7.2 Skill 列表

列表字段：

- 名称。
- 描述。
- 当前版本。
- 状态：草稿、已发布、归档。
- 最近更新时间。
- 最近提交 SHA 短码。
- 文件数量。

筛选：

- 关键词。
- 状态。
- 更新时间。
- 标签。

操作：

- 查看详情。
- 编辑。
- 创建新版本。
- 复制。
- 归档。
- 删除。

删除必须二次确认。第一阶段可以软删除 sqlite 记录，但 Git 历史不删除。

### 7.3 Skill 详情

详情页必须包含：

- 基本信息。
- 当前版本。
- 文件树。
- Markdown 预览。
- 原始文件编辑。
- 版本历史。
- Git commit 信息。
- 审计日志。

文件树支持：

- 新建文件。
- 新建目录。
- 重命名。
- 删除。
- 上传。
- 下载。
- 查看 diff。

### 7.4 创建 Skill

创建入口提供两种模式：

1. 手动创建：用户填写名称、描述、`SKILL.md` 内容和文件结构。
2. LLM 创建：用户填写目标和材料，由 LLM 生成草稿。

名称校验：

- 必填。
- 仅允许小写字母、数字、短横线。
- 长度 3 到 64。
- 同一用户下唯一。

描述校验：

- 必填。
- 建议 50 到 500 字符。
- 必须包含明确适用场景，推荐包含触发关键词。

可选字段校验：

- `argument-hint` 必须是字符串，用于提示命令参数，例如 `[filename]`。
- `disable-model-invocation` 必须是布尔值，适合部署、删除等只允许手动触发的 Skill。
- `user-invocable` 必须是布尔值，控制是否在 `/` 菜单中显示。

保存方式：

- 保存草稿：只写 sqlite 和工作区，不创建发布 tag。
- 发布版本：写 Git commit，并创建产品版本记录。

### 7.5 更新 Skill

更新入口提供三种模式：

1. 直接编辑文件。
2. LLM 辅助更新。
3. 从本地上传 Skill 包覆盖或合并。

更新发布时要求填写：

- 版本号，系统可推荐。
- 更新摘要。
- 变更类型：patch、minor、major。

发布后：

- 创建 Git commit。
- 更新 sqlite 版本索引。
- 可选创建 Git tag。

### 7.6 版本历史

版本历史展示：

- 产品版本。
- Git commit SHA。
- 作者。
- 发布时间。
- 更新摘要。
- 变更类型。

操作：

- 查看文件。
- 对比任意两个版本。
- 恢复到此版本。
- 下载此版本。

恢复版本不是重写历史，而是基于目标历史版本内容创建一个新 commit。

### 7.7 导入与导出

导入支持：

- 上传 zip。
- 从 Git 指定仓库导入，并绑定为当前用户的 Skill。
- 粘贴 `SKILL.md`。

导入必须校验：

- 是否包含 `SKILL.md`。
- front matter 是否合法。
- 目录路径是否安全。
- 文件数量和大小是否超限。

导出支持：

- zip。
- 单文件 `SKILL.md`。
- 指定版本导出。

### 7.8 审计日志

记录字段：

- 用户。
- 操作类型。
- Skill。
- 版本。
- 时间。
- 请求来源 IP。
- 操作摘要。
- 关联 LLM 任务 ID。
- 关联 Git commit SHA。

## 8. 非功能需求

### 8.1 安全

1. Cookie 中的 `user_id` 是唯一租户来源。
2. 所有文件路径必须做规范化与白名单校验。
3. 禁止在日志、数据库、前端页面中展示完整 token、私钥。
4. LLM 请求日志只保存摘要和 token 用量，不保存完整敏感内容。
5. 上传文件大小默认限制为 20MB。
6. 单个 Skill 文件数量默认限制为 500。
7. 单文件默认限制为 2MB，`assets/` 可单独放宽到 10MB。
8. Git 操作必须串行化或加锁，避免同一工作目录并发冲突。

### 8.2 性能

第一阶段目标：

- Skill 列表 1000 条内响应小于 500ms。
- 单个 Skill 文件树 500 文件内加载小于 1s。
- LLM 生成任务使用异步任务，不阻塞普通 API。
- Git commit/push 操作允许较慢，但前端必须展示进度状态。

### 8.3 可维护性

后端模块建议：

```text
backend/
  app/
    api/
    core/
    db/
    models/
    schemas/
    services/
      git_service.py
      llm_service.py
      skill_service.py
      validation_service.py
      audit_service.py
    workers/
```

前端模块建议：

```text
frontend/
  src/
    api/
    components/
    pages/
    routes/
    stores/
    styles/
    types/
```

## 9. 数据模型

### 9.1 users

用于缓存 Cookie 用户信息，不作为认证源。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer | 主键 |
| user_id | string | Cookie 用户 ID，唯一 |
| user_name | string | 可选 |
| user_email | string | 可选 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 9.2 skills

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer | 主键 |
| user_id | string | 租户 |
| name | string | Skill 名称 |
| description | text | 触发描述 |
| argument_hint | string | 参数提示，可选 |
| disable_model_invocation | boolean | 是否禁止 AI 自动调用 |
| user_invocable | boolean | 是否在 `/` 菜单显示 |
| status | string | draft/published/archived/deleted |
| current_version_id | integer | 当前版本 |
| git_group_url | string | Git group 地址 |
| git_repo_name | string | Skill 对应仓库名 |
| git_remote_url | string | Skill 仓库 remote URL |
| git_local_path | string | Skill 仓库本地路径 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

唯一索引：

```text
(user_id, name)
```

### 9.3 skill_versions

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer | 主键 |
| skill_id | integer | Skill ID |
| user_id | string | 租户 |
| version | string | 产品版本 |
| change_type | string | patch/minor/major |
| summary | text | 更新摘要 |
| git_commit_sha | string | Git commit |
| git_tag | string | 可选 tag |
| author_name | string | 作者 |
| author_email | string | 作者邮箱 |
| created_at | datetime | 创建时间 |

### 9.4 skill_files

用于草稿和快速展示。发布版本以 Git 为准。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer | 主键 |
| skill_id | integer | Skill ID |
| user_id | string | 租户 |
| path | string | Skill 内相对路径 |
| content | text/blob | 文件内容 |
| content_type | string | text/binary |
| size | integer | 大小 |
| sha256 | string | 内容摘要 |
| updated_at | datetime | 更新时间 |

### 9.5 llm_jobs

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer | 主键 |
| user_id | string | 租户 |
| skill_id | integer | 可选 |
| job_type | string | create/update/review |
| status | string | queued/running/succeeded/failed/canceled |
| input_summary | text | 输入摘要 |
| output_summary | text | 输出摘要 |
| error_message | text | 错误 |
| model | string | 模型 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 9.6 audit_logs

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer | 主键 |
| user_id | string | 租户 |
| skill_id | integer | 可选 |
| version_id | integer | 可选 |
| action | string | 操作 |
| summary | text | 摘要 |
| ip | string | 来源 IP |
| llm_job_id | integer | 可选 |
| git_commit_sha | string | 可选 |
| created_at | datetime | 创建时间 |

## 10. API 规格

所有 API 均以 `/api` 开头。后端从 Cookie 解析用户，不接受前端传 `user_id` 决定租户。

### 10.1 用户

```http
GET /api/me
```

返回当前用户信息。

### 10.2 Skill

```http
GET /api/skills
POST /api/skills
GET /api/skills/{skill_id}
PATCH /api/skills/{skill_id}
DELETE /api/skills/{skill_id}
POST /api/skills/{skill_id}/repository
PATCH /api/skills/{skill_id}/repository
```

`POST /api/skills/{skill_id}/repository` 用于在 Git group 下创建独立 Skill 仓库。  
`PATCH /api/skills/{skill_id}/repository` 用于绑定已存在仓库的 remote URL。

### 10.3 文件

```http
GET /api/skills/{skill_id}/files
GET /api/skills/{skill_id}/files/content?path=SKILL.md
PUT /api/skills/{skill_id}/files/content
DELETE /api/skills/{skill_id}/files/content?path=...
POST /api/skills/{skill_id}/files/upload
```

### 10.4 版本

```http
GET /api/skills/{skill_id}/versions
POST /api/skills/{skill_id}/versions
GET /api/skills/{skill_id}/versions/{version_id}
GET /api/skills/{skill_id}/versions/{version_id}/files
POST /api/skills/{skill_id}/versions/{version_id}/restore
GET /api/skills/{skill_id}/diff?from_version_id=1&to_version_id=2
```

### 10.5 LLM

```http
POST /api/llm/skill-drafts
POST /api/llm/skill-updates
GET /api/llm/jobs
GET /api/llm/jobs/{job_id}
POST /api/llm/jobs/{job_id}/cancel
```

### 10.6 导入导出

```http
POST /api/import/zip
POST /api/import/skill-md
GET /api/skills/{skill_id}/export.zip
GET /api/skills/{skill_id}/versions/{version_id}/export.zip
```

## 11. Git 工作流

### 11.1 初始化

后端启动：

1. 读取 `SKILL_GIT_GROUP_URL`。
2. 读取 `SKILL_GIT_WORKDIR`。
3. 读取 `SKILL_GIT_SSH_KEY`，默认使用 `/Users/zhangguangming/.ssh/id_rsa`。
4. 读取可选 `SKILL_GIT_API_TOKEN`，用于自动创建仓库。
5. 若本地仓库根目录不存在，则创建目录。
6. 对 sqlite 中已绑定的 Skill 仓库逐个校验 remote URL；本地目录存在则 fetch，不存在则 clone。

Skill 仓库命名建议：

```text
{safe_user_id}--{skill_name}
```

如果公司 Git group 支持同名空间下同名仓库唯一，则必须通过 `safe_user_id` 前缀或其他稳定前缀避免不同租户的 Skill 仓库名冲突。前端可以展示 Skill 原始名称，Git 仓库名由后端生成。

### 11.2 发布版本

发布 Skill 版本：

1. 获取 Skill 仓库级 Git 锁。
2. 若 Skill 尚未绑定仓库，则在 group 下创建或绑定独立仓库。
3. clone 或 fetch 对应 Skill 仓库。
4. 将文件写入该仓库根目录。
5. `git add`。
6. `git commit`，message 格式：

```text
release: {skill_name} v{version}

{summary}
```

7. 可选创建 tag：

```text
v{version}
```

8. `git push`。
9. 若创建 tag，则 `git push --tags` 或推送指定 tag。
10. sqlite 写入版本记录和仓库映射。
11. 释放锁。

### 11.3 冲突处理

如果 push 失败：

1. fetch/rebase 一次。
2. 若无冲突，重试 push。
3. 若有冲突，记录失败状态并在前端提示用户重新打开 diff 处理。

## 12. 前端页面规格

### 12.1 路由

```text
/                       Skill 工作台
/skills                 Skill 列表
/skills/new             创建 Skill
/skills/:id             Skill 详情
/skills/:id/edit        编辑 Skill
/skills/:id/versions    版本历史
/skills/:id/diff        版本对比
/llm-jobs               LLM 任务
/settings               设置
/audit-logs             审计日志
```

### 12.2 设计要求

1. 默认首屏是可操作工作台，不做宣传页。
2. 工具类界面应偏工作台风格：信息密度适中、层次清楚、避免大面积装饰。
3. 编辑器区域必须支持保存状态、未保存提示、错误提示。
4. 长任务必须展示排队、运行、成功、失败状态。
5. 版本 diff 必须可读，至少支持按文件查看。
6. 所有破坏性操作必须二次确认。
7. 移动端至少可查看列表和详情；复杂编辑可优先桌面体验。

## 13. 校验规则

### 13.1 `SKILL.md`

必须校验：

- 文件存在。
- YAML front matter 可解析。
- `name` 存在且与系统 Skill 名称一致。
- `description` 存在且非空。
- Markdown 正文非空。

建议校验：

- `description` 是否包含明确触发条件。
- `SKILL.md` 是否过长。
- 是否把大段参考资料塞进入口文件。
- 是否提到可选脚本或参考资料的加载方式。

### 13.2 文件路径

禁止：

- 绝对路径。
- `..`。
- 空路径。
- 控制字符。
- 超过 240 字符的路径。
- 超过 128 字符的单段文件名。

### 13.3 版本号

第一阶段使用语义化版本：

```text
MAJOR.MINOR.PATCH
```

系统可根据变更类型推荐：

- patch：修复描述、补充小内容。
- minor：新增流程、脚本、参考资料。
- major：重构 Skill 目标、触发范围或不兼容结构变化。

## 14. 测试要求

### 14.1 后端测试

必须覆盖：

- Cookie 用户解析。
- 多租户隔离。
- Skill CRUD。
- `SKILL.md` 校验。
- 路径安全校验。
- 版本发布。
- Git service mock。
- LLM service mock。
- 导入 zip 安全校验。

### 14.2 前端测试

建议覆盖：

- Skill 列表渲染。
- 创建表单校验。
- 文件树操作。
- 编辑保存。
- LLM 任务状态轮询。
- 版本历史与 diff 页面。

### 14.3 集成测试

必须提供本地 smoke test：

1. 设置测试 Cookie `user_id=test-user`。
2. 创建 Skill。
3. 编辑 `SKILL.md`。
4. 发布 `0.1.0`。
5. 查看版本历史。
6. 触发 LLM mock 更新。
7. 发布 `0.1.1`。
8. 对比两个版本。
9. 导出 zip。

## 15. 配置项

`.env.example` 至少包含：

```bash
APP_ENV=local
DATABASE_URL=sqlite:///./data/skillmng.sqlite3
COOKIE_USER_ID_KEY=user_id
COOKIE_USER_NAME_KEY=user_name
COOKIE_USER_EMAIL_KEY=user_email

SKILL_GIT_GROUP_URL=https://code.myxiaojin.cn/groups/xiaojin-skills
SKILL_GIT_REPO_URL_TEMPLATE=git@code.myxiaojin.cn:xiaojin-skills/{repo_slug}.git
SKILL_GIT_WORKDIR=./data/git/skill-repos
SKILL_GIT_SSH_KEY=/Users/zhangguangming/.ssh/id_rsa
SKILL_GIT_API_TOKEN=replace-with-git-api-token-if-auto-create-is-needed
SKILL_GIT_AUTHOR_NAME=Skill Manager
SKILL_GIT_AUTHOR_EMAIL=skill-manager@example.com
SKILL_CREATE_TAGS=true

https_proxy=http://127.0.0.1:1235
http_proxy=http://127.0.0.1:1235
all_proxy=socks5://127.0.0.1:1234

DISABLE_PROMPT_CACHING=0
ANTHROPIC_BASE_URL=https://idealab.alibaba-inc.com/api/anthropic
ANTHROPIC_AUTH_TOKEN=replace-with-your-token
ANTHROPIC_MODEL=claude-opus-4-6
ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-6
ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-opus-4-6
ANTHROPIC_DEFAULT_SONNET_MODEL=claude-opus-4-6
CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1
DISABLE_AUTOUPDATER=1
API_TIMEOUT_MS=3000000
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

## 16. 交付物

Agent 实现时至少交付：

1. `backend/` Python3 后端。
2. `frontend/` TypeScript 前端。
3. `data/` 运行时目录，需加入 `.gitignore`。
4. `.env.example`。
5. README 启动说明。
6. 数据库迁移脚本。
7. 单元测试与 smoke test。
8. Skill 规范校验器。
9. LLM prompt 模板。
10. Git 操作封装。

## 17. 验收标准

### 17.1 功能验收

1. 设置 Cookie `user_id=alice` 后，只能看到 alice 的 Skill。
2. 设置 Cookie `user_id=bob` 后，看不到 alice 的 Skill。
3. 可以手动创建一个 Skill，并保存草稿。
4. 可以通过 LLM mock 创建一个 Skill 草稿。
5. 可以发布 Skill `0.1.0`，Git 产生 commit。
6. 可以更新 Skill 并发布 `0.1.1`。
7. 可以查看 `0.1.0` 与 `0.1.1` 的 diff。
8. 可以恢复 `0.1.0` 内容并生成新的 commit。
9. 可以导出 zip。
10. 缺少 Cookie `user_id` 时 API 返回 401。

### 17.2 安全验收

1. 上传 zip 中包含 `../evil.txt` 时必须拒绝。
2. API body 中传入其他 `user_id` 不影响租户隔离。
3. 日志中不得出现完整 `ANTHROPIC_AUTH_TOKEN`。
4. 仓库中不得提交真实 token 或 SSH 私钥。
5. 删除 Skill 不会删除 Git 历史。

### 17.3 工程验收

1. 后端测试可通过。
2. 前端构建可通过。
3. README 能指导本地启动。
4. sqlite 数据库可自动初始化。
5. Git 仓库 clone/fetch/push 失败时前端能看到明确错误。

## 18. 推荐实现里程碑

### M1：项目骨架

- FastAPI 后端。
- React TypeScript 前端。
- sqlite 初始化。
- Cookie 用户解析。
- `.env.example`。

### M2：Skill CRUD 与文件编辑

- Skill 列表。
- 创建和详情。
- 文件树。
- `SKILL.md` 校验。
- 草稿保存。

### M3：Git 版本管理

- clone/fetch。
- 发布 commit。
- 版本历史。
- diff。
- restore。

### M4：LLM 辅助创建/更新

- LLM client。
- prompt 模板。
- 任务记录。
- 草稿生成。
- diff 生成。

### M5：导入导出与审计

- zip 导入。
- zip 导出。
- 审计日志。
- smoke test。

## 19. 风险与待决问题

1. 公司 Skill 规范已通过 `doc/guifan.md` 接入第一阶段；后续若内网规范继续扩展，需要追加为规则插件或 prompt 片段。
2. 每个 Skill 一个仓库后，仓库自动创建依赖 Git 平台 API token；若 token 不可用，第一阶段需要支持手动绑定已创建仓库。
3. Git 仓库并发写入风险：第一阶段用进程内锁即可，生产多实例需要分布式锁。
4. sqlite 多写并发能力有限：第一阶段可接受，后续迁移 PostgreSQL。
5. LLM 输出不稳定：必须有格式校验、自动修复和人工确认。
6. SSH key 文件名未知：通过 `SKILL_GIT_SSH_KEY` 配置解决。
7. 内部 LLM API 是否完全兼容 Anthropic API 需实现时验证。

## 20. Agent 实施提示

实现 Agent 应优先按以下顺序工作：

1. 先建立可运行骨架，不要直接进入复杂 UI。
2. 所有租户隔离逻辑先写测试。
3. 所有 Git 操作通过单一 service 封装。
4. LLM 先做 mock，再接真实 API。
5. 创建/更新 Skill 的 prompt 必须显式引用公开规范摘要。
6. 不要提交真实 token，不要复制本机 SSH 私钥。
7. 每个里程碑结束后运行测试并更新 README。
