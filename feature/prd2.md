# Skill 管理系统 PRD2：导航页面与工作流完善需求

版本：v0.1  
日期：2026-05-26  
依赖文档：[feature/prd1.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd1.md)、[doc/guifan.md](/Users/zhangguangming/Desktop/work/code/skillmng/doc/guifan.md)  
代码仓库接口文档：[doc/antcode-api-guide.md](/Users/zhangguangming/Desktop/work/code/skillmng/doc/antcode-api-guide.md)  
观察页面：<http://localhost:5173/>

## 1. 背景

当前系统已经具备基础前后端、左侧菜单导航、Skill 创建、列表、详情、版本、LLM 任务和审计日志页面。左侧菜单“Skill 列表 / 创建 Skill / LLM 任务 / 审计日志 / 设置”均可点击进入对应路由。

本 PRD2 不重写 PRD1，而是在当前实现基础上补充“可用但不够顺手、可点但工作流不完整”的改进需求。重点是让左侧主菜单进入的每个页面都能承担真实管理任务，并修复版本、LLM、审计、设置等页面中的信息表达和数据一致性问题。

## 2. 当前观察到的问题

### 2.1 工作台

当前工作台在已有 Skill 数据时仍容易呈现“还没有 Skill，先创建一个”的空态，不能体现用户已有资产、最近版本、最近 LLM 任务和审计动态。

需要修改：

- 工作台必须根据当前 Cookie 用户实时展示统计数据。
- 有 Skill 时不得展示纯空态。
- 工作台的“创建 Skill”“导入 / 导出”按钮必须进入真实工作流。

### 2.2 Skill 列表

当前列表能进入详情、编辑、版本、导出、删除，但信息表达偏工程化。

需要修改：

- “当前版本”不应显示 `current_version_id`，应显示产品版本号，例如 `0.1.1`。
- 状态值应有中文显示和颜色映射，例如 `draft=草稿`、`published=已发布`、`archived=已归档`、`deleted=已删除`。
- 长 description 应截断但提供 hover tooltip 或展开详情。
- 操作按钮需要稳定宽度和清晰 icon，避免文字拥挤。
- 删除后应支持列表状态筛选，不要默认混入 deleted 数据。
- 导入入口不应只写“导入 zip”，应明确支持 zip、`SKILL.md`、Git remote 绑定三种导入方式。

### 2.3 创建 Skill

当前手动创建和 LLM 辅助创建已经存在，但需要加强生成结果预览和 `SKILL.md` 一致性。

需要修改：

- 手动创建页应把“元数据字段”和“正文 body”明确分开。
- `initial_body` 只允许填写正文内容，系统负责渲染唯一 front matter。
- 如果用户在正文里粘贴了完整 `SKILL.md`，系统应识别并提示“检测到 front matter，是否拆分为元数据 + 正文”，不得生成双 front matter。
- 提交前必须展示最终 `SKILL.md` 预览。
- LLM 辅助创建成功后，落地前必须展示文件树、`SKILL.md` 预览、校验结果、风险提示。
- LLM 生成结果必须通过公司规范校验后才能落地。

### 2.4 Skill 详情与编辑

当前详情页可查看文件树、绑定 Git remote、发布版本和 LLM 辅助更新，但缺少“保存前校验”和“发布前差异确认”。

需要修改：

- `SKILL.md` 保存前必须运行校验，发现 front matter 重复、name 不一致、description 缺失、正文为空时阻止保存。
- 详情页应显示“校验状态”：通过、警告、错误。
- 发布版本前必须展示本次未发布 diff。
- 发布按钮在存在校验错误、Git remote 无效或版本号冲突时应禁用。
- Git remote 显示应支持复制和打开链接；未绑定时提示可自动创建或手动绑定。
- Git 仓库必须是发布目标和共享出口。正式发布后的 Skill 会被其他系统从 Git 仓库读取使用，因此发布前必须确认目标仓库、目标分支、commit SHA 和文件树。
- 文件树应支持重命名、删除、新建目录、上传文件；删除非空目录必须二次确认。

