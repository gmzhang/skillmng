# Skill 管理系统 PRD5：真实发布链路一致性与全功能验收收口

版本：v0.1  
日期：2026-05-27  
验收地址：http://localhost:5173/  
验收用户：`bob1`，来自 Cookie 登录态  
依赖文档：[feature/prd1.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd1.md)、[feature/prd2.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd2.md)、[feature/prd3.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd3.md)、[feature/prd4.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd4.md)、[doc/guifan.md](/Users/zhangguangming/Desktop/work/code/skillmng/doc/guifan.md)、[doc/antcode-api-guide.md](/Users/zhangguangming/Desktop/work/code/skillmng/doc/antcode-api-guide.md)

## 1. 背景

PRD4 完成后，系统已经具备较完整的可用形态：

1. 左侧菜单均可跳转。
2. 工作台可以展示当前用户、环境健康、Skill 数量、版本数量、LLM 任务数量、近期审计。
3. Skill 已经可以通过 LLM 创建，并同步到 AntCode 仓库。
4. Skill 详情页可以查看文件、编辑文件、同步仓库、发布版本。
5. 版本页可以查看历史版本，并支持版本对比。
6. LLM 任务页可以查看输入、输出、patch 文件、测试建议和风险。
7. 设置页可以真实测试 AntCode 连接和 LLM 连接，并展示测试结果。

本次进一步验证发现，系统主流程已经基本跑通，但在“最终发布到 Git 后给其他系统使用”这个核心目标上，还存在几个需要优先修复的一致性问题。PRD5 的目标是把发布链路从“能跑通”收口到“状态可信、可复现、可审计、可验收”。

## 2. 本次验证结论

整体评价：当前系统已经可试用，真实 LLM、AntCode group、版本发布、审计日志等关键模块都已经成型。

必须修复的问题：

1. 版本发布没有生成 Git tag。
2. 草稿分支状态和远端实际分支不一致。
3. 本地 Git 仓库存在缺少 `origin` remote 的情况，导致草稿 diff 和草稿提交接口失败。
4. 仓库 SSH URL / repo template 显示和实际接口返回存在不一致。
5. 审计日志的 action 和 commit 信息还不够可读、可跳转。

建议增强的问题：

1. LLM 任务列表长文本可读性需要优化。
2. 恢复版本、删除 Skill、上传 zip、下载 zip 等高风险或文件类操作需要补全确认和 E2E 验收。
3. 同步仓库成功后，需要主动修正本地数据库中已经失效的 draft 状态。

## 3. 已验证通过的功能

### 3.1 工作台

地址：`/`

已验证：

1. 可以显示当前 Cookie 用户 `bob1`。
2. 可以显示环境健康：
   - 用户：`bob1`
   - LLM：`anthropic / qwen3.6-plus`
   - AntCode Token：已配置
   - LLM Token：已配置
   - 代理：已配置
   - 数据库：`1 个 Skill`
3. 可以显示 Skill 总数、版本总数、LLM 任务总数、近期审计。
4. 可以显示最近更新的 Skill。
5. 可以显示最近发布版本。
6. 可以显示最近动态。

结论：工作台信息密度和入口已经够用，可以作为默认首页。

### 3.2 Skill 列表

地址：`/skills`

已验证：

1. 可以展示已创建的 Skill：`web-search-mcp`。
2. 可以展示当前版本：`v0.1.1`。
3. 可以展示 AntCode 仓库链接。
4. 可以展示 Git 状态。
5. 可以进入详情页、编辑页、版本页。
6. 导入菜单可以打开，包含：
   - 上传 zip 导入。
   - 粘贴 SKILL.md。
   - 绑定 Git remote。

注意：

1. “绑定 Git remote”在列表页仍应保持禁用或引导用户先进入详情页。
2. 下载 zip 入口存在，但本次没有完整验证下载文件内容。
3. 删除 Skill 入口存在，但本次没有执行删除。

