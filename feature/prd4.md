# Skill 管理系统 PRD4：全页面验收反馈与发布前收尾需求

版本：v0.1  
日期：2026-05-27  
验收地址：http://localhost:5173/  
验收用户：`bob1`，来自 Cookie 登录态  
依赖文档：[feature/prd1.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd1.md)、[feature/prd2.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd2.md)、[feature/prd3.md](/Users/zhangguangming/Desktop/work/code/skillmng/feature/prd3.md)、[doc/guifan.md](/Users/zhangguangming/Desktop/work/code/skillmng/doc/guifan.md)、[doc/antcode-api-guide.md](/Users/zhangguangming/Desktop/work/code/skillmng/doc/antcode-api-guide.md)

## 1. 验收结论

当前系统的主导航、工作台、Skill 列表、创建 Skill、LLM 任务、审计日志、设置页都已经可访问，整体已经从“页面原型”进入“可试用系统”的状态。最明显的进步是：

1. 左侧菜单可以正常跳转。
2. Skill 列表、LLM 任务、审计日志都有筛选入口。
3. 创建页已经区分“手动创建”和“LLM 辅助”。
4. 设置页已经能读取真实配置，并显示 `LLM_PROVIDER=anthropic`。
5. 设置页已展示 AntCode group、namespace、repo template、SSH key、系统限制、规范校验规则。

但从“给别的系统使用的 Skill 发布平台”角度看，还差最后一层工程闭环：真实 LLM 连接失败要可定位，AntCode/Git 发布链路要可复现、可审计、可恢复，关键操作要有结果页或持久化记录，而不是只靠一次性 toast。

## 2. 本次点击验证范围

已点击和观察：

1. 工作台 `/`
2. Skill 列表 `/skills`
3. 创建 Skill `/skills/new`
4. 创建页“手动创建”tab
5. 创建页“LLM 辅助”tab
6. LLM 任务 `/llm-jobs`
7. 审计日志 `/audit-logs`
8. 设置 `/settings`
9. 设置页“测试 LLM 连接”
10. 设置页“测试 AntCode 连接”

未直接触发的动作：

1. 未创建真实 AntCode 仓库。
2. 未发布真实版本到 master。
3. 未向真实仓库 push draft branch。
4. 未删除 Skill 或远端分支。

原因：这些动作会在真实 `xiaojin-skills` group 产生远端副作用。PRD4 要求后续用隔离测试 Skill 或测试 group 完成端到端验收。

## 3. 当前观察问题

### 3.1 工作台空态还不够能带路

现象：

- `bob1` 当前看到空工作台。
- 页面显示“还没有 Skill,先创建一个”。
- 顶部有“创建 Skill”和“导入 / 导出”入口。

问题：

- 空态只告诉用户没有数据，但没有解释第一条 Skill 应该怎么开始。
- “导入 / 导出”在工作台出现，但当前空态下更准确的是“导入 Skill”。
- 没有显示当前用户隔离范围、数据源状态、真实 Git 配置状态。

要求：

1. 工作台空态增加三个行动入口：
   - 手动创建 Skill。
   - LLM 辅助创建 Skill。
   - 从 zip / Git 导入 Skill。
2. 工作台顶部增加环境健康摘要：
   - 当前用户。
   - LLM provider。
   - AntCode token 是否配置。
   - 代理是否配置。
   - 当前数据库是否为空。
3. 空态文案明确说明：保存草稿先进入 draft branch，发布后合并到 master 并打 tag。

### 3.2 Skill 列表空态缺少下一步

现象：

- Skill 列表表格为空，显示“暂无数据”。
- 页面顶部有搜索、状态筛选、创建、导入入口。

问题：

- 空表格没有行动按钮，用户需要自己找到右上角入口。
- 空态没有说明“列表只显示当前 Cookie 用户的数据”。
- `导入 ▾` 的“绑定 Git remote”项是 disabled，但没有说明为什么 disabled。

要求：

