# Contributing to skillmng
Thank you for your interest in contributing to skillmng.

skillmng is a management system for Agent Skills, including Skill creation, validation, versioning, LLM-assisted editing, Git-backed publishing, import/export, and audit workflows.

## Ways to contribute
You can help by:

+ Reporting bugs
+ Suggesting new Skill management workflows
+ Improving documentation
+ Adding tests
+ Improving frontend usability
+ Improving backend validation, security, or Git workflows
+ Adding examples of real-world Skills

## Development setup
Backend:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
pytest -q
```

<font style="color:rgb(26, 28, 31);">Frontend:</font>

```bash
cd frontend
pnpm install
pnpm dev
```

## <font style="color:rgb(26, 28, 31);">Pull request guidelines</font>
<font style="color:rgb(26, 28, 31);">Before opening a pull request, please:</font>

1. <font style="color:rgb(26, 28, 31);">Keep the change focused.</font>
2. <font style="color:rgb(26, 28, 31);">Add or update tests when behavior changes.</font>
3. <font style="color:rgb(26, 28, 31);">Do not commit real tokens, API keys, SSH keys, cookies, or private data.</font>
4. <font style="color:rgb(26, 28, 31);">Run backend tests when touching backend code.</font>
5. <font style="color:rgb(26, 28, 31);">Run frontend type checks/build when touching frontend code.</font>
6. <font style="color:rgb(26, 28, 31);">Explain the motivation and behavior change clearly in the PR description.</font>

## <font style="color:rgb(26, 28, 31);">Security and safety expectations</font>
<font style="color:rgb(26, 28, 31);">Contributions must preserve these project invariants:</font>

+ <font style="color:rgb(26, 28, 31);">Tenant isolation: user identity must come from trusted server-side context or configured cookies, not request body fields.</font>
+ <font style="color:rgb(26, 28, 31);">Path safety: reject absolute paths,</font><font style="color:rgb(26, 28, 31);"> </font><font style="color:rgb(26, 28, 31);">..</font><font style="color:rgb(26, 28, 31);">, control characters, unsafe zip entries, and oversized files.</font>
+ <font style="color:rgb(26, 28, 31);">Secret hygiene: never log or commit secrets.</font>
+ <font style="color:rgb(26, 28, 31);">Git safety: do not rewrite published history for restore workflows.</font>
+ <font style="color:rgb(26, 28, 31);">LLM safety: keep provider configuration explicit, avoid logging full prompts/responses with sensitive data, and support mock/test modes.</font>

## <font style="color:rgb(26, 28, 31);">Code style</font>
<font style="color:rgb(26, 28, 31);">Prefer small, readable changes that follow the existing project structure:</font>

+ <font style="color:rgb(26, 28, 31);">Backend HTTP handlers should stay thin.</font>
+ <font style="color:rgb(26, 28, 31);">Business logic belongs in service modules.</font>
+ <font style="color:rgb(26, 28, 31);">Frontend API calls belong in</font><font style="color:rgb(26, 28, 31);"> </font><font style="color:rgb(26, 28, 31);">frontend/src/api</font><font style="color:rgb(26, 28, 31);">.</font>
+ <font style="color:rgb(26, 28, 31);">Shared frontend UI belongs in</font><font style="color:rgb(26, 28, 31);"> </font><font style="color:rgb(26, 28, 31);">frontend/src/components</font><font style="color:rgb(26, 28, 31);">.</font>
+ <font style="color:rgb(26, 28, 31);">Tests should cover security-sensitive behavior whenever possible.</font>

## <font style="color:rgb(26, 28, 31);">License</font>
<font style="color:rgb(26, 28, 31);">By contributing, you agree that your contributions will be licensed under the MIT License.</font>
