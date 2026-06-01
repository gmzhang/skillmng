# Skill 管理系统 PRD8：PRD7 修复复验与体验收口

版本：v0.1  
日期：2026-05-29  
验收地址：http://localhost:5173/  
验收用户：`skillmng`，来自 Cookie 登录态  
依赖文档：
- [feature/prd6.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd6.md)
- [feature/prd7.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd7.md)
- [CODEX_HANDOFF.md](/Users/zhangguangming/Desktop/work/code/skillmng/CODEX_HANDOFF.md)
- [doc/guifan.md](/Users/zhangguangming/Desktop/work/code/skillmng/doc/guifan.md)

## 1. 背景

PRD7 的实现改动完成后，对本地真实页面 `http://localhost:5173/` 重新做了一轮端到端复验。

本轮测试新建 Skill：

```text
codex-retest-195494
```

对应 AntCode 仓库：

```text
xiaojin-skills/codex-retest-195494
```

本轮复验覆盖：

1. 创建 Skill。
2. 创建 AntCode 仓库。
3. 首次发布 `v0.1.0`。
4. 远端同步。
5. LLM 辅助更新。
6. 查看 LLM 变更并确认写回。
7. 二次发布 `v0.1.1`。
8. 版本历史。
9. 版本 diff 页面与 diff API。
10. 设置页 AntCode / LLM 连接测试。
11. 审计日志。
12. 前端构建与后端关键测试。

整体结论：

1. PRD7 中两个 P0 问题已复验通过。
2. 主发布链路已可用。
3. 仍有两个体验层 P1/P2 收口项，建议进入本轮 PRD8 修复。
4. 本系统是内网应用，不再要求代理配置，也不再把“代理未配置”视为问题。

## 2. PRD7 P0 复验结论

### 2.1 P0：同步后 default_branch 被污染为 draft 分支

复验结论：已通过。

本轮操作：

1. 创建 Skill `codex-retest-195494`。
2. 创建仓库 `xiaojin-skills/codex-retest-195494`。
3. 发布 `v0.1.0`。
4. 点击“从远端同步”。
5. 检查详情页与 API 状态。

页面结果：

```text
主分支: master
草稿分支: draft/skillmng/codex-retest-195494
当前版本: v0.1.0
Git tag: v0.1.0
```

API 抽检：

```json
{
  "id": 2,
  "name": "codex-retest-195494",
  "status": "published",
  "current_version": "0.1.1",
  "published_commit_sha": "e3ac2ff02288fd9a2891ef2e7d3920eba3355daf",
  "published_tag": "v0.1.1",
  "default_branch": "master",
  "draft_branch": "draft/skillmng/codex-retest-195494",
  "draft_commit_sha": "afe9ac0d1ed7a89e34b3adc177dccedfb54f1592"
}
```

验收判断：

1. `default_branch` 未再被改成 `draft/...`。
2. 二次发布预览中“主分支”仍显示 `master`。
3. 发布、同步、diff 均继续基于正式分支语义运行。

### 2.2 P0：版本 diff API 返回 500

复验结论：已通过。

版本数据：

```text
v0.1.0 commit: 8c6899177f1257e0582d0c54941f5d8212ff239c
v0.1.1 commit: e3ac2ff02288fd9a2891ef2e7d3920eba3355daf
```

API 抽检：

```text
GET /api/skills/2/diff?from_version_id=3&to_version_id=4
status: 200
```

返回内容包含：

```text
files[0].path = SKILL.md
files[0].change = modified
```

页面结果：

1. 版本对比页正常打开。
2. 标题显示“版本对比 从 v0.1.0 到 v0.1.1”。
3. 统计显示：

```text
新增 0
修改 1
删除 0
```

4. 文件显示：

```text
modified SKILL.md
```

5. 左右 diff 正常展示 `SKILL.md` 变更。

验收判断：

1. 原 500 问题未复现。
2. 页面不再空白。
3. API 与 UI 行为一致。

## 3. 本轮完整流程记录

### 3.1 创建与建仓

测试 Skill：

```text
codex-retest-195494
```

描述：

```text
用于复测 PRD7 修复后的 Skill 管理系统端到端流程。关键词: codex retest publish diff sync audit。
```

创建结果：

