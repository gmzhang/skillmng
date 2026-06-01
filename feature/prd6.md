# Skill 管理系统 PRD6：发布链路收敛与真实 Git 真源治理

版本：v0.1  
日期：2026-05-29  
依赖文档：
- [feature/prd1.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd1.md)
- [feature/prd2.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd2.md)
- [feature/prd3.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd3.md)
- [feature/prd4.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd4.md)
- [feature/prd5.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd5.md)
- [doc/guifan.md](/Users/zhangguangming/Desktop/work/code/skillmng/doc/guifan.md)
- [doc/antcode-api-guide.md](/Users/zhangguangming/Desktop/work/code/skillmng/doc/antcode-api-guide.md)
- [CODEX_HANDOFF.md](/Users/zhangguangming/Desktop/work/code/skillmng/CODEX_HANDOFF.md)

## 1. 背景

当前系统已经具备真实 LLM、AntCode 仓库创建、草稿分支提交、版本发布、审计日志和设置诊断等能力。但代码中仍有两套发布链路并存：

1. 旧链路：`POST /api/skills/{skill_id}/versions`，以本地 Git 版本发布为主。
2. 新链路：`POST /api/skills/{skill_id}/drafts/commit` 后调用 `POST /api/skills/{skill_id}/publish`，将远端草稿分支合并到 `master` 并创建 tag。

PRD5 已经明确：Skill 内容真源必须是远端 AntCode Git 仓库，发布版本必须能被其他系统从 `master` 和 tag 稳定消费。因此 PRD6 的目标是把发布链路从“双轨并存”收敛为“AntCode workflow 为唯一正式发布路径”，并补齐发布前预检、半成功状态治理、LLM 落地草稿提交、代理配置和安全收尾。

## 2. 总目标

1. 正式发布只以远端 AntCode `master` 分支和 `v{version}` tag 成功推送为准。
2. sqlite 只保存编辑草稿、索引和审计记录，不得被视为正式 Skill 内容真源。
3. `current_version`、`current_version_id`、`published_commit_sha`、`published_tag` 只能在远端发布成功后更新。
4. 旧 `/versions` 发布接口不得在生产 AntCode 模式下制造“本地成功但远端失败仍被视为发布”的状态。
5. LLM 创建/更新落地后必须进入统一 AntCode 草稿分支流程。
6. 设置页显示的代理状态必须和后端真实出站请求行为一致。
7. 敏感 token 不得出现在文档、日志、审计、前端或提交信息中。

## 3. 关键概念

### 3.1 sqlite draft

用户在页面中编辑和保存的当前文件树。它用于快速展示、编辑和生成草稿，但不是正式发布结果。

### 3.2 remote draft branch

远端仓库中的草稿分支：

```text
draft/{user_id}/{skill_name}
```

草稿分支是发布候选。`draft_status=remote` 表示远端存在对应分支且数据库记录的 `draft_commit_sha` 应与远端 head 一致。

### 3.3 published master/tag

正式发布结果：

```text
master
v{version}
```

其他系统只应消费远端 `master` 分支和 `v{version}` tag。只有这一层成功后，系统才能更新当前版本指针。

## 4. P0 必须修复

### 4.1 敏感 token 文档治理

当前 `doc/antcode-api-guide.md` 中出现了明文 AntCode token 示例。必须处理：

1. 立即通知使用者旋转该 token。
2. 文档中所有 token 示例统一改为 `$TOKEN` 或 `<ANTCODE_PRIVATE_TOKEN>`。
3. 不得在日志、审计、测试快照、前端页面、错误信息中输出 token 明文。
4. 设置页只展示“已配置 / 未配置”，不展示 token 前后缀；若确需区分，只展示不可逆 hash 后 6 位。

验收：

- 仓库中搜索不到旧 token 明文。
- 设置页和审计日志不包含 token 明文。

### 4.2 正式发布链路唯一化

前端正式发布入口只能走：

```text
POST /api/skills/{skill_id}/drafts/commit
GET  /api/skills/{skill_id}/drafts/diff
POST /api/skills/{skill_id}/publish
```

旧接口：

```text
POST /api/skills/{skill_id}/versions
```

必须降级为 legacy/local 发布接口：

1. 测试环境可以继续使用，保证现有后端本地 Git 测试可运行。
2. 生产 AntCode 模式下不得被普通 UI 使用。
3. 如果生产环境仍允许调用，必须明确返回 `local_only` / `git_pushed=false`，且不得更新正式发布指针。
4. API 文档和前端代码中不得再把它称为正常发布入口。

验收：

- Skill 详情页和版本页发布按钮不调用 `/versions`。
- 生产 AntCode 模式下，直接调用 `/versions` 不会造成“远端失败但 current_version 已更新”的状态。
- 审计日志能区分 `skill.version.publish` 与 legacy/local publish。

### 4.3 发布前预检

`POST /api/skills/{skill_id}/publish` 在执行 merge/tag/push 前必须完成预检：