### 3.3 创建 Skill

地址：`/skills/new`

已验证：

1. 手动创建 tab 可以展示名称、描述、argument-hint、开关、正文等字段。
2. LLM 辅助 tab 可以展示 provider、model、API style、token 状态。
3. LLM 辅助 tab 可以填写 Skill 名称、描述、目标、场景、触发关键词、目标 Agent、参考材料、约束等字段。
4. 粘贴 SKILL.md 入口可以跳转到创建页。

注意：

1. 本次没有新增第二个真实 Skill，避免产生过多远端仓库。
2. 后续 E2E 必须使用专门测试 Skill 完整验证创建、提交、发布、删除或归档流程。

### 3.4 Skill 详情

地址：`/skills/1`

已验证：

1. 可以展示 Skill 名称、状态、校验结果、AntCode 仓库链接。
2. 可以展示当前版本、主分支、草稿分支、草稿 commit、发布 commit。
3. 文件树可以打开文件。
4. `references/channel_mapping.md` 可以正常查看。
5. 编辑模式可以进入和退出。
6. 新建文件弹窗可以打开和关闭。
7. 同步仓库按钮可以调用成功。

发现的问题：

1. 页面显示存在草稿分支：`draft/bob1/web-search-mcp`。
2. 同步仓库接口返回远端分支只有 `master`。
3. 这说明 UI / 数据库中的 draft 状态和远端真实状态不一致。

### 3.5 版本管理

地址：`/skills/1/versions`

已验证：

1. 可以展示两个版本：
   - `v0.1.1`
   - `v0.1.0`
2. 可以勾选两个版本。
3. 可以进入版本对比页。
4. 版本对比页可以展示 `SKILL.md` 的 side-by-side diff。

发现的问题：

1. 两个版本的 tag 列均为 `-`。
2. 接口返回 `git_tag: null`。
3. 同步仓库返回 `tags: []`。
4. 版本发布目前只有 commit，没有 tag，不符合“发布版本可被其他系统稳定消费”的要求。

### 3.6 LLM 任务

地址：`/llm-jobs`

已验证：

1. 可以展示已成功的 create 任务。
2. 可以显示模型 `qwen3.6-plus`。
3. 可以关联到 Skill。
4. 任务详情 drawer 可以显示：
   - 状态。
   - 类型。
   - 模型。
   - Skill。
   - 输入。
   - 输出摘要。
   - patch 文件。
   - 测试建议。
   - 风险。
5. LLM 任务证据链已经较完整。

建议：

1. 列表页不要展示过长的 input 文本。
2. 长输入保留在详情 drawer 中即可。
3. 列表列宽要控制，避免模型、输入、输出挤压表格。

### 3.7 审计日志

地址：`/audit-logs`

已验证：

1. 可以展示版本发布、文件写入、仓库同步、仓库创建、LLM 创建、设置测试等日志。
2. 可以关联 Skill、版本、LLM 任务。
3. 发布时间和 action 基本可追踪。

发现的问题：

1. `settings.antcode.test`、`settings.llm.test` 仍是原始 action key，不够产品化。
2. commit SHA 目前只是文本，不明显可点击。
3. 对发布类日志，应直接链接到 AntCode commit 页面。

### 3.8 设置

地址：`/settings`

已验证：

1. AntCode 连接测试成功。
2. LLM 连接测试成功。
3. 页面可以展示最近一次连接测试结果。
4. AntCode 测试结果展示：
   - 用户名。
   - group path。
   - 代理状态。
5. LLM 测试结果展示：
   - provider。
   - model。
   - API style。
   - base URL。
   - 请求路径。
   - HTTP status。
   - 代理状态。
6. token 未明文展示。

结论：设置页已经达到“可诊断”的基本要求。

## 4. 关键问题与修复要求

### 4.1 发布版本必须创建 Git tag

现象：