### 2.5 版本历史

当前版本页可选择两个版本进行对比，但存在 ID、版本号和摘要显示不清的问题。

需要修改：

- 版本表格必须显示产品版本号、Git commit、tag、change type、summary、作者、发布时间。
- `current_version_id` 只作为内部字段，不得在 UI 中当成版本号展示。
- 对比两个版本时，默认顺序应为“旧版本 -> 新版本”，避免 `from=新版本&to=旧版本` 导致 diff 方向反直觉。
- 行选择最多允许选择两个版本；选中两个后按钮文案显示“对比 0.1.0 -> 0.1.1”。
- 恢复版本前必须展示将要恢复的文件 diff，并说明“恢复会创建新 commit，不重写历史”。
- 发布新版本弹窗应自动推荐下一个 patch 版本，例如当前 `0.1.1` 推荐 `0.1.2`。

### 2.6 版本对比

当前 diff 页已经能显示 modified/removed 文件和左右对比，但需要增强可读性。

需要修改：

- 页面顶部明确展示基准版本和目标版本：`从 v0.1.0 到 v0.1.1`。
- 文件列表应显示 added/modified/removed 的数量汇总。
- 对删除文件和新增文件，应显示空侧说明，而不是空白编辑器。
- Monaco diff 区域需要支持自动换行、同步滚动、折叠未变化区域。
- 大文件 diff 应提示“文件较大，仅展示前 N 行 / 可下载完整 diff”。
- 允许从 diff 页直接返回对应 Skill 详情和版本历史。

### 2.7 LLM 任务

当前 LLM 任务页可以查看任务、详情、落地，但落地动作风险较高。

需要修改：

- Skill 列不显示数字 ID，应显示 Skill 名称，并可点击进入详情。
- 任务详情抽屉应展示输入摘要、输出摘要、patch 文件列表、风险、测试建议。
- “落地”前必须展示 patch diff，并二次确认。
- 已落地任务不得重复落地；按钮应显示“已落地”并禁用。
- queued/running 任务支持取消；取消后审计记录 `llm.job.cancel`。
- failed 任务应展示错误详情和“重新提交”入口。
- 列表应支持按状态、类型、Skill、时间筛选。

### 2.8 审计日志

当前审计日志能展示 action、Skill ID、版本 ID、摘要、commit、IP，但不够可读。

需要修改：

- Skill 列显示 Skill 名称，并可点击进入详情。
- 版本列显示产品版本号，并可点击进入版本详情。
- LLM Job 列显示 `#id` 并可打开任务详情。
- Commit 列支持复制完整 SHA。
- 支持按 action、Skill、版本、LLM Job、时间范围筛选。
- action 应有中文解释 tooltip，例如 `skill.version.publish=发布版本`。
- 审计详情抽屉展示完整原始记录，但敏感字段必须脱敏。

### 2.9 设置

当前设置页仍是占位页，必须补齐。

需要修改：

- 设置页分为“Git 设置”“LLM 设置”“系统限制”“规范校验”四个区域。
- Git 设置展示 AntCode API base URL、group URL、namespace ID、repo URL template、默认主分支、草稿分支前缀、SSH key 路径、代理配置、是否自动创建仓库。
- LLM 设置展示 provider、base URL、model、timeout、token 是否已配置；token 只显示掩码，不显示明文。
- 系统限制展示单文件大小、assets 大小、zip 大小、最大文件数。
- 规范校验展示当前启用规则：公司 `doc/guifan.md`、Agent Skills 标准、PRD1 规则。
- 提供“测试 AntCode API”“测试 Git 推送”“测试 LLM 连接”“刷新配置”按钮。
- 配置值第一阶段可以只读，但测试按钮必须调用后端 API 返回明确结果。

### 2.10 AntCode 仓库发布与草稿分支

新增强约束：

