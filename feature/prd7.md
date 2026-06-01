# Skill 管理系统 PRD7：端到端实测问题修复与发布真源校准

版本：v0.1  
日期：2026-05-29  
验收地址：http://localhost:5173/  
验收用户：`skillmng`，来自 Cookie 登录态  
依赖文档：
- [feature/prd1.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd1.md)
- [feature/prd2.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd2.md)
- [feature/prd3.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd3.md)
- [feature/prd4.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd4.md)
- [feature/prd5.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd5.md)
- [feature/prd6.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd6.md)
- [doc/guifan.md](/Users/zhangguangming/Desktop/work/code/skillmng/doc/guifan.md)
- [CODEX_HANDOFF.md](/Users/zhangguangming/Desktop/work/code/skillmng/CODEX_HANDOFF.md)

## 1. 背景

基于 PRD6 的方向，对本地真实页面 `http://localhost:5173/` 进行了一轮端到端验收。测试使用现有登录态 `skillmng`，新建测试 Skill：

```text
codex-e2e-068782
```

测试覆盖：

1. 手动创建 Skill。
2. AntCode 仓库创建。
3. 首次发布 `v0.1.0`。
4. 远端同步。
5. 真实 LLM 辅助更新。
6. LLM 更新写回。
7. 二次发布 `v0.1.1`。
8. 版本历史与 tag/commit 链接。
9. 版本 diff。
10. 设置页 AntCode / LLM 连通性测试。
11. 审计日志。
12. zip 导出。

整体结果：主流程大部分能跑通，但发现两个 P0 问题直接影响“远端 Git 真源”的可信度，必须优先修复。

## 2. 实测通过项

### 2.1 手动创建 Skill

已验证：

1. 创建页能填写 name、description、body。
2. 创建页能展示最终 `SKILL.md` 预览。
3. 保存本地草稿成功。
4. 进入 Skill 详情页后校验状态为“通过”。

测试 Skill：

```text
codex-e2e-068782
```

### 2.2 AntCode 仓库创建

已验证：

1. 点击“在 AntCode 创建仓库”成功。
2. Skill 详情页展示仓库：

```text
xiaojin-skills/codex-e2e-068782
```

3. 仓库链接可见。

### 2.3 首次发布

已验证：

1. 发布弹窗可填写版本号和摘要。
2. 点击“预览变更”后会先提交草稿分支。
3. 发布确认弹窗展示：
   - 目标仓库。
   - 主分支。
   - 草稿分支。
   - 草稿 SHA。
   - 发布版本。
   - 预计 tag。
4. 首次发布 `v0.1.0` 成功。
5. 详情页状态变为 `published`。
6. 版本页展示 `v0.1.0`、commit 链接、tag 链接。

首次发布结果：

```text
version: 0.1.0
tag: v0.1.0
commit: b9b322d2325b2c8523e55386a1c2ac4a190810f2
```

### 2.4 LLM 辅助更新

已验证：

1. 真实 LLM 任务可以提交。
2. 任务状态从 running 变为 succeeded。
3. 输出摘要正常。
4. 点击“写回当前 Skill”后，`SKILL.md` 增加“验收检查清单”小节。
5. 草稿 commit 从首发 commit 更新为新 SHA。

LLM 更新结果：

```text
job_id: 2
status: succeeded
draft_commit_sha: 5f15bfc2f5be15c577cf28e159fb2c421a8eca53
```

### 2.5 二次发布与审计

已验证：

1. 二次发布 `v0.1.1` 成功。
2. 版本页展示两个版本：
   - `v0.1.0`
   - `v0.1.1`
3. 两个版本均有 commit 链接和 tag 链接。
4. 审计日志展示发布、草稿提交、LLM 提交、LLM 落地、设置测试等记录。
5. 发布审计中的 commit/tag 可点击跳转到 AntCode。

二次发布结果：

```text
version: 0.1.1
tag: v0.1.1
commit: 5f15bfc2f5be15c577cf28e159fb2c421a8eca53
```

### 2.6 设置页连接测试

已验证：

1. AntCode API 测试成功。
2. LLM 连接测试成功。
3. 测试结果保留在页面上。
4. LLM API style 自动识别为 `openai-compatible`。

设置页显示：