1. 保存本地草稿成功。
2. 详情页正常显示文件树与 `SKILL.md`。
3. 点击“在 AntCode 创建仓库”成功。
4. 仓库显示为：

```text
xiaojin-skills/codex-retest-195494
```

### 3.2 首次发布 v0.1.0

发布参数：

```text
version: 0.1.0
change_type: patch
summary: 首次端到端复测发布
```

结果：

```text
tag: v0.1.0
commit: 8c6899177f1257e0582d0c54941f5d8212ff239c
```

发布后详情页：

```text
status: published
当前版本: v0.1.0
Git tag: v0.1.0
主分支: master
草稿分支: draft/skillmng/codex-retest-195494
最新发布 commit: 8c6899177
```

### 3.3 远端同步

点击“从远端同步”后：

```text
主分支: master
当前版本: v0.1.0
Git tag: v0.1.0
```

结论：

1. 同步成功。
2. `default_branch` 未污染。

### 3.4 LLM 辅助更新

LLM 更新目标：

```text
补充一个“复测检查清单”小节，包含创建、仓库、同步、发布、版本 diff、审计六个检查点。
```

任务结果：

```text
job_id: 1
status: succeeded
summary: 在 SKILL.md 中添加了“复测检查清单”小节，包含创建、仓库、同步、发布、版本 diff、审计六个检查点。
```

页面行为：

1. 任务成功后出现“查看变更 diff”。
2. 点击后显示“变更文件 (1)”。
3. 文件显示：

```text
modified SKILL.md
```

4. 点击“确认写回”后，`SKILL.md` 增加“复测检查清单”小节。
5. 草稿 SHA 更新为：

```text
afe9ac0d1ed7a89e34b3adc177dccedfb54f1592
```

### 3.5 二次发布 v0.1.1

发布参数：

```text
version: 0.1.1
change_type: patch
summary: LLM 补充复测检查清单
```

发布预览：

```text
目标仓库: xiaojin-skills/codex-retest-195494
主分支: master
草稿分支: draft/skillmng/codex-retest-195494
草稿 SHA: afe9ac0d1
发布版本: v0.1.1
预计 Tag: v0.1.1
变更文件 (1): modified SKILL.md
```

发布结果：

```text
tag: v0.1.1
commit: e3ac2ff02288fd9a2891ef2e7d3920eba3355daf
```

详情页结果：

```text
status: published
当前版本: v0.1.1
Git tag: v0.1.1
主分支: master
最新发布 commit: e3ac2ff02
```

### 3.6 版本历史

版本页展示：

```text
0.1.1 patch LLM 补充复测检查清单 e3ac2ff02 v0.1.1
0.1.0 patch 首次端到端复测发布 8c6899177 v0.1.0
```

验收结果：

1. commit 链接存在。
2. tag 链接存在。
3. 版本顺序正确。
4. 两个版本可选中对比。

### 3.7 审计日志

审计日志已记录：

```text
创建 Skill
创建 Git 仓库
提交草稿到分支
发布版本 v0.1.0
同步 Git 仓库
提交 LLM 更新任务
落地 LLM 更新补丁
提交草稿到分支
发布版本 v0.1.1
测试 AntCode 连接
测试 LLM 连接
```

验收结果：

1. 关键操作都有审计记录。
2. 发布记录带 commit 与 tag。
3. 草稿提交记录带 draft branch 与 SHA。

## 4. 不再处理项：代理配置

本系统是内网应用，不需要代理。

因此，下列现象不再作为问题处理：

```text
设置页显示: 代理未配置
AntCode 测试 detail: 代理 未启用
LLM 测试 detail: 代理 未启用
```

实现 Agent 不需要再改代理相关逻辑，除非后续单独提出新需求。

注意：

1. 不要为了 PRD8 修改 `settings_api.py` 的代理展示。
2. 不要新增代理配置项。
3. 不要把代理未启用作为健康检查失败条件。
4. 不要修改 AGENTS.md；它只描述命令习惯，不构成本轮产品需求。

## 5. PRD8 需求范围

本轮只做体验收口，不再重构发布主链路。

### 5.1 P1：LLM 写回确认需要显示行级 diff

当前状态：