1. Skill 列表空态使用明确的 Empty 区块：
   - 标题：暂无 Skill。
   - 描述：当前用户还没有 Skill，数据按 Cookie 用户隔离。
   - 主按钮：创建 Skill。
   - 次按钮：上传 zip 导入。
2. disabled 菜单项必须给出 tooltip，说明“请先创建或进入某个 Skill 详情后绑定 remote”。
3. 搜索和状态筛选在空数据时仍应显示结果数量，例如 `0 个结果`。

### 3.3 创建 Skill 缺少提交前预览和动作边界

现象：

- 手动创建页已有 name、description、argument-hint、开关、初始正文。
- LLM 辅助页已有目标、使用场景、关键词、目标 Agent、参考材料、约束条件、是否生成 scripts / references。
- 粘贴含 front matter 的正文时，已有拆分提示。

问题：

- 保存前看不到最终生成的 `SKILL.md`。
- 用户不知道“保存草稿”只是写 sqlite，还是会提交到远端 draft branch。
- LLM 辅助提交后没有先展示生成结果预览，成功后才可以落地。
- LLM 创建页没有显示当前 provider、模型、连通性状态。

要求：

1. 手动创建页增加“预览 SKILL.md”区域，展示系统合成后的完整文件。
2. 保存按钮文案根据真实动作拆分：
   - `保存本地草稿`
   - `保存并提交草稿分支`
   - `创建仓库并提交草稿`
3. LLM 辅助页顶部显示：
   - provider。
   - model。
   - 最近一次 LLM 连接测试结果。
4. LLM 任务成功后必须先展示：
   - 生成文件列表。
   - `SKILL.md` 预览。
   - 校验结果。
   - 风险和测试建议。
5. 只有用户确认后，才允许“落地为 Skill 草稿”。

### 3.4 LLM 真实连接失败需要可诊断

现象：

- 设置页显示 `Provider=anthropic`、`Model=claude-opus-4-6`、Token 已配置。
- 点击“测试 LLM 连接”后返回：`LLM API: 无效的api key`。

问题：

- 这是当前最关键的阻断问题。系统已经切到真实 LLM，但 token 或请求头/路径/API 风格不匹配。
- 目前只有 toast，用户错过后无法复查。
- 错误没有显示请求目标路径、API style、HTTP status、是否使用代理。

要求：

1. 设置页新增“最近一次连接测试结果”面板，至少展示：
   - 测试时间。
   - provider。
   - model。
   - API style：Anthropic messages / OpenAI compatible。
   - base URL。
   - 实际请求路径，不能展示 token。
   - HTTP status。
   - 错误摘要。
   - 是否走代理。
2. LLM 连接测试写入审计日志，action 为 `settings.llm.test`。
3. 后端支持可配置 API style：
   - `LLM_API_STYLE=anthropic`
   - `LLM_API_STYLE=openai-compatible`
   - `LLM_API_STYLE=auto`
4. 对当前内部网关 `https://idealab.alibaba-inc.com/api/anthropic`，必须通过一次真实调试确认正确 endpoint 和认证 header。
5. 真实 LLM 未连通时：
   - 创建页 LLM tab 不禁用，但提交前要明确提示“真实 LLM 当前不可用”。
   - LLM 任务失败状态必须展示完整可读错误。

### 3.5 AntCode 连接测试缺少可复查结果

现象：

- 设置页显示 AntCode token 已配置、group URL、namespace、repo template。
- 点击“测试 AntCode 连接”后按钮进入 loading，但页面没有保留可复查结果。

问题：

- 用户无法判断 AntCode 是成功、失败、超时，还是 toast 消失了。
- 代理显示为空，与项目 AGENTS 中“联网命令默认使用代理”的要求不一致。

要求：

1. 设置页新增“最近一次 AntCode 测试结果”面板，展示：
   - 测试时间。
   - group id / group path。
   - 当前 token 对应 username。
   - HTTP status。
   - 是否使用代理。
   - 错误摘要。
2. AntCode 测试写入审计日志，action 为 `settings.antcode.test`。
3. 后端 `httpx` 出站请求必须读取 `.env` 或运行环境中的代理配置：
   - `https_proxy`
   - `http_proxy`
   - `all_proxy`