1. `version` 符合 `MAJOR.MINOR.PATCH`。
2. 当前 Skill 下该 `version` 不存在。
3. 远端 `v{version}` tag 不存在。
4. Skill 已绑定 AntCode project。
5. 远端 draft branch 存在。
6. 数据库中的 `draft_commit_sha` 与远端 draft branch head 一致。
7. `SKILL.md` 校验没有 error。
8. 本地 clone 有 `origin` remote，且 remote URL 与当前 Skill metadata 一致。
9. 后端可以 fetch 远端仓库。

任何预检失败都必须在 merge/tag/push 前返回明确错误，且不得更新 `Skill` 或 `SkillVersion` 的正式发布字段。

验收：

- 重复版本号不会创建远端 tag。
- 重复 tag 不会创建 `SkillVersion`。
- 远端 draft branch 缺失时发布失败，`current_version` 不变。
- `SKILL.md` 校验 error 时发布失败。

### 4.4 发布事务顺序与半成功治理

发布操作涉及远端 Git 和 sqlite，不能真正依赖数据库事务覆盖 Git 副作用。必须明确顺序和补偿策略：

推荐顺序：

1. 预检数据库版本和远端 tag。
2. fetch 远端 master/draft。
3. merge draft 到 master 或首次发布时从 draft 创建 master。
4. 创建本地 tag。
5. push master。
6. push tag。
7. 写入 `SkillVersion`。
8. 更新 `Skill.current_version_id/current_version/published_commit_sha/published_tag/status/draft_status`。
9. 写审计日志，包含 commit/tag URL。

如果第 7 步数据库写入失败，而第 5/6 步已经成功，必须返回可诊断错误，并提供后续 sync/backfill 能力从远端 tag 修复 sqlite 索引。

验收：

- push 失败不写正式版本记录。
- DB 版本冲突在 push 前被发现。
- sync 能识别远端已存在的 tag，并补齐缺失的 `published_tag` / `current_version` / `current_version_id`。

### 4.5 LLM 落地统一进入 AntCode 草稿流程

当前 LLM 落地后的草稿提交不得继续走旧 `git_service.commit_draft` 分支逻辑。必须统一调用 AntCode workflow：

```text
antcode_skill_service.create_or_bind_repository
antcode_skill_service.commit_draft
```

要求：

1. LLM create 落地为 Skill 后，自动创建或绑定 AntCode 仓库。
2. LLM update 写回文件后，自动提交到远端 draft branch。
3. 草稿提交失败不能只写 warning 后吞掉；必须在返回结果、任务详情或审计日志中可见。
4. `draft_status=local_only` 不允许被发布接口接受。

验收：

- LLM apply 后 Skill 详情页能看到 remote draft branch 和 draft commit。
- 草稿 push 失败时 UI 能看到明确提示。
- 发布接口拒绝 `local_only` 草稿。

### 4.6 AntCode HTTP 代理一致性

设置页已经展示代理状态，但 AntCode HTTP client 必须真实使用代理配置：

```text
https_proxy
http_proxy
all_proxy
```

要求：

1. `AntCodeClient` 构造 `httpx.Client` 时读取 settings 中的 proxy。
2. 设置页 `proxy_enabled` 必须反映 AntCode 和 LLM HTTP 请求的真实行为。
3. Git SSH/HTTPS 仍应通过环境变量或 `GIT_SSH_COMMAND` 使用对应网络配置。

验收：

- `test-git` 使用的 httpx client 走同一 proxy 配置。
- 单元测试覆盖 proxy 注入。

## 5. P1 强烈建议

### 5.1 发布前 diff 确认

Skill 详情页和版本页发布新版本时，不应直接 `commitDraft -> publish`。应改为：

1. 用户点击发布。
2. 后端提交当前 sqlite 文件树到 draft branch。
3. 前端拉取 `/drafts/diff`。
4. 弹窗展示：
   - AntCode 仓库 URL。
   - 目标分支 `master`。
   - 草稿分支。
   - draft commit SHA。
   - 预计 tag。
   - 文件 diff 列表。
5. 用户确认后调用 `/publish`。

验收：

- 用户能在发布前看到文件差异。
- 新增、修改、删除文件都有清晰提示。
- 没有 diff 时允许发布但必须明确提示“内容无变化，将形成空发布/或拒绝”，策略需统一。

### 5.2 restore 改为 AntCode workflow

版本恢复不能继续只走旧 `/versions/{id}/restore` 的本地发布语义。建议流程：

1. 从目标历史 commit 读取文件树。
2. 写回 sqlite draft。
3. 提交到远端 draft branch。
4. 展示 draft vs master diff。
5. 用户确认后发布为新版本。

验收：

- 恢复不会重写历史。
- 恢复后的新版本也有 master commit 和 `v{version}` tag。
- 恢复失败不污染当前正式版本指针。

### 5.3 sync 语义增强

`/repository/sync` 需要从远端恢复可信状态：

1. 读取远端 branches/tags。
2. 校正不存在的 draft branch 状态。
3. 按 semver tag 或 tag commit 时间识别最新正式版本，不能简单假设 `tags[0]` 是最新。
4. 回填 `SkillVersion.git_tag`、`Skill.published_tag`、`Skill.current_version`、`Skill.current_version_id`。
5. 从远端 master 恢复 sqlite 文件树。

