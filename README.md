# Skill 管理系统

skillmng is an open-source management platform for Agent Skills. It helps maintainers create, validate, version, review, and publish reusable Skills with Git-backed history, secure import/export, audit logs, and LLM-assisted editing workflows.

The project is especially designed for Codex-style and agentic development workflows where Skills need to be maintained as structured, reviewable, testable software artifacts.

面向 Agent 的 Skill 创建、版本管理、LLM 辅助优化与 Git 托管平台。
完整需求见 [`feature/prd1.md`](./feature/prd1.md);Skill 文件规范见 [`doc/guifan.md`](./doc/guifan.md)。

## 技术栈

- **后端**:Python 3.11+ / FastAPI / SQLAlchemy 2.x / Alembic / sqlite / GitPython
- **前端**:React 18 / TypeScript / Vite / Ant Design 5 / Tailwind / TanStack Query / Monaco Editor
- **持久化**:`./data/skillmng.sqlite3` (后续可平滑迁 PostgreSQL)

## 本地启动

### 1. 准备配置

```bash
cp .env.example .env
# 按需修改 .env;敏感字段(token/密钥)切勿提交回仓库
```

### 2. 启动后端

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

或直接:`./scripts/run_backend.sh`

### 3. 启动前端

```bash
cd frontend
pnpm install
pnpm dev
```

或直接:`./scripts/run_frontend.sh`

### 4. 设置测试 Cookie

打开浏览器访问 <http://localhost:5173>。当前阶段没有登录页,需要在 DevTools → Application → Cookies → http://localhost:5173 中手动添加:

| 字段 | 值 | 说明 |
|---|---|---|
| `user_id` | `alice` | 必需,租户隔离主键 |
| `user_name` | `Alice` | 可选,展示用 |
| `user_email` | `alice@example.com` | 可选,Git author 用 |

刷新页面即可看到当前用户信息。换 `user_id=bob` 可验证跨租户隔离。

## 测试

```bash
cd backend
. .venv/bin/activate
pytest -x
```

端到端 smoke test(严格按 PRD §14.3 9 步运行):

```bash
pytest tests/test_smoke.py -v
```

涵盖测试范围:租户隔离、SKILL.md 校验、路径安全、Skill CRUD、Git 版本(commit/diff/restore)、LLM Mock 完整链路、zip 导入安全。

## 服务器部署

### Docker 构建 & 运行

```bash
make build   # 构建镜像
make run     # 启动容器
make logs    # 查看日志
make stop    # 停止容器
```

### 数据持久化

容器运行时数据挂载在宿主机 `~/skillmng-data/`（可通过 `DATA_DIR` 覆盖）:

```
~/skillmng-data/
├── skillmng.sqlite3           # 主数据库（Skill、用户、版本、审计日志等）
├── skillmng.sqlite3-wal       # SQLite WAL 日志（备份时需一起同步）
└── git/
    └── skill-repos/           # 各 Skill 的本地 Git 仓库
        ├── alice--my-skill/
        └── bob--code-review/
```

**OSS 同步注意事项**:
- 同步 `skillmng.sqlite3` 时必须同时同步 `skillmng.sqlite3-wal` 和 `skillmng.sqlite3-shm`（如果存在），否则数据不完整。
- 建议在容器停止状态下同步，或使用 `sqlite3 skillmng.sqlite3 "VACUUM INTO '/tmp/backup.sqlite3'"` 生成一致性快照再同步。
- `git/skill-repos/` 是各 Skill 的完整 Git 仓库，已推送到 GIT 的数据可从远端恢复，未推送的仅存在于此目录。

## 目录结构

```
skillmng/
├── backend/        Python FastAPI 后端
├── frontend/       React + Vite 前端
├── data/           运行时数据(sqlite + Git 工作区,gitignored)
├── scripts/        启动脚本
├── feature/prd1.md 需求规格
├── doc/guifan.md   SKILL.md 公司规范
├── CLAUDE.md       Agent 协作指引
└── .env.example    完整配置示例
```

## 第一阶段范围

按 PRD §18 推进里程碑(本次会话全部完成,共 51 个后端测试通过):

- [x] **M1** — 可运行骨架(双服务、sqlite、Cookie 用户、`.env.example`)
- [x] **M2** — Skill CRUD + 文件树 + `SKILL.md` 校验
- [x] **M3** — Git 版本管理(commit、diff、restore)
- [x] **M4** — LLM 辅助创建/更新(全 Mock,接口预留真实切换)
- [x] **M5** — 导入导出(zip 安全)+ 审计日志 + smoke test

### 主要功能入口

- `/` 工作台
- `/skills` Skill 列表(支持搜索、导出、导入 zip)
- `/skills/new` 创建 Skill(手动 / LLM 辅助 两种模式)
- `/skills/:id` 详情(文件树 + Monaco 编辑器,发布版本、LLM 辅助更新弹窗)
- `/skills/:id/versions` 版本历史(发布、恢复、多选对比)
- `/skills/:id/diff` 版本 diff(Monaco DiffEditor 分文件查看)
- `/llm-jobs` LLM 任务列表(实时刷新、详情、落地、取消)
- `/audit-logs` 审计日志

## 关键约束

- Cookie 中的 `user_id` 是**唯一**租户来源,前端 body/query 中的 `user_id` 必须忽略 (PRD §4.2)。
- 不提交真实 token/SSH 私钥;`.env` 已纳入 `.gitignore`。
- 中文注释为权威版本(详见 [LEGAL.md](./LEGAL.md))。
- Git auto-create-via-API 暂不实现,需要管理员先在 `xiaojin-skills` 下手动建仓库,再通过 `PATCH /api/skills/{id}/repository` 绑定 remote URL。