1. `GET /api/skills/1/versions` 返回 `git_tag: null`。
2. 版本页 tag 列显示 `-`。
3. `POST /api/skills/1/repository/sync` 返回 `tags: []`。

要求：

1. 每次发布版本时，必须创建 Git tag，格式固定为：
   - `v0.1.0`
   - `v0.1.1`
   - `v{semver}`
2. tag 必须指向本次发布合并到 `master` 后的发布 commit。
3. tag 必须 push 到远端 AntCode 仓库。
4. 数据库 `skill_versions.git_tag` 必须保存 tag 名称。
5. Skill 当前状态中的 `published_tag` 必须同步更新。
6. 版本页 tag 列显示真实 tag。
7. Skill 详情页当前版本旁边显示真实 tag。
8. 审计日志 `skill.version.publish` 需要记录：
   - version。
   - commit sha。
   - tag。
   - branch。

验收标准：

1. 发布 `0.1.2` 后，版本页显示 `v0.1.2` tag。
2. AntCode 仓库 tag 列表能看到 `v0.1.2`。
3. `GET /api/skills/{id}/versions` 返回 `git_tag: "v0.1.2"`。
4. `GET /api/skills/{id}` 返回 `published_tag: "v0.1.2"`。

### 4.2 修复本地 Git 仓库缺少 origin 的问题

现象：

调用草稿 diff 或草稿 commit 接口时，出现错误：

```text
git remote set-url origin git@code.myxiaojin.cn:cqcfd7cn/xiaojin-skills/web-search-mcp.git
error: No such remote 'origin'
```

要求：

1. 所有需要操作 Git 的入口，在执行 fetch、pull、push、set-url 前，必须确保本地仓库存在 `origin` remote。
2. 如果本地目录已经是 Git 仓库但没有 `origin`：
   - 执行 `git remote add origin <ssh_url>`。
3. 如果本地目录有 `origin` 但 URL 与数据库记录不一致：
   - 执行 `git remote set-url origin <ssh_url>`。
4. 如果本地目录不是 Git 仓库：
   - 优先 clone 远端仓库。
   - 如果远端为空或不存在，再走初始化流程。
5. 不允许因为 `origin` 不存在导致接口 500 或业务错误。
6. 后端应抽象一个统一方法，例如 `ensure_git_remote(skill)`，所有 Git 操作共用。

涉及接口至少包括：

1. 仓库创建。
2. 仓库同步。
3. 文件写入。
4. 草稿提交。
5. 草稿 diff。
6. 版本发布。
7. 版本恢复。
8. zip 导入后提交。

验收标准：

1. 删除本地 repo 的 `origin` 后，再调用草稿 diff，系统可以自动修复 remote 并返回 diff。
2. 删除本地 repo 的 `origin` 后，再提交草稿，系统可以自动修复 remote 并成功提交。
3. 错误日志和审计日志中不得泄漏 token。

### 4.3 统一 repo URL 和真实 remote 来源

现象：

1. 设置页 repo template 显示：

```text
git@code.myxiaojin.cn:xiaojin-skills/{repo_slug}.git
```

2. Skill 详情接口曾返回：

```text
git@code.myxiaojin.cn:cqcfd7cn/xiaojin-skills/web-search-mcp.git
```

问题：

如果 UI、数据库、实际 remote 使用不同 URL，后续 fetch、push、commit 链接都会变得不可信。

要求：

1. 创建仓库后，必须以 AntCode API 返回的真实 `ssh_url_to_repo` 或等价字段作为 Skill 的 `git_ssh_url`。
2. repo template 只能作为创建前的 fallback，不应覆盖 AntCode 返回的真实 URL。
3. 设置页可以继续展示 repo template，但 Skill 详情页必须展示真实 remote。
4. 同步仓库时，如果本地 origin 与 Skill `git_ssh_url` 不一致，应以 Skill `git_ssh_url` 修正本地 origin。
5. 审计日志记录仓库创建时，应记录：
   - project_id。
   - path_with_namespace。
   - web_url。
   - ssh_url。

