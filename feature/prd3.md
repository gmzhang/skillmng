# Skill 管理系统 PRD3：Git 发布闭环与真实 LLM 接入

版本：v0.1  
日期：2026-05-26  
依赖文档：[feature/prd1.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd1.md)、[feature/prd2.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd2.md)、[doc/guifan.md](/Users/zhangguangming/Desktop/work/code/skillmng/doc/guifan.md)、[doc/antcode-api-guide.md](/Users/zhangguangming/Desktop/work/code/skillmng/doc/antcode-api-guide.md)

## 1. 背景

PRD2 的主体页面已经基本完成：工作台、Skill 列表、详情、版本历史、版本对比、审计日志、设置页都已可用。当前主要问题不再是页面有没有，而是 Git 发布链路的数据闭环与真实 LLM 能力还没有完全打通。

本 PRD3 聚焦两件事：

1. 补齐 `repo -> draft branch -> draft commit -> master commit -> tag -> current_version` 的一致性。
2. 将 LLM 从 mock 切到真实 Anthropic 兼容接口，用真实模型生成和更新 Skill。

## 2. 当前观察问题

### 2.1 当前版本字段未贯通

现象：

- 工作台能显示最近发布版本 `v0.1.2` 和 commit。
- Skill 列表“当前版本”显示 `-`。
- Skill 详情“当前版本”和“最新发布 commit”显示 `-`。
- 版本历史中实际存在 `0.1.0`、`0.1.1`、`0.1.2`。

要求：

- `GET /api/skills` 和 `GET /api/skills/{id}` 必须返回一致的聚合字段。
- 当前版本必须使用产品版本号，例如 `0.1.2`，不得显示内部 version id。
- 当前 commit 必须指向 `master` 上最新正式发布 commit。

需要返回：

```json
{
  "current_version": "0.1.2",
  "current_version_id": 3,
  "published_commit_sha": "6f0b698ad...",
  "published_commit_short": "6f0b698ad",
  "published_tag": "v0.1.2"
}
```

### 2.2 Tag 未创建或未展示

现象：

- 版本历史 Tag 列均为 `-`。
- PRD2 要求正式发布后创建 `v{version}` tag。

要求：

- 发布成功后必须在远端仓库 `master` 对应 commit 上创建 tag。
- tag 格式为 `v{version}`，例如 `v0.1.2`。
- 如果远端 tag 已存在，发布应失败并提示版本冲突，不得覆盖旧 tag。
- 版本历史必须展示 tag。
- 审计日志必须记录 tag。

### 2.3 草稿分支状态未体现

现象：

- 详情页“草稿分支”显示 `-`。
- 保存文件的审计记录仍是 `写入文件 path=SKILL.md size=...`，无法判断是否提交到远端草稿分支。

要求：

- 保存草稿必须提交到远端 `draft/{user_id}/{skill_name}` 分支。
- 详情页必须展示草稿分支和最新草稿 commit。
- 审计日志应区分：
  - `skill.draft.commit`：草稿分支提交。
  - `skill.version.publish`：合并到 master 的正式发布。
- 文件保存可以先写入 sqlite 草稿缓存，但必须最终产生远端草稿 commit 才算成功。

### 2.4 Git 内容真源约束

要求：

- 远端 Git 仓库是 Skill 内容真源。
- 本地 clone、sqlite 文件内容和工作区只作为缓存或编辑缓冲。
- 系统重启或本地缓存删除后，必须能通过 `repository/sync` 从远端恢复 Skill 文件树、当前版本、草稿分支和 commit 信息。

### 2.5 Description 触发词校验误报

现象：

- `yuque` description 包含“适用于用户提到...或要求...”等触发表达，但详情页仍提示“description 未包含明显触发关键词”。

要求：

- 中文触发词校验应包含：`适用于`、`当用户`、`用户提到`、`提到`、`要求`、`需要`、`场景`、`触发`、`使用`、`调用`、`URL`、`链接`。
- 英文触发词校验应包含：`use when`、`when`、`trigger`、`mentioned`、`asks`、`needs`、`URL`。
- 校验结果应分为 warning 和 error；description 触发词不足只作为 warning，不阻塞保存，除非用户选择严格模式。

## 3. 真实 LLM 接入

### 3.1 配置

`.env` 已包含真实 LLM 配置。后端必须从环境变量读取，不得写入日志、数据库明文或前端明文。

关键配置：

```bash
ANTHROPIC_BASE_URL=https://idealab.alibaba-inc.com/api/anthropic
ANTHROPIC_MODEL=claude-opus-4-6
ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-opus-4-6
ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-6
ANTHROPIC_DEFAULT_SONNET_MODEL=claude-opus-4-6
API_TIMEOUT_MS=3000000
DISABLE_PROMPT_CACHING=0
```