- 每个 Skill 在 `https://code.myxiaojin.cn/groups/xiaojin-skills` 群组下对应一个独立仓库。
- 群组 namespace ID 为 `354800126`，路径为 `xiaojin-skills`。
- 系统不得把本地 sqlite 或本地文件目录作为 Skill 内容真源。Skill 内容真源是远端 Git 仓库。
- 本地允许存在临时 clone、临时工作区和缓存，但提交或发布完成后不得依赖本地保留的 Skill 内容；重启后必须能从远端 Git 仓库恢复状态。
- 每次保存草稿都应提交到该 Skill 仓库的草稿临时分支。
- 真正发布时，将草稿分支内容合并到主分支 `master`，并在 `master` 上形成正式发布 commit。
- 发布到 `master` 后，必须记录 commit SHA、产品版本、tag、仓库 URL，并供其他系统读取。

分支约定：

```text
master
draft/{user_id}/{skill_name}
```

如果 AntCode 对分支名有限制，`user_id` 和 `skill_name` 必须经过安全 slug 化。草稿分支是临时协作/预发布载体，不是正式发布结果。

仓库创建要求：

- 首次发布或首次保存草稿前，如果 Skill 未绑定仓库，系统必须调用 AntCode API 创建仓库。
- 创建仓库 API 必须使用 `POST https://code.myxiaojin.cn/api/v3/projects/`，不得使用 `/api/v4/`。
- 请求头使用 `PRIVATE-TOKEN`，token 必须从环境变量读取，不得写入日志、数据库明文或前端页面。
- 创建仓库请求体至少包含：

```json
{
  "name": "repo-name",
  "path": "repo-path",
  "namespace_id": 354800126,
  "visibility": "private",
  "initialize_with_readme": true
}
```

- 创建成功后保存 `project_id`、`path_with_namespace`、`http_url_to_repo`、`ssh_url_to_repo`。
- SSH URL 可能包含 AntCode tenant path，例如 `git@code.myxiaojin.cn:cqcfd7cn/xiaojin-skills/repo.git`，不得自行拼错。

草稿提交要求：

- 保存草稿时，系统将当前文件树提交到 `draft/{user_id}/{skill_name}`。
- 如果草稿分支不存在，调用 `POST /api/v3/projects/{project_id}/repository/branches` 创建分支，参数名必须是 `branch_name`，基准为 `master` 或仓库默认分支。
- 草稿提交可以通过本地临时 clone + git push 实现，也可以通过 AntCode 文件 API 实现；不论哪种方式，都必须记录草稿 commit SHA。
- 草稿分支可以有多个 commit，但 UI 只展示最新草稿状态。

正式发布要求：

- 发布时必须先校验草稿分支与目标版本。
- 发布前展示 `draft` 分支相对 `master` 的 diff。
- 用户确认后，将草稿分支合并到 `master`，形成正式发布 commit。
- 如果 AntCode API 不能可靠创建/合并 PR，后端应使用本地临时 clone 执行 `git fetch`、`git checkout master`、`git merge --no-ff draft/...`、`git push origin master`。
- 发布成功后在 `master` 上创建 tag，tag 格式为 `v{version}`。
- 发布成功后可保留草稿分支用于下一轮编辑，也可删除并在下次编辑时重新创建；策略必须在设置页展示。
- 发布失败时不得更新当前版本指针。

禁止事项：

- 不得把 Skill 内容只保存在本地数据库而不提交 Git。
- 不得发布到本地临时仓库后就认为发布成功。
- 不得在真实发布流程里使用 mock repo。
- 不得把 AntCode token 明文写入 PRD、日志、sqlite 或前端。

## 3. 左侧菜单交互要求

左侧菜单必须作为稳定主导航：

- 点击菜单后 URL 与页面内容必须一致。
- 当前菜单项高亮必须覆盖子路由，例如 `/skills/1`、`/skills/1/edit`、`/skills/1/versions` 都高亮“Skill 列表”。
- 菜单项应有 tooltip，窄屏或折叠状态下仍可理解。
- 内容页顶部必须有面包屑，显示当前位置，例如 `Skill 列表 / admit-optimize-plan / 版本历史`。
- 从任意二级页面返回主菜单页面时，不应丢失列表筛选条件。