验收标准：

1. Skill 详情页显示的 Git SSH URL 与 `git remote get-url origin` 一致。
2. AntCode 仓库链接、commit 链接、tag 链接都能打开到同一个项目。

### 4.4 草稿分支状态必须和远端一致

现象：

1. UI 显示“有未发布草稿”。
2. Skill 详情显示 draft branch 和 draft commit。
3. 仓库同步返回远端 branches 只有 `master`。

要求：

1. 系统需要明确区分三种草稿状态：
   - `none`：没有草稿。
   - `local_only`：本地有草稿 commit，但尚未 push 到远端。
   - `remote`：远端存在 draft branch。
2. 如果目标设计是“本地不保留 Skill 内容，每次提交都是 Git commit”，推荐草稿提交后也 push 到远端 draft branch。
3. 发布成功后，应根据配置决定是否删除 draft branch：
   - `DELETE_DRAFT_BRANCH_AFTER_PUBLISH=true`：发布后删除远端 draft branch，并清空数据库 draft 状态。
   - `DELETE_DRAFT_BRANCH_AFTER_PUBLISH=false`：保留 draft branch，但其 commit 必须与 master 发布 commit 或后续草稿一致。
4. 仓库同步时必须拉取远端分支列表，修正数据库状态：
   - 如果数据库有 `draft_branch`，但远端没有该 branch，且本地也没有有效草稿 commit，则清空 draft 状态。
   - 如果本地有草稿但远端没有，UI 显示“本地草稿未推送”，并提供“推送草稿分支”按钮。
   - 如果远端有 draft branch，UI 显示“远端草稿”。
5. Skill 列表中的 Git 状态不能只依赖数据库字段，需要结合同步结果或最近一次 sync snapshot。

验收标准：

1. 仓库同步后，如果远端只有 `master`，列表页不再错误显示“有未发布草稿”。
2. 新增文件并提交草稿后，远端出现 `draft/bob1/{skill_slug}` 分支。
3. 发布后，若配置删除草稿分支，远端 draft branch 消失，UI 显示“无草稿”。
4. 发布后，若配置保留草稿分支，UI 状态不能误导用户存在未发布差异。

### 4.5 草稿 diff 和草稿提交必须可用

要求：

1. Skill 详情页应提供明确的“查看草稿差异”入口。
2. 草稿 diff 应展示：
   - 对比基准：`master` 当前 commit。
   - 草稿来源：draft branch 或 local draft commit。
   - 文件列表。
   - added / modified / removed 统计。
3. 如果没有草稿差异，显示“草稿与 master 一致”。
4. 草稿提交按钮应允许填写 commit message。
5. 草稿提交成功后必须：
   - 创建 Git commit。
   - push 到远端 draft branch。
   - 更新数据库 draft branch 和 draft commit。
   - 写入审计日志。

验收标准：

1. 修改 `SKILL.md` 后点击保存，系统可以生成草稿差异。
2. 提交草稿后，AntCode 上能看到 draft branch 和对应 commit。
3. 再次打开详情页，草稿状态、commit、diff 均正确。

### 4.6 审计日志需要增强可读性和跳转能力

现象：

1. 设置测试类 action 仍显示原始 key。
2. commit SHA 不是明显链接。

要求：

1. 审计 action 增加中文显示映射：
   - `settings.antcode.test`：测试 AntCode 连接。
   - `settings.llm.test`：测试 LLM 连接。
   - `skill.version.publish`：发布版本。
   - `skill.repository.sync`：同步仓库。
   - `skill.repository.create`：创建仓库。
   - `skill.file.write`：写入文件。
   - `skill.file.upload`：上传文件。
   - `skill.version.restore`：恢复版本。