```text
AntCode: 连接成功:用户 zhangguangming.zgm / 群组 xiaojin-skills
LLM: 连接成功,模型: qwen3.6-plus
```

### 2.7 zip 导出

已验证：

```text
GET /api/skills/2/export.zip
status: 200
content-type: application/zip
size: 693 bytes
```

## 3. P0 问题：同步后 default_branch 被污染为 draft 分支

### 3.1 现象

首次发布 `v0.1.0` 后，详情页显示：

```text
主分支: master
草稿分支: draft/skillmng/codex-e2e-068782
```

点击“从远端同步”后，再回到详情页，主分支变成：

```text
主分支: draft/skillmng/codex-e2e-068782
```

API 返回也确认数据库状态被污染：

```json
{
  "id": 2,
  "name": "codex-e2e-068782",
  "status": "published",
  "current_version": "0.1.1",
  "default_branch": "draft/skillmng/codex-e2e-068782",
  "draft_branch": "draft/skillmng/codex-e2e-068782",
  "draft_commit_sha": "5f15bfc2f5be15c577cf28e159fb2c421a8eca53",
  "published_commit_sha": "5f15bfc2f5be15c577cf28e159fb2c421a8eca53",
  "published_tag": "v0.1.1"
}
```

### 3.2 影响

这是发布真源相关的严重问题：

1. UI 把“正式主分支”显示为 draft branch。
2. 二次发布确认弹窗中“主分支”也显示为 draft branch。
3. 用户会以为系统正在发布到草稿分支。
4. 后端可能基于错误的 `skill.default_branch` 进行 fetch、checkout、merge、diff。
5. 版本 diff API 500 可能与该状态污染有关。

### 3.3 可能原因

推测是 `/repository/sync` 调用 AntCode project metadata 回填时，将 AntCode 返回的 `default_branch` 直接写入 `Skill.default_branch`。在当前 AntCode 场景中，项目 default branch 可能被平台返回为草稿分支，或者因首次发布/分支状态异常被识别成草稿分支。

无论 AntCode 返回什么，系统的正式发布目标都必须受本系统配置控制：

```text
settings.skill_default_branch = master
```

### 3.4 修复要求

1. `Skill.default_branch` 不得被远端 project metadata 中的 draft branch 覆盖。
2. 系统正式发布分支必须始终取：

```text
settings.skill_default_branch
```

除非后续显式支持“每个 Skill 自定义主分支”，否则不能从 AntCode 返回值自动改写为 draft。

3. `_apply_project_to_skill` 或 `sync_from_remote` 中必须加保护：
   - 如果远端 default_branch 为空，使用 settings 默认值。
   - 如果远端 default_branch 以 `draft/` 开头，忽略并保留 settings 默认值。
   - 如果远端 default_branch 与 settings 默认值不同，需要记录 warning 或 sync diagnostic，不要静默覆盖。
4. `/publish`、`/drafts/diff`、`/repository/sync` 中的正式分支计算必须统一调用一个 helper，例如：

```python
resolve_publish_branch(skill, settings) -> str
```

该 helper 第一阶段必须返回 `settings.skill_default_branch`，并拒绝 draft branch。

5. 已被污染的数据需要在 sync 或 migration/backfill 中自动修复：

```text
if skill.default_branch startswith "draft/":
    skill.default_branch = settings.skill_default_branch
```

### 3.5 验收标准

1. 点击“从远端同步”后，详情页主分支仍为 `master`。
2. 发布确认弹窗主分支仍为 `master`。
3. API `/api/skills/{id}` 返回：

```json
{
  "default_branch": "master"
}
```

4. 若数据库中已有污染值，sync 后自动修复。
5. 新增后端测试覆盖：
   - AntCode project 返回 `default_branch=draft/...` 时，数据库仍保存 `master`。
   - sync 后不会把 default_branch 改成 draft。
   - publish 目标分支不会使用 draft branch。

## 4. P0 问题：版本 diff API 500

### 4.1 现象

版本页有两个版本：

```text
v0.1.0 -> commit b9b322d23, tag v0.1.0
v0.1.1 -> commit 5f15bfc2f, tag v0.1.1
```

打开版本对比页：

```text
/skills/2/diff?from=3&to=4
```

页面只显示两个版本选择框，不显示 diff 文件列表。