验收：

- 远端删除 draft branch 后，sync 会清空本地 draft 状态。
- 远端有 tag 但 sqlite 缺索引时，sync 能给出可修复信息或自动补齐。

### 5.4 API 命名清理

当前存在相近接口：

```text
/repository/create
/repository
/draft/commit
/drafts/commit
/versions
/publish
```

建议保留新接口，旧接口只做兼容，并在代码注释和文档中标注 legacy：

正式接口：

```text
POST /api/skills/{id}/repository/create
POST /api/skills/{id}/drafts/commit
GET  /api/skills/{id}/drafts/diff
POST /api/skills/{id}/publish
POST /api/skills/{id}/repository/sync
```

兼容接口：

```text
PATCH /api/skills/{id}/repository
POST  /api/skills/{id}/versions
POST  /api/skills/{id}/versions/{version_id}/restore
```

## 6. 数据状态规则

### 6.1 Skill 字段

| 字段 | 更新条件 |
|---|---|
| `draft_branch` | 成功提交或同步到远端 draft branch 后更新 |
| `draft_commit_sha` | 必须等于远端 draft branch head |
| `draft_status` | `none` / `remote` / `local_only`;发布只接受 `remote` |
| `published_commit_sha` | master push 成功后更新 |
| `published_tag` | tag push 成功后更新 |
| `current_version` | tag push + SkillVersion 写入成功后更新 |
| `current_version_id` | SkillVersion 写入成功后更新 |

### 6.2 SkillVersion 字段

`SkillVersion` 只代表正式发布版本。不得为 local-only commit 创建正式 `SkillVersion`，除非字段和 UI 明确标注为 legacy/local，并且不会被其他系统消费。

### 6.3 审计字段

发布审计必须包含：

```json
{
  "version": "0.1.2",
  "branch": "master",
  "draft_branch": "draft/bob1/web-search-mcp",
  "draft_commit_sha": "...",
  "commit_sha": "...",
  "git_tag": "v0.1.2",
  "commit_url": "...",
  "tag_url": "..."
}
```

不得包含 token、cookie、Authorization header、PRIVATE-TOKEN header。

## 7. 测试要求

### 7.1 后端单元/集成测试

新增或调整测试：

1. AntCode client proxy 注入测试。
2. 空 bare remote：只有 draft branch，首次 publish 创建 master 和 tag。
3. 已有 master：publish 使用 merge commit 并创建 tag。
4. 重复 version：发布前失败，不 push master/tag。
5. 重复 tag：发布前失败，不写 SkillVersion。
6. draft branch 不存在：发布失败，正式字段不变。
7. draft head 与数据库 `draft_commit_sha` 不一致：发布失败。
8. `SKILL.md` 校验 error：发布失败。
9. LLM apply 后调用统一 AntCode draft workflow。
10. sync 发现远端 draft branch 不存在时清空 `draft_status`。

### 7.2 前端检查

必须通过：

```bash
cd frontend && pnpm lint
cd frontend && pnpm build
```

发布弹窗验收：

1. 发布前展示 diff。
2. 展示目标仓库、master、draft branch、draft SHA、预计 tag。
3. 校验 error 时发布按钮禁用或提交后明确失败。
4. `local_only` 草稿不可发布。

### 7.3 后端检查

必须通过：

```bash
cd backend && . .venv/bin/activate && pytest -q
```

### 7.4 收尾检查

每轮实现结束必须运行：

```bash
git status --short
git diff --stat
```

## 8. 非目标

1. 不实现复杂企业 SSO。
2. 不实现多人协作编辑。
3. 不实现在线执行 Skill 脚本。
4. 不删除现有 legacy 测试能力，但必须限制其正式发布语义。
5. 不把 AntCode token、LLM token 或 SSH 私钥写入仓库。

## 9. 推荐实现顺序

1. 先移除文档中的明文 token 并提示旋转。
2. 为 AntCode workflow 增加本地 bare remote 测试框架。
3. 实现发布前预检。
4. 调整 `/publish` 的状态更新顺序和半成功治理。
5. 限制 legacy `/versions` 在生产 AntCode 模式下的正式发布语义。
6. 将 LLM apply 后草稿提交切到 `antcode_skill_service.commit_draft`。
7. 为 AntCode client 注入 proxy。
8. 前端发布弹窗增加 draft diff 确认。
9. 增强 sync 回填状态。
10. 跑全量后端测试、前端 lint/build。

## 10. 验收结论标准

PRD6 完成后，系统必须满足：

1. UI 发布成功意味着远端 AntCode `master` 已更新且 `v{version}` tag 已存在。
2. 任何远端 push/tag 失败都不会更新正式版本指针。
3. 任何 sqlite 版本冲突都在 push 前发现。
4. LLM 生成或更新落地后进入远端 draft branch。
5. 设置页的代理和连接测试结果可信。
6. 审计日志能从版本发布记录直接追到 AntCode commit/tag。
7. 仓库中不再包含明文 token。