`ANTHROPIC_AUTH_TOKEN` 只允许后端读取，前端只展示“已配置”。

### 3.2 Provider 切换

新增或确认：

```bash
LLM_PROVIDER=anthropic
```

要求：

- `LLM_PROVIDER=mock` 时继续使用现有 mock client，便于测试。
- `LLM_PROVIDER=anthropic` 时使用真实 Anthropic 兼容 HTTP client。
- 设置页必须显示当前 provider，并提供“测试 LLM 连接”。
- 若 provider 为 `anthropic` 但 token 缺失，后端启动不必失败，但调用 LLM API 时必须返回明确错误。

### 3.3 Anthropic 兼容客户端

后端新增 `AnthropicLLMClient`，实现现有 `LLMClient` 协议：

```python
class LLMClient(Protocol):
    def create_skill_draft(self, inp: CreateInput) -> CreateOutput: ...
    def update_skill(self, inp: UpdateInput) -> UpdateOutput: ...
```

要求：

- 使用 `ANTHROPIC_BASE_URL`、`ANTHROPIC_AUTH_TOKEN`、`ANTHROPIC_MODEL`。
- 超时使用 `API_TIMEOUT_MS`。
- 请求头不得被日志完整打印。
- 支持至少一次可配置重试。
- 对非 2xx 响应记录摘要错误，不记录 token。
- 兼容内部 Anthropic API 的实际响应格式；如果不兼容，要在错误中说明响应摘要。

建议接口：

```http
POST {ANTHROPIC_BASE_URL}/v1/messages
```

如果内部 endpoint 已经包含 `/v1/messages` 或路径不同，实现时应通过配置或探测避免重复拼接路径。

### 3.4 LLM 输出格式

真实 LLM 必须输出严格 JSON，不允许直接把自然语言当作结果落地。

创建 Skill 输出：

```json
{
  "summary": "生成说明",
  "files": [
    {
      "path": "SKILL.md",
      "content": "---\\nname: ...\\n---\\n..."
    }
  ],
  "tests": ["测试建议"],
  "risks": ["风险提示"]
}
```

更新 Skill 输出：

```json
{
  "summary": "更新说明",
  "change_type": "patch",
  "patches": [
    {
      "path": "SKILL.md",
      "change": "modify",
      "content": "完整新内容"
    }
  ],
  "tests": ["测试建议"],
  "risks": ["风险提示"]
}
```

要求：

- `SKILL.md` 必须是完整文件内容，不接受片段。
- `patches[].change` 只允许 `add`、`modify`、`remove`。
- `path` 必须通过路径安全校验。
- 输出 JSON 解析失败时，允许自动要求模型修复一次。
- 自动修复后仍失败，则任务状态为 `failed`，并展示可读错误。

### 3.5 Prompt 要求

真实 LLM prompt 必须包含：

- `doc/guifan.md` 的公司 Skill 规范摘要。
- Agent Skills 开放标准摘要。
- PRD1/PRD2/PRD3 中关于 `SKILL.md`、front matter、description、参数、文件组织的要求。
- 明确要求只输出 JSON。
- 明确禁止输出真实 token、密钥、内部 cookie。
- 明确要求 `SKILL.md` 只有一个 front matter。
- 明确要求 description 按“功能说明 + 使用场景 + 关键词”组织。
- 明确要求大资料放 `references/`，重复流程放 `scripts/`。

### 3.6 LLM 任务落地

要求：

- LLM 创建结果落地为 Skill 草稿后，必须创建远端仓库和草稿分支 commit。
- LLM 更新结果落地前必须展示 patch diff。
- 用户确认落地后，结果必须提交到草稿分支。
- 已落地任务不可重复落地。
- LLM 落地审计记录：
  - `llm.create.submit`
  - `llm.create.apply`
  - `llm.update.submit`
  - `llm.update.apply`
  - `skill.draft.commit`

### 3.7 LLM 安全

要求：

- 不记录完整 prompt。
- 不记录完整 response，除非响应已经被脱敏且仅存储在开发调试模式。
- `llm_jobs.input_summary` 只保存摘要。
- `llm_jobs.output_summary` 只保存摘要。
- 真实 token 不进入 sqlite、日志、前端、审计、测试快照。
- 设置页 token 展示建议只显示“已配置”，不展示首尾字符。

## 4. API 补充

### 4.1 Skill DTO 补充

`GET /api/skills` 和 `GET /api/skills/{id}` 返回：

```json
{
  "current_version": "0.1.2",
  "published_commit_sha": "6f0b698ad...",
  "published_tag": "v0.1.2",
  "draft_branch": "draft/bob1/yuque",
  "draft_commit_sha": "abc123...",
  "git_project_id": 327201404,
  "git_path_with_namespace": "xiaojin-skills/yuque"
}
```

### 4.2 Settings API 补充

`GET /api/settings` 返回：