2. 审计表格保留原始 action，可放在 tooltip 或详情里。
3. 如果日志有 commit sha 和 repo web url，commit 必须渲染为可点击链接。
4. 如果日志有 tag，tag 必须渲染为可点击链接。
5. 审计详情应展示结构化 metadata，但隐藏 token、Cookie、Authorization。

验收标准：

1. 审计日志里不再直接暴露 `settings.llm.test` 作为主显示文案。
2. 点击发布日志的 commit 可以打开 AntCode commit 页面。
3. 点击发布日志的 tag 可以打开 AntCode tag 页面。

### 4.7 版本恢复需要明确语义

要求：

1. 恢复历史版本不能直接重写 `master`。
2. 恢复历史版本应创建一个新的 draft commit。
3. 用户确认后再发布为新版本。
4. 恢复弹窗必须说明：
   - 将恢复哪个版本。
   - 会生成新的草稿。
   - 不会删除已有版本。
   - 发布后会产生新的版本号和 tag。
5. 恢复操作写入审计日志。

验收标准：

1. 从 `v0.1.0` 恢复时，生成新的草稿 diff。
2. 发布恢复结果时，生成 `v0.1.2` 或用户填写的新版本号。
3. 历史版本仍保留。

### 4.8 下载、导入、删除流程补齐验收

要求：

1. 下载 zip：
   - zip 内必须包含 `SKILL.md`。
   - zip 内必须包含 references / scripts / assets 等 Skill 文件。
   - zip 不包含 `.git`、本地缓存、数据库文件、token。
2. 上传 zip 导入：
   - 校验路径安全。
   - 校验单文件大小。
   - 校验 `SKILL.md` front matter。
   - 导入后生成新的 Skill 草稿。
3. 粘贴 SKILL.md 导入：
   - 支持 front matter。
   - 自动拆分 name / description / body。
   - 用户确认后创建 Skill。
4. 删除 Skill：
   - 第一阶段建议做软删除或归档。
   - 删除前弹窗说明不会删除远端仓库，除非后续明确支持远端删除。
   - 删除或归档写入审计日志。

验收标准：

1. 下载 zip 后解压，文件结构和详情页一致。
2. 上传同一个 zip，可以生成一个新的 Skill 或提示 slug 冲突并要求用户改名。
3. 删除 Skill 后，列表默认不展示，但审计日志仍可追踪。

### 4.9 LLM 任务列表可读性优化

要求：

1. 列表页保留摘要，不直接展示大段 input。
2. 长输入、长输出、patch diff 放到 drawer 里。
3. 列表建议列：
   - ID。
   - 类型。
   - 状态。
   - Skill。
   - provider / model。
   - 耗时。
   - 创建时间。
   - 操作。
4. 失败任务应在列表显示短错误摘要，详情展示完整错误。

验收标准：

1. 表格在 1440px 宽度下不出现明显挤压。
2. 长文本不会撑破表格。

## 5. API 和数据模型要求

### 5.1 Skill 当前状态字段

建议后端返回：

```json
{
  "published_commit_sha": "bbb8c386...",
  "published_tag": "v0.1.1",
  "default_branch": "master",
  "draft_branch": "draft/bob1/web-search-mcp",
  "draft_commit_sha": "d4b50030...",
  "draft_status": "none | local_only | remote",
  "draft_has_diff": true,
  "git_web_url": "https://code.myxiaojin.cn/xiaojin-skills/web-search-mcp",
  "git_ssh_url": "git@code.myxiaojin.cn:xxx/xiaojin-skills/web-search-mcp.git"
}
```

### 5.2 Version 字段

建议后端返回：

```json
{
  "version": "0.1.2",
  "commit_sha": "xxxx",
  "git_tag": "v0.1.2",
  "tag_url": "https://code.myxiaojin.cn/xiaojin-skills/web-search-mcp/-/tags/v0.1.2",
  "commit_url": "https://code.myxiaojin.cn/xiaojin-skills/web-search-mcp/-/commit/xxxx"
}
```