## 4. 数据与 API 补充

### 4.1 Skill 列表 DTO

`GET /api/skills` 返回中必须补充：

```json
{
  "current_version": "0.1.1",
  "current_commit_sha": "fde9eeb13...",
  "draft_commit_sha": "abc1234...",
  "git_bound": false,
  "git_project_id": 327200665,
  "git_web_url": "https://code.myxiaojin.cn/xiaojin-skills/repo",
  "draft_branch": "draft/bob1/admit-optimize-plan",
  "validation_status": "valid|warning|error"
}
```

### 4.2 LLM Job DTO

LLM job 返回中必须补充：

```json
{
  "skill_name": "admit-optimize-plan",
  "applied_at": "2026-05-26T05:55:34+08:00",
  "patches": [
    {
      "path": "SKILL.md",
      "change": "modify"
    }
  ],
  "tests": [],
  "risks": []
}
```

### 4.3 审计日志 DTO

审计日志返回中必须补充：

```json
{
  "skill_name": "admit-optimize-plan",
  "version": "0.1.1",
  "action_label": "发布版本",
  "commit_short": "fde9eeb"
}
```

### 4.4 设置 API

新增：

```http
GET /api/settings
POST /api/settings/test-git
POST /api/settings/test-llm
POST /api/settings/reload
```

第一阶段设置 API 可只读，不允许从页面写入 `.env`。

### 4.5 AntCode 仓库 API

新增：

```http
POST /api/skills/{skill_id}/repository/create
POST /api/skills/{skill_id}/drafts/commit
GET /api/skills/{skill_id}/drafts/diff
POST /api/skills/{skill_id}/publish
POST /api/skills/{skill_id}/repository/sync
```

语义：

- `repository/create`：在 `xiaojin-skills` group 下创建该 Skill 的独立仓库，并保存 AntCode project metadata。
- `drafts/commit`：把当前编辑文件树提交到草稿分支。
- `drafts/diff`：返回草稿分支相对 `master` 的 diff。
- `publish`：将草稿分支合并到 `master`，创建正式 commit 和 tag，更新版本索引。
- `repository/sync`：从远端仓库同步项目详情、分支、最新 commit 和文件树。

### 4.6 数据模型补充

`skills` 表需要补充或确认以下字段：

| 字段 | 说明 |
| --- | --- |
| git_project_id | AntCode project id |
| git_namespace_id | 固定为 `354800126` 或配置值 |
| git_path_with_namespace | 例如 `xiaojin-skills/admit-optimize-plan` |
| git_http_url | HTTPS clone URL |
| git_ssh_url | SSH clone URL |
| git_web_url | Web 页面 URL |
| default_branch | 默认 `master` |
| draft_branch | 当前草稿分支 |
| draft_commit_sha | 最新草稿 commit |
| published_commit_sha | 最新发布 commit |

`skill_versions` 表必须保证 `git_commit_sha` 指向 `master` 上的正式发布 commit，而不是草稿分支 commit。

### 4.7 配置补充

`.env.example` 需要补充：

```bash
ANTCODE_API_BASE_URL=https://code.myxiaojin.cn/api/v3
ANTCODE_GROUP_URL=https://code.myxiaojin.cn/groups/xiaojin-skills
ANTCODE_NAMESPACE_ID=354800126
ANTCODE_PRIVATE_TOKEN=replace-with-private-token
SKILL_DEFAULT_BRANCH=master
SKILL_DRAFT_BRANCH_PREFIX=draft
SKILL_DELETE_DRAFT_BRANCH_AFTER_PUBLISH=false
```

`ANTCODE_PRIVATE_TOKEN` 只允许后端读取，前端只展示“已配置/未配置”。

快速开发期补充：

- 为了便于本地快速联调，允许开发者把真实 token 写入本机未跟踪文件 `.env.local` 或 `backend/.env.local`。
- `.env.local` 和 `backend/.env.local` 必须加入 `.gitignore`，不得提交。
- PRD、README、测试快照、审计日志、错误日志和 sqlite 明文字段中不得出现真实 token。
- Agent 实现时应优先读取环境变量；本地启动脚本可自动加载 `.env.local`。
- 后续 token 重置后，只需要更新本机 `.env.local`，不应修改仓库文档。