```json
{
  "llm": {
    "provider": "anthropic",
    "base_url": "https://idealab.alibaba-inc.com/api/anthropic",
    "model": "claude-opus-4-6",
    "timeout_ms": 3000000,
    "token_configured": true
  }
}
```

`POST /api/settings/test-llm`：

- mock provider：返回 mock 可用。
- anthropic provider：发送最小真实请求，返回模型名和连通性。
- 失败时返回可读错误摘要，不暴露 token。

### 4.3 Repository Sync API

`POST /api/skills/{skill_id}/repository/sync` 必须同步：

- AntCode project metadata。
- master 最新 commit。
- 最新 tag。
- 草稿分支是否存在。
- 草稿分支最新 commit。
- 远端文件树。
- sqlite 中 Skill 聚合字段。

## 5. UI 修改要求

### 5.1 Skill 列表

- 当前版本显示产品版本号，例如 `0.1.2`。
- Git 列展示仓库已绑定、草稿分支状态、最新发布 commit tooltip。
- 如果有未发布草稿，显示“有草稿”标识。

### 5.2 Skill 详情

- 当前版本显示 `v0.1.2`。
- 最新发布 commit 显示短 SHA，并可复制完整 SHA。
- tag 显示 `v0.1.2`。
- 草稿分支显示分支名和 commit。
- 如果草稿分支相对 master 有 diff，显示“有未发布变更”。
- 发布按钮点击后先展示草稿 diff，再确认发布。

### 5.3 设置页

- LLM provider 为真实 provider 时，不再显示“Mock 客户端不会真正调用外部 API”。
- token 只显示“已配置/未配置”，不显示首尾字符。
- “测试 LLM 连接”必须展示成功/失败 toast。
- “测试 AntCode 连接”如果耗时较久，应有 loading 和超时提示。

### 5.4 LLM 任务页

- 空态提示用户去“创建 Skill -> LLM 辅助”或“Skill 详情 -> LLM 辅助更新”。
- 任务详情展示 prompt 摘要、输出摘要、文件/patch 列表、测试建议、风险提示。
- `applied_at` 非空时显示“已落地”，禁用再次落地。

### 5.5 审计日志

- `skill.draft.commit` 显示为“提交草稿”。
- `skill.version.publish` 显示为“发布版本”。
- commit 列支持复制完整 SHA。
- 旧 `openclaw/skills.git` 绑定记录可以保留，但应显示“历史 remote”或“历史记录”提示，避免误解为当前 remote。

## 6. 数据迁移要求

对已有数据执行兼容迁移：

1. 根据 `skill_versions` 最新记录回填 `skills.current_version_id`。
2. 回填 `skills.published_commit_sha`。
3. 如果版本记录已有 tag 为空，不要伪造 tag；后续发布必须创建 tag。
4. 对已有 `git_path_with_namespace=xiaojin-skills/yuque` 的 Skill，同步远端仓库 metadata。
5. 保留旧审计日志，但新日志使用新 action 命名。

## 7. 验收标准

1. `LLM_PROVIDER=anthropic` 时，设置页显示真实 provider，并能测试 LLM 连接。
2. LLM 创建 Skill 能调用真实接口，生成严格 JSON，展示文件树和预览。
3. LLM 更新 Skill 能调用真实接口，生成 patch diff，用户确认后落地草稿分支。
4. LLM 输出如果不是合法 JSON，系统自动修复一次；仍失败时任务为 failed。
5. Skill 列表当前版本显示 `0.1.2`，不再显示 `-`。
6. Skill 详情当前版本、最新发布 commit、tag 与版本历史一致。
7. 保存草稿后，详情页显示草稿分支和草稿 commit。
8. 正式发布后，master 有正式 commit，远端有 `v{version}` tag。
9. `repository/sync` 后，删除本地临时 clone 也能恢复文件树和版本聚合字段。
10. 审计日志能区分提交草稿与发布版本。
11. description 校验不再误报“适用于用户提到...”这类中文触发表达。
12. 真实 token 不出现在前端明文、日志、审计、sqlite 明文字段、PRD 或 README。

## 8. 推荐实施顺序

1. 数据迁移：回填 `current_version_id`、`published_commit_sha` 等聚合字段。
2. 修复 Skill DTO 和详情/列表字段展示。
3. 实现发布 tag 创建与展示。
4. 打通草稿分支 commit 与详情页展示。
5. 实现 repository sync 的完整远端恢复。
6. 实现 AnthropicLLMClient 和 provider 切换。
7. 改造 LLM create/update prompt 和严格 JSON 解析。
8. 改造 LLM 落地流程：结果进入草稿分支。
9. 完善设置页测试 LLM 连接和 token 脱敏展示。
10. 补充测试：Git 发布闭环、真实 LLM client mock HTTP、JSON 修复、敏感信息不落库。