### 5.3 审计 metadata

发布版本审计建议：

```json
{
  "action": "skill.version.publish",
  "skill_id": 1,
  "version": "0.1.2",
  "branch": "master",
  "commit_sha": "xxxx",
  "git_tag": "v0.1.2",
  "commit_url": "https://code.myxiaojin.cn/...",
  "tag_url": "https://code.myxiaojin.cn/..."
}
```

草稿提交审计建议：

```json
{
  "action": "skill.draft.commit",
  "skill_id": 1,
  "draft_branch": "draft/bob1/web-search-mcp",
  "commit_sha": "xxxx",
  "pushed": true
}
```

## 6. 端到端验收脚本

Agent 完成 PRD5 后，必须执行以下 E2E 验收。可以使用一个临时测试 Skill，验收完成后由用户统一清理。

### 6.1 发布链路 E2E

步骤：

1. 使用 Cookie `user_id=bob1` 打开首页。
2. 创建一个测试 Skill，例如 `prd5-smoke-skill`。
3. 创建或绑定 AntCode 仓库。
4. 写入 `SKILL.md` 和一个 references 文件。
5. 提交草稿。
6. 确认远端存在 draft branch。
7. 查看草稿 diff。
8. 发布 `0.1.0`。
9. 确认 master 有发布 commit。
10. 确认远端存在 tag `v0.1.0`。
11. 修改 `SKILL.md`。
12. 提交草稿。
13. 发布 `0.1.1`。
14. 对比 `v0.1.0` 和 `v0.1.1`。
15. 查看审计日志。

通过标准：

1. 所有步骤无接口错误。
2. 所有 Git 操作在 AntCode 上可复查。
3. tag、commit、branch、数据库字段一致。

### 6.2 同步修复 E2E

步骤：

1. 手动或通过测试代码移除本地 repo 的 `origin` remote。
2. 调用仓库同步。
3. 调用草稿 diff。
4. 调用草稿提交。

通过标准：

1. 系统自动恢复 `origin`。
2. 不再出现 `No such remote 'origin'`。

### 6.3 导入导出 E2E

步骤：

1. 下载一个已发布 Skill 的 zip。
2. 解压检查文件。
3. 重新上传 zip 导入。
4. 处理 slug 冲突。
5. 确认新 Skill 文件完整。

通过标准：

1. zip 内容安全且完整。
2. 导入后的 Skill 通过规范校验。

## 7. 优先级

P0：

1. 发布版本创建并 push Git tag。
2. 修复本地 repo 缺少 `origin`。
3. 草稿分支状态和远端一致。
4. 草稿 diff / 草稿提交可用。

P1：

1. 统一 repo URL 来源。
2. 审计日志中文化和 commit/tag 跳转。
3. 版本恢复语义明确为“恢复到草稿”。

P2：

1. LLM 任务列表可读性优化。
2. 下载、上传、删除流程的完整 UI polish。

## 8. 非目标

本 PRD 不要求：

1. 实现完整权限后台。
2. 实现远端仓库物理删除。
3. 实现多租户管理后台。
4. 替换 sqlite。
5. 引入复杂 CI/CD。

## 9. 交付要求

Agent 执行 PRD5 时，需要交付：

1. 后端代码修改。
2. 前端代码修改。
3. 数据库迁移或兼容升级逻辑。
4. 必要的单元测试。
5. 必要的接口测试。
6. 一次真实 E2E 验收记录。
7. 不得在日志、审计、前端页面输出 token、Cookie、Authorization header。

最终验收时，请在 `http://localhost:5173/` 逐页验证：

1. 工作台。
2. Skill 列表。
3. 创建 Skill。
4. Skill 详情。
5. 文件编辑。
6. 草稿 diff。
7. 版本发布。
8. 版本对比。
9. LLM 任务。
10. 审计日志。
11. 设置页连接测试。