4. 设置页代理为空时给出 warning：当前后端进程没有代理配置，内网接口可能失败。

### 3.6 设置页 token 掩码还可以更保守

现象：

- AntCode token 显示为“已配置”并展示部分掩码。
- LLM token 只显示“已配置”。

建议：

1. 第一阶段设置页只展示“已配置 / 未配置”，不展示 token 前后缀。
2. 如果确实需要区分 token，展示 hash 后 6 位，而不是原 token 前后缀。
3. 所有错误日志和审计日志都不得包含 token、Cookie、Authorization header。

### 3.7 LLM 任务页空态已改善，但需要任务级证据

现象：

- LLM 任务空态已经有去创建页和 Skill 详情页的引导。
- 有状态、类型、Skill ID 筛选。

要求：

1. 任务列表增加列：
   - provider。
   - model。
   - token 用量或耗时。
   - 失败错误摘要。
2. 任务详情增加：
   - 原始输入摘要。
   - 生成文件 diff。
   - 校验结果。
   - tests / risks。
   - apply 前后的 draft commit。
3. 落地 LLM 结果时必须自动提交 draft branch，失败时要让任务处于 `succeeded_not_applied` 或类似状态，避免“生成成功但落地失败”混在一起。

### 3.8 审计日志空态和语义需要补齐

现象：

- 审计日志页面可打开，有 action 和 Skill ID 搜索。
- 当前用户无数据时显示“暂无数据”。

要求：

1. 空态说明“只显示当前用户的操作记录”。
2. 审计日志必须覆盖以下动作：
   - `skill.create`
   - `skill.file.write`
   - `skill.draft.commit`
   - `skill.repository.create`
   - `skill.repository.sync`
   - `skill.version.publish`
   - `skill.version.restore`
   - `llm.job.create`
   - `llm.job.apply`
   - `settings.llm.test`
   - `settings.antcode.test`
3. 每条审计日志必须能跳转到相关对象：
   - Skill。
   - Version。
   - LLM Job。
   - Git commit。
4. Git commit 链接应该跳到 AntCode commit 页面，而不是只显示短 SHA。

### 3.9 发布链路还需要端到端验收页

PRD3 已要求发布闭环，本次验收因真实远端副作用未直接触发。PRD4 要求新增一个“发布前检查”流程，避免用户误点发布后才发现问题。

发布前检查必须包含：

1. Skill 规范校验通过。
2. AntCode 仓库已创建。
3. draft branch 存在。
4. draft commit 存在。
5. draft 与 master 有差异。
6. 版本号格式正确。
7. 远端 tag `v{version}` 不存在。
8. 当前用户有 push master 和 create tag 权限。
9. 发布摘要不为空。

发布确认页必须展示：

1. 将要发布的 repo。
2. draft branch。
3. draft commit。
4. master 当前 commit。
5. 将创建的版本号和 tag。
6. diff 统计。
7. 发布后是否删除 draft branch。

### 3.10 本地内容缓存策略需要更明确

用户要求“本地不应该保留 Skill 的内容，每次提交都是 git 仓库的一个 commit”。当前系统仍有 sqlite 文件树作为编辑态缓存。

要求：

1. 明确 sqlite 文件树只是编辑缓存，不是内容真源。
2. 每次保存草稿成功后，必须产生远端 draft commit。
3. 页面应显示缓存状态：
   - `未提交`
   - `已提交 draft`
   - `已发布 master`
4. 系统启动后如果发现 sqlite 文件树和远端 draft/master 不一致，应提示用户选择：
   - 以远端覆盖本地缓存。
   - 将本地缓存提交为新 draft commit。
5. 发布成功后，sqlite 内容必须能从 master/tag 重新拉取恢复。

## 4. 页面级收尾需求

### 4.1 工作台

新增：

1. 环境健康卡片。
2. 最近一次 LLM / AntCode 测试状态。
3. 未发布草稿列表。
4. 最近发布版本列表。
5. 空态行动按钮。

验收：