本地示例：

```bash
ANTCODE_PRIVATE_TOKEN=<put-real-token-in-local-env-only>
```

## 5. `SKILL.md` 一致性修复要求

系统必须保证每个 Skill 的 `SKILL.md` 只有一个 front matter 块。

必须新增校验：

- 文件必须以 `---` 开头。
- 只能存在一个开头 front matter。
- front matter 结束后，正文中如果再次出现疑似完整 front matter，应提示错误或警告。
- `name` 必须与 Skill 名称一致。
- `description` 必须与数据库 description 保持同步，或提示用户选择以哪一边为准。

必须新增修复入口：

- 在详情页发现双 front matter 时，展示“自动拆分修复”按钮。
- 修复逻辑保留第一个合法 front matter，将后续重复 front matter 移除或转为正文普通文本。
- 修复前后展示 diff，用户确认后保存。

## 6. 验收标准

1. 左侧 6 个菜单均可点击，URL、页面标题、高亮状态一致。
2. 有 Skill 数据时，工作台展示统计卡片和最近记录，不展示错误空态。
3. Skill 列表当前版本显示 `0.1.1` 这类产品版本号，不显示内部 version id。
4. 创建 Skill 时，用户粘贴完整 `SKILL.md` 不会产生双 front matter。
5. 保存或发布包含双 front matter 的 `SKILL.md` 会被拦截。
6. Skill 详情页可看到校验状态、Git 绑定状态、当前产品版本。
7. 版本历史选择两个版本后，按钮文案明确显示对比方向。
8. 版本对比页能清楚展示 added/modified/removed 文件和左右 diff。
9. LLM 任务落地前必须看到 patch diff，已落地任务不可重复落地。
10. 审计日志中的 Skill、版本、LLM Job 都可跳转到对应详情。
11. 设置页不再是占位页，能展示 Git/LLM/限制/规范信息，并能测试连接。
12. 所有新增页面和弹窗在 1365x768 视口下无明显文本重叠和按钮挤压。
13. 首次保存草稿或首次发布 Skill 时，系统能在 `xiaojin-skills` group 下创建独立仓库。
14. 草稿保存后，远端仓库存在 `draft/{user_id}/{skill_name}` 分支和草稿 commit。
15. 正式发布后，`master` 分支包含发布内容，`skill_versions.git_commit_sha` 指向 `master` commit。
16. 本地删除临时 clone 后，系统仍能通过 `repository/sync` 从远端仓库恢复 Skill 文件树和版本信息。
17. AntCode token 不出现在仓库文档、前端页面、审计日志、错误日志和 sqlite 明文字段中；快速开发期只能放在未跟踪的 `.env.local`。

## 7. 推荐实施顺序

1. 实现 AntCode API client：读取 `ANTCODE_PRIVATE_TOKEN`，支持获取 group、创建项目、获取项目详情、列分支、创建草稿分支。
2. 调整数据模型：补充 AntCode project metadata、草稿分支、草稿 commit、正式发布 commit。
3. 改造保存草稿：当前编辑内容提交到远端草稿分支，不再只保存本地内容。
4. 改造正式发布：展示草稿 diff，确认后合并到 `master`，创建 tag 和版本记录。
5. 修复 DTO：补充 Skill 名称、产品版本、校验状态、LLM applied 状态、Git project 信息。
6. 修复 `SKILL.md` 校验与双 front matter 防护。
7. 完善 Skill 列表、详情、版本历史、diff 页。
8. 完善 LLM 任务落地前 diff 与幂等控制，LLM 落地也必须进入草稿分支。
9. 完善审计日志可读性和跳转。
10. 实现设置页只读信息、AntCode API 测试、Git 推送测试和 LLM 连接测试。
11. 最后统一补面包屑、菜单 tooltip、筛选状态保留和响应式检查。