直接请求 API：

```text
GET /api/skills/2/diff?from_version_id=3&to_version_id=4
```

返回：

```text
500 Internal Server Error
```

### 4.2 影响

1. 用户无法验证两个正式版本之间的内容差异。
2. 发布前/发布后追溯能力受损。
3. 恢复版本、审计和发布可信度都会下降。
4. 这是 PRD2/PRD5/PRD6 均要求必须可用的核心功能。

### 4.3 可能原因

可能与以下因素有关：

1. `Skill.git_repo_name`、本地 clone 路径和 AntCode workflow 的本地目录命名不一致。
2. `version_service.diff_versions` 仍走旧 `git_service.diff_versions(repo_slug, sha_a, sha_b)`，而 AntCode workflow 使用 `antcode_skill_service.local_repo_path(skill)`。
3. sync 或 publish 后本地仓库当前分支/remote 状态异常。
4. `default_branch` 被污染成 draft branch 后，后续 repo 操作路径或 checkout 状态不一致。

### 4.4 修复要求

1. 版本 diff 必须兼容 AntCode workflow 发布出来的版本。
2. 对已绑定 `git_project_id` 的 Skill，diff 应优先走 AntCode workflow 的本地 clone 路径，而不是旧 `git_service.repo_path_for(repo_slug)`。
3. 后端 diff 失败时不得返回裸 500，应返回结构化错误：

```json
{
  "code": "git_diff_failed",
  "message": "版本 diff 失败: ...可读摘要..."
}
```

4. 修复后 `v0.1.0 -> v0.1.1` 应至少显示：

```text
modified SKILL.md
```

5. 前端 diff 页如果 API 返回错误，应展示明确错误状态，而不是空白页面。

### 4.5 验收标准

1. `GET /api/skills/{id}/diff?from_version_id=...&to_version_id=...` 返回 200。
2. diff 响应包含 `SKILL.md` modified。
3. 前端 diff 页展示新增/修改/删除数量。
4. Monaco diff 区域能展示 `SKILL.md` 内容变化。
5. 新增后端测试覆盖：
   - AntCode workflow 发布两个版本后可 diff。
   - 本地 legacy `/versions` 发布两个版本后仍可 diff。
   - diff repo 缺失或 commit 不存在时返回结构化错误，不返回裸 500。

## 5. P1 问题：Skill 详情页 LLM 写回缺少 patch diff 确认

### 5.1 现象

在 Skill 详情页点击“LLM 辅助更新”：

1. 提交 LLM 任务。
2. 任务成功后弹窗只展示状态和输出摘要。
3. 点击“写回当前 Skill”直接应用 patch。

LLM 任务页已有补丁 diff 预览弹窗，但详情页入口绕过了这个确认流程。

### 5.2 影响

1. LLM 输出可能覆盖 `SKILL.md` 或其它文件，风险较高。
2. 用户无法在写回前确认 patch 内容。
3. 与 PRD2/PRD6 中“LLM 落地前必须展示 diff 并二次确认”的要求不一致。

### 5.3 修复要求

1. Skill 详情页 LLM 更新成功后，不直接显示“写回当前 Skill”。
2. 应先调用：

```text
GET /api/llm/jobs/{job_id}/patch-diff
```

3. 在弹窗内展示 patch diff：
   - 文件列表。
   - change 类型。
   - before/after。
   - tests。
   - risks。
4. 用户点击“确认写回”后才调用 apply。
5. 已落地任务按钮禁用，并显示“已落地”。

### 5.4 验收标准

1. 详情页 LLM 更新成功后能看到 patch 文件列表。
2. 能查看 `SKILL.md` diff。
3. 不确认 diff 无法写回。
4. 写回后不能重复写回。

## 6. P1 问题：代理配置与 AGENTS 要求不一致

### 6.1 现象

设置页显示：

```text
代理未配置
https_proxy: (无)
http_proxy: (无)
all_proxy: (无)
```

但项目 AGENTS 指令要求联网命令默认使用代理：

```bash
export https_proxy=http://127.0.0.1:1235
export http_proxy=http://127.0.0.1:1235
export all_proxy=socks5://127.0.0.1:1234
```

当前测试中 AntCode API 和 LLM API 均能连通，但配置展示与项目运行约束不一致。