1. 新用户首次进入能在 3 次点击内创建第一个 Skill。
2. 有数据用户能看到草稿、发布、失败任务、审计摘要。

### 4.2 Skill 列表

新增：

1. 空态行动按钮。
2. Git 状态更细：
   - 未绑定。
   - 仓库已创建。
   - 有未提交修改。
   - 有 draft commit。
   - 已发布。
3. 当前版本显示 `v0.1.2` 和 tag。
4. 支持按 Git 状态筛选。

验收：

1. 发布成功后列表当前版本不允许显示 `-`。
2. draft commit 存在时必须显示“有草稿”。
3. published commit 存在时必须显示短 SHA 或可点击 commit。

### 4.3 创建 Skill

新增：

1. 最终 `SKILL.md` 预览。
2. 创建前规范校验。
3. 创建后是否立即创建 AntCode 仓库的选项。
4. 创建后是否立即提交 draft branch 的选项。
5. LLM 生成结果确认页。

验收：

1. 粘贴完整 `SKILL.md` 不会产生双 front matter。
2. 创建成功后至少生成一个合法 `SKILL.md`。
3. 开启“提交 draft branch”后，详情页能看到 draft branch 和 commit。

### 4.4 Skill 详情 / 编辑

新增：

1. 文件保存后的“提交草稿”结果展示。
2. draft vs master diff 入口。
3. 发布前检查。
4. LLM 更新结果 diff preview。
5. 远端同步冲突提示。

验收：

1. 编辑 `SKILL.md` 后保存，状态变为未发布草稿。
2. 提交草稿后产生 `draft/{user_id}/{skill_name}` commit。
3. 发布后当前版本、tag、published commit 同步更新。

### 4.5 版本历史 / Diff

新增：

1. Tag 列必须有值。
2. Commit 可点击跳转 AntCode。
3. 支持按 tag / version / commit 搜索。
4. Diff 页面显示比较方向、文件列表、增删行数。

验收：

1. 发布版本 `0.1.2` 后必须出现 tag `v0.1.2`。
2. 已存在 tag 再发布相同版本必须失败。
3. restore 操作必须产生新的 draft commit 或明确的恢复版本记录。

### 4.6 LLM 任务

新增：

1. provider / model / duration 列。
2. 错误详情 drawer。
3. 生成内容预览。
4. apply 前 diff。
5. apply 后 draft commit。

验收：

1. 真实 LLM token 无效时任务进入 failed，并显示“无效 api key”类错误。
2. 修复 token 后，同一个输入能成功生成 JSON 并通过规范校验。
3. apply 后能在 Skill 详情看到文件变化和 draft commit。

### 4.7 审计日志

新增：

1. 动作中文映射完整。
2. Git commit 链接。
3. 连接测试类审计。
4. 导出审计日志。

验收：

1. 每个关键动作都有一条审计记录。
2. 审计日志不泄露 token。
3. 多租户隔离：`bob1` 看不到其他用户审计。

### 4.8 设置

新增：

1. 最近一次测试结果面板。
2. 代理缺失 warning。
3. API style 显示与配置。
4. Token 仅显示配置状态。
5. “复制诊断信息”按钮，自动脱敏。

验收：

1. LLM 测试失败时页面保留失败原因。
2. AntCode 测试成功时显示 username 和 group path。
3. 刷新配置后 provider / proxy / token 状态立即更新。

## 5. API 与数据一致性要求

### 5.1 Skill 聚合字段

`GET /api/skills` 和 `GET /api/skills/{id}` 必须稳定返回：

```json
{
  "current_version": "0.1.2",
  "current_version_id": 3,
  "published_commit_sha": "abcdef...",
  "published_tag": "v0.1.2",
  "draft_branch": "draft/bob1/my-skill",
  "draft_commit_sha": "123456..."
}
```

### 5.2 发布事务

发布必须作为一个业务事务处理：

1. 校验版本号。
2. 校验 tag 不存在。
3. 合并 draft 到 master。
4. push master。
5. 创建并 push tag。
6. 写 `skill_versions`。
7. 更新 `skills.current_version_id/current_version/published_commit_sha`。
8. 写审计日志。