1. Skill 详情页 LLM 任务完成后，已经出现“查看变更 diff”。
2. 点击后展示：

```text
变更文件 (1)
modified SKILL.md
确认写回
```

问题：

1. 当前确认前主要看到的是文件级列表。
2. 用户无法在同一弹窗中逐行检查实际变更内容。
3. 这仍然弱于版本 diff 页的可审查能力。

目标：

LLM 写回前必须显示行级 diff，让用户确认具体内容后再写回。

需求：

1. Skill 详情页的 LLM 更新弹窗，在任务 succeeded 后点击“查看变更 diff”，应展示每个 changed file 的行级 before/after 对比。
2. 展示形式可复用版本 diff 页现有组件或抽取共享 DiffViewer。
3. 至少支持：
   - modified 文件。
   - added 文件。
   - deleted 文件。
4. 每个文件必须展示：
   - change 类型。
   - path。
   - before 内容。
   - after 内容。
5. “确认写回”按钮必须位于 diff 内容之后或 diff 区域附近，避免用户未看到内容就确认。
6. 如果 diff 内容过长，使用可滚动区域，不要撑破弹窗。
7. 如果 diff 计算失败，禁止确认写回，并显示可理解错误。
8. 不改变后端 LLM 任务的提交、执行和 apply API 语义，除非现有接口无法提供 before/after。

验收标准：

1. LLM 任务成功后，点击“查看变更 diff”能看到 `SKILL.md` 的实际新增行。
2. 用户能在确认写回前看到新增小节内容。
3. 点击“确认写回”后，文件内容落地，草稿 commit 更新。
4. 审计日志仍记录 `llm.update.apply`。

建议实现：

1. 优先复用 `SkillDiff.tsx` 中成熟的 diff 渲染逻辑。
2. 如有重复，可抽出 `components/FileDiffViewer.tsx`。
3. 前端类型与 API 返回保持兼容，避免为了展示 diff 改动过多后端逻辑。

### 5.2 P2：首次发布预览文案优化

当前状态：

首次发布 `v0.1.0` 时，发布确认弹窗显示：

```text
变更文件 (0)
无变更文件
```

问题：

1. 对空仓库首次发布来说，这在技术上可以理解。
2. 但对用户来说，“首次发布”却显示“无变更文件”，容易误解为没有内容会被发布。

目标：

首次发布到空 `master` 时，预览文案应明确这是初始化发布。

需求：

1. 当目标主分支不存在，或当前没有可对比的 `origin/master`，但草稿分支有内容时，不显示“无变更文件”作为唯一信息。
2. 应显示更清晰的提示，例如：

```text
首次发布：将创建 master 分支并发布当前 Skill 内容。
```

或：

```text
首次发布：目标主分支暂无历史，将以草稿内容初始化正式版本。
```

3. 如果能计算首发文件列表，可以显示 added 文件；如果暂不计算，至少必须显示“首次发布”提示。
4. 二次及后续发布仍显示真实变更文件列表。

验收标准：

1. 新 Skill 首次发布预览不再只显示“变更文件 (0) / 无变更文件”。
2. 用户能明确知道这是首发初始化。
3. 二次发布仍显示 `modified SKILL.md` 等真实差异。

建议实现：

1. 后端 publish preview 返回 `is_initial_publish` 或类似字段。
2. 前端根据该字段显示首发文案。
3. 如当前 preview 响应已能从 `files.length === 0` 与 `published_commit_sha == null` 推断，也可以先在前端最小实现，但推荐后端给显式字段。

## 6. 不允许做的事

1. 不要重写 AntCode 发布主流程。
2. 不要改动已经通过的 `default_branch` 修复逻辑，除非测试证明必须调整。
3. 不要恢复旧的本地-only publish 路径作为正式发布入口。
4. 不要把代理未配置作为错误。
5. 不要删除或回滚现有用户数据。
6. 不要修改 `.env`、`.env.local` 或输出任何 token。
7. 不要删除用户或其他 Agent 已经产生的未提交改动。

## 7. 测试要求

### 7.1 后端测试

在后端虚拟环境中执行：

```bash
cd backend
. .venv/bin/activate
pytest tests/test_prd7.py tests/test_publish_workflow.py tests/test_versions_git_mock.py
```