### 6.2 修复要求

1. 明确后端服务启动时是否应读取代理环境变量。
2. 如果本地开发必须走代理，则 `scripts/run_backend.sh`、部署文档或 `.env.example` 应体现该配置。
3. 设置页代理状态必须反映后端真实出站行为。
4. AntCode client 和 LLM client 都应使用同一代理解析逻辑。

### 6.3 验收标准

1. 设置页能正确显示代理是否启用。
2. `test-git` 和 `test-llm` 的 detail 中 `proxy_enabled` 与设置页一致。
3. 文档说明本地开发如何启用代理。

## 7. P2 问题：当前版本与 tag 展示重复

### 7.1 现象

Skill 详情页“当前版本”显示类似：

```text
v0.1.1 v0.1.1
```

第一个是产品版本，第二个是 tag，但两个 tag 文案完全相同。

### 7.2 修复要求

1. UI 应区分产品版本与 Git tag。
2. 建议展示为：

```text
当前版本: 0.1.1
Git tag: v0.1.1
```

或在同一个单元格中明确标签：

```text
版本 v0.1.1 / tag v0.1.1
```

### 7.3 验收标准

用户不会看到两个无标签的重复 `v0.1.1`。

## 8. P2 问题：React Router future flag warning

### 8.1 现象

浏览器控制台出现 React Router warning：

```text
React Router Future Flag Warning: React Router will begin wrapping state updates in React.startTransition in v7...
```

### 8.2 影响

这是非阻塞警告，不影响当前业务流程。

### 8.3 建议

可在后续统一升级或开启 future flag 时处理，不作为本轮必须修复项。

## 9. 需要新增或调整的测试

### 9.1 后端测试

必须新增：

1. `sync_from_remote` 不污染 default_branch：
   - 远端 project 返回 `default_branch=draft/...`。
   - 数据库最终仍为 `master`。
2. 已污染数据修复：
   - 初始 `skill.default_branch=draft/...`。
   - 调用 sync 或 helper 后恢复为 `master`。
3. AntCode workflow 两版本 diff：
   - 本地 bare remote。
   - commit draft。
   - publish `0.1.0`。
   - 修改 `SKILL.md`。
   - commit draft。
   - publish `0.1.1`。
   - diff 返回 `modified SKILL.md`。
4. diff 异常结构化：
   - commit 不存在或 repo 缺失时返回业务错误，不返回裸 500。
5. LLM apply 后 patch-diff / apply 幂等：
   - apply 前能获取 diff。
   - apply 后重复 apply 被拒绝。

### 9.2 前端测试或手动验收

必须手动验收：

1. 同步后详情页主分支仍显示 `master`。
2. 发布确认框主分支仍显示 `master`。
3. `v0.1.0 -> v0.1.1` diff 页面展示 `SKILL.md` modified。
4. 详情页 LLM 写回前展示 diff 确认。
5. 当前版本/tag 展示不再重复。

## 10. 验收路径

使用一个新的测试 Skill，完整跑以下流程：

1. 创建 Skill。
2. 创建 AntCode 仓库。
3. 发布 `0.1.0`。
4. 点击“从远端同步”。
5. 确认主分支仍为 `master`。
6. LLM 辅助更新。
7. 查看 patch diff。
8. 确认写回。
9. 发布 `0.1.1`。
10. 确认发布弹窗主分支为 `master`。
11. 版本历史展示两个 tag。
12. 版本 diff 展示 `SKILL.md` 修改。
13. 审计日志中发布记录可点击 commit/tag。
14. 导出 zip 成功。

## 11. 验证命令

后端：

```bash
cd backend
. .venv/bin/activate
pytest -q
```

前端：

```bash
cd frontend
pnpm lint
pnpm build
```

收尾：

```bash
git status --short
git diff --stat
```

## 12. 完成标准

PRD7 完成后必须满足：

1. `default_branch` 永远不会被 draft branch 污染。
2. AntCode workflow 发布出的任意两个版本都可正常 diff。
3. diff API 不再裸 500。
4. Skill 详情页 LLM 写回前必须展示 patch diff。
5. 设置页代理状态与实际 client 行为一致。
6. 当前版本和 tag 展示清晰不重复。
7. 全量后端测试、前端 lint/build 通过。