如果第 3 到第 5 步失败，数据库不得误标记为发布成功。

### 5.3 连接测试结果

建议新增表 `connection_test_results` 或复用审计日志 detail 字段，保存脱敏后的测试结果：

```json
{
  "target": "llm",
  "ok": false,
  "provider": "anthropic",
  "model": "claude-opus-4-6",
  "api_style": "anthropic",
  "base_url": "https://idealab.alibaba-inc.com/api/anthropic",
  "status_code": 401,
  "message": "LLM API: 无效的api key",
  "proxy_enabled": false,
  "tested_at": "2026-05-27T12:00:00+08:00"
}
```

## 6. 真实 LLM 修复要求

当前真实 LLM 测试失败，必须优先修复。建议执行顺序：

1. 用后端配置读取当前 `ANTHROPIC_BASE_URL`、model、token 配置状态，不打印 token。
2. 确认内部网关需要的认证 header：
   - `x-api-key`
   - `Authorization: Bearer`
   - 或其他公司网关约定。
3. 确认真实 endpoint：
   - `{base}/v1/messages`
   - `{base}/messages`
   - `{base}/chat/completions`
   - 或内部文档指定路径。
4. 将 API style 做成 `.env` 配置，不要硬编码猜测。
5. LLM 失败时把 HTTP status 和脱敏响应摘要写入任务错误。

验收标准：

1. 设置页“测试 LLM 连接”成功。
2. 创建页 LLM 辅助生成一个 Skill 草稿。
3. LLM 任务详情展示生成文件、tests、risks。
4. 生成的 `SKILL.md` 通过规范校验。
5. 全链路不泄露 token。

## 7. AntCode / Git 端到端验收要求

需要准备一个测试 Skill，例如 `codex-e2e-smoke-skill`，在真实或隔离 group 内跑通：

1. 创建 Skill。
2. 创建 AntCode 仓库。
3. 保存草稿。
4. 产生 `draft/{user_id}/{skill_name}` 分支。
5. 编辑 `SKILL.md`。
6. 再次提交 draft commit。
7. 查看 draft vs master diff。
8. 发布 `0.1.0`。
9. master 出现发布 commit。
10. tag 出现 `v0.1.0`。
11. Skill 列表和详情显示当前版本。
12. 版本历史显示 tag 和 commit。
13. 审计日志记录完整链路。
14. 删除本地缓存后从远端 sync 能恢复文件树。

验收通过后，删除测试仓库或标记为测试用途。

## 8. 优先级

P0：

1. 修复真实 LLM 连接失败或明确支持当前内部网关 API style。
2. 设置页连接测试结果持久展示。
3. AntCode/Git 发布链路端到端验收。
4. 发布前检查。
5. 防止 token 泄露。

P1：

1. 创建页最终 `SKILL.md` 预览。
2. LLM 生成结果预览和 apply 前 diff。
3. 工作台 / Skill 列表空态增强。
4. 审计日志补齐连接测试、draft commit、publish。
5. 代理配置检测与 warning。

P2：

1. 审计导出。
2. Git 状态筛选。
3. 版本历史搜索。
4. 设置页复制脱敏诊断信息。

## 9. Agent 执行建议

建议按以下顺序开发：

1. 先做设置页诊断闭环：连接测试结果面板、审计日志、代理 warning。
2. 修复 LLM API style，让“测试 LLM 连接”成功。
3. 补创建页预览和 LLM 结果确认页。
4. 用测试 Skill 跑通 AntCode：create repo、draft commit、publish、tag。
5. 补发布前检查和发布确认页。
6. 回填工作台、列表、详情、版本历史中的聚合字段展示。
7. 最后补空态、筛选、导出等体验项。

完成后请提供一份验收记录，至少包含：

1. 测试用户。
2. 测试 Skill 名称。
3. AntCode 仓库 URL。
4. draft branch。
5. draft commit。
6. master commit。
7. tag。
8. LLM 任务 ID。
9. 审计日志截图或记录 ID。
10. 所有敏感信息已脱敏的说明。
