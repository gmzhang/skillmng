
SKILL.md 是 Skill 的核心文件，定义了 Skill 的名称、描述和具体指令。本规范遵循 [Agent Skills](https://agentskills.io/) 开放标准。

---

## 文件结构
一个标准的 SKILL.md 文件包含两部分：

```markdown
---
name: skill-name
description: Skill 的功能描述
---

# Skill 标题

这里是 Skill 的详细指令内容...
```

**结构说明：**

+ **Frontmatter**：位于文件开头的 YAML 格式元数据，用 `---` 包裹
+ **指令内容**：Markdown 格式的详细指令

---

## Frontmatter 字段
### 必填字段
| 字段 | 类型 | 说明 | 示例 |
| --- | --- | --- | --- |
| `name` | string | Skill 名称，作为 `/skill-name` 调用命令 | `code-review` |
| `description` | string | 功能描述，AI 根据此判断何时自动加载 | `审查代码中的 bug、安全问题和风格问题` |


### 可选字段
| 字段 | 类型 | 说明 | 示例 |
| --- | --- | --- | --- |
| `argument-hint` | string | 参数提示，显示在命令补全中 | `[filename]` |
| `disable-model-invocation` | boolean | 禁止 AI 自动调用，仅支持手动触发 | `true` |
| `user-invocable` | boolean | 是否在 `/` 菜单中显示 | `false` |


---

## 字段详细说明
### name
Skill 的调用名称，用户通过 `/name` 命令触发。

**规则：**

+ 只能包含小写字母、数字、连字符
+ 最长 64 个字符
+ 建议使用能体现功能的简洁名称

```yaml
# 好的示例
name: code-review
name: api-docs-generator
name: fix-issue

# 不好的示例
name: Code_Review    # 包含大写和下划线
name: tool           # 过于笼统
```

### description
**最重要的字段**，决定了 AI 何时自动加载此 Skill。

**编写公式：功能说明 + 使用场景 + 关键词**

```yaml
# ❌ 不好的示例：过于笼统
description: 代码工具

# ❌ 不好的示例：没有说明使用场景
description: 代码审查

# ✅ 好的示例：功能明确、场景清晰
description: 审查代码中的 bug、安全问题和风格问题。当用户请求代码审查、检查 PR 或查看代码质量时使用。
```

**多语言支持：**

```yaml
description: Review code for bugs, security issues, and style violations. 审查代码中的 bug、安全问题和风格问题。Use when reviewing pull requests or checking code quality.
```

### argument-hint
提示用户如何传入参数。

```yaml
---
name: fix-issue
description: 修复 GitHub Issue
argument-hint: [issue-number]
---
```

用户看到：`/fix-issue [issue-number]`

### disable-model-invocation
某些 Skill 只适合手动触发（如部署命令），可以禁止自动触发：

```yaml
---
name: deploy
description: 部署应用到生产环境
disable-model-invocation: true
---
```

---

## 指令内容编写规范
### 推荐结构
```markdown
# Skill 标题

简要说明 Skill 的功能和用途。

## 任务说明

明确说明 Skill 要完成的任务。

## 执行步骤

1. 第一步操作
2. 第二步操作
3. ...

## 输出格式

规定输出的格式和结构。

## 示例

提供输出示例。
```

### 编写技巧
| 技巧 | 说明 |
| --- | --- |
| **明确目标** | 清晰说明 Skill 要达成什么目的 |
| **步骤化** | 将复杂任务分解为具体步骤 |
| **结构化输出** | 使用表格、列表规定输出格式 |
| **提供示例** | 给出期望输出的示例 |
| **标注限制** | 说明使用边界和注意事项 |


### 输出格式定义
清晰的输出结构有助于用户理解结果：

```markdown
## 输出格式

| 字段 | 说明 |
| --- | --- |
| 问题等级 | 🔴 严重 / 🟡 中等 / 🟢 建议 |
| 位置 | 文件名:行号 |
| 描述 | 问题说明 |
| 建议 | 修复建议 |
```

### 提供示例
```markdown
## 示例输出

### 示例 1：安全问题

🔴 严重 - auth.ts:42
- 问题：密码明文存储
- 建议：使用 bcrypt 加密后再存储

### 示例 2：风格问题

🟢 建议 - utils.ts:15
- 问题：函数命名不规范
- 建议：使用 camelCase 命名风格
```

---

## 参数传递
### 使用 $ARGUMENTS
接收用户传入的完整参数：

```markdown
---
name: fix-issue
description: 修复 GitHub Issue
---

修复 GitHub Issue $ARGUMENTS。
```

调用：`/fix-issue 123`

AI 接收到：`修复 GitHub Issue 123。`

### 按位置访问参数
使用 `$0`、`$1`、`$2` 等访问按空格分割的参数：

```markdown
---
name: migrate
description: 迁移组件
---

将 $0 组件从 $1 迁移到 $2。
```

调用：`/migrate SearchBar React Vue`

AI 接收到：`将 SearchBar 组件从 React 迁移到 Vue。`

### 参数默认值处理
在指令中处理参数为空的情况：

```markdown
修复 GitHub Issue $ARGUMENTS。

如果未指定 Issue 编号，先询问用户要修复哪个 Issue。
```

---

## 引用外部文件
Skill 可以引用同目录下的其他文件：

```markdown
---
name: api-docs
description: API 文档生成
---

根据 [templates/api-template.md](templates/api-template.md) 格式生成文档。
```

**目录结构：**

```plain
my-skill/
├── SKILL.md
└── templates/
    └── api-template.md
```

---

## 完整示例
```markdown
---
name: code-review
description: 审查代码中的 bug、安全问题和风格问题。当用户请求代码审查、检查 PR 或查看代码质量时使用。
argument-hint: [file-path]
---

# 代码审查

对提供的代码进行全面审查，输出结构化的问题报告。

## 审查维度

1. **正确性**：逻辑是否正确，边界条件是否处理
2. **安全性**：是否存在注入、XSS 等安全风险
3. **可读性**：命名是否清晰，注释是否充分
4. **性能**：是否存在明显的性能问题

## 执行步骤

1. 读取待审查的代码文件
2. 按审查维度逐一检查
3. 记录发现的问题
4. 按格式输出报告

## 输出格式

| 等级 | 位置 | 问题 | 建议 |
| --- | --- | --- | --- |
| 🔴 严重 | file:line | 问题描述 | 修复建议 |
| 🟡 中等 | file:line | 问题描述 | 修复建议 |
| 🟢 建议 | file:line | 问题描述 | 修复建议 |

## 示例输出

🔴 严重 - auth.ts:42
- 问题：密码明文存储
- 建议：使用 bcrypt 加密后再存储

🟡 中等 - user.ts:88
- 问题：缺少输入验证
- 建议：添加 email 格式校验

🟢 建议 - utils.ts:15
- 问题：函数命名不规范
- 建议：使用 camelCase 命名风格
```

---

## 注意事项
| 项目 | 说明 |
| --- | --- |
| **文件编码** | 使用 UTF-8 编码 |
| **文件名** | 必须为 `SKILL.md`（大写） |
| **YAML 语法** | Frontmatter 必须是合法的 YAML 格式 |
| **兼容性** | 遵循 Agent Skills 标准，可在多个 AI 工具间复用 |


---

## 空白模板
复制以下模板创建你的 Skill：

```markdown
---
name: your-skill-name
description: 功能说明。使用场景说明。触发关键词。
argument-hint: [参数提示]
---

# Skill 标题

简要说明 Skill 的功能和用途。

## 任务说明

明确说明 Skill 要完成的任务。

## 执行步骤

1. 第一步
2. 第二步
3. ...

## 输出格式

规定输出的格式和结构。

## 示例

提供输出示例。
```

---

## 更多资源
+ [Agent Skills 开放标准](https://agentskills.io/)
+ [Anthropic Skills 官方文档](https://docs.anthropic.com/claude/docs/skills)
+ [Skill 开发与注册](./03-Skill开发与注册)