本轮复验基线：

```text
21 passed in 39.91s
```

如果新增后端逻辑，例如 `is_initial_publish` 字段，需要补充对应测试。

建议新增测试：

1. publish preview 在首次发布时返回 `is_initial_publish=true`。
2. publish preview 在二次发布时返回 `is_initial_publish=false` 且返回真实 diff 文件。
3. LLM diff 展示所需接口返回 before/after 内容。

### 7.2 前端测试

执行：

```bash
pnpm -C frontend build
```

本轮复验基线：

```text
build success
```

允许存在 Vite chunk size warning，不作为本轮失败条件。

如果抽取 diff 组件，需要确保：

1. SkillDiff 页面仍正常显示版本 diff。
2. SkillDetail 的 LLM 弹窗能显示行级 diff。
3. TypeScript build 通过。

### 7.3 浏览器验收路径

在 `http://localhost:5173/` 使用用户 `skillmng` 验收：

1. 新建一个 Skill。
2. 创建 AntCode 仓库。
3. 打开发布弹窗，预览首次发布。
4. 确认首次发布预览出现“首次发布/初始化正式版本”类提示。
5. 发布 `v0.1.0`。
6. 提交 LLM 辅助更新。
7. 等待任务 succeeded。
8. 点击“查看变更 diff”。
9. 确认弹窗中能看到实际新增行。
10. 点击“确认写回”。
11. 发布 `v0.1.1`。
12. 打开版本页，对比 `v0.1.0 -> v0.1.1`。
13. 确认版本 diff 页面仍正常。
14. 打开审计日志，确认 LLM apply 和发布记录存在。

## 8. 验收通过标准

PRD8 完成后必须满足：

1. PRD7 两个 P0 不回归：
   - `default_branch` 同步后仍为 `master`。
   - 版本 diff API 返回 200。
2. LLM 写回前能看到行级 diff。
3. LLM 写回后草稿 commit 更新，审计日志记录 apply。
4. 首次发布预览不再让用户误解为“没有内容会发布”。
5. 二次发布预览仍显示真实变更文件。
6. 前端 build 通过。
7. 后端关键测试通过。
8. 不引入代理相关需求。

## 9. 给实现 Agent 的执行提示词

```text
你是 skillmng 项目的实现 Agent。请先仔细阅读 CODEX_HANDOFF.md、feature/prd6.md、feature/prd7.md、feature/prd8.md，然后严格按 feature/prd8.md 执行。

重要约束：
1. 本轮只做 PRD8 的体验收口，不要重写 AntCode 发布主流程。
2. PRD7 的两个 P0 已通过复验：default_branch 不再污染，版本 diff API 已返回 200。实现时必须保证不回归。
3. 这是内网应用，不需要代理；不要修改代理逻辑，不要把“代理未配置”当成问题。
4. 不要修改 .env / .env.local，不要输出任何 token。
5. 不要删除或回滚用户/其他 Agent 的未提交改动。

本轮必须完成：
1. Skill 详情页 LLM 写回确认前显示行级 diff。
   - 用户点击“查看变更 diff”后，必须看到每个文件的 change、path、before、after。
   - 优先复用或抽取版本 diff 页已有渲染逻辑。
   - diff 失败时禁止确认写回，并显示清晰错误。
2. 首次发布预览文案优化。
   - 首发到空 master 时，不要只显示“变更文件 (0) / 无变更文件”。
   - 显示“首次发布：将创建 master 分支并发布当前 Skill 内容”或同等清晰文案。
   - 二次发布仍显示真实变更文件列表。

完成后请执行并汇报：
1. cd backend && . .venv/bin/activate && pytest tests/test_prd7.py tests/test_publish_workflow.py tests/test_versions_git_mock.py
2. pnpm -C frontend build
3. 浏览器端到端验收：
   - 新建 Skill
   - 首次发布预览确认有首发初始化提示
   - 发布 v0.1.0
   - LLM 辅助更新
   - 查看 LLM 行级 diff
   - 确认写回
   - 发布 v0.1.1
   - 版本对比页确认仍正常
   - 审计日志确认记录存在

只实现 feature/prd8.md 范围内的需求。遇到与 PRD8 无关的问题，记录但不要扩大修改范围。
```
