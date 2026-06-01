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

Frontend:

```bash
cd frontend
pnpm install
pnpm dev
```

## Pull request guidelines
Before opening a pull request, please:

1. Keep the change focused.
2. Add or update tests when behavior changes.
3. Do not commit real tokens, API keys, SSH keys, cookies, or private data.
4. Run backend tests when touching backend code.
5. Run frontend type checks/build when touching frontend code.
6. Explain the motivation and behavior change clearly in the PR description.

## Security and safety expectations
Contributions must preserve these project invariants:

+ Tenant isolation: user identity must come from trusted server-side context or configured cookies, not request body fields.
+ Path safety: reject absolute paths,.., control characters, unsafe zip entries, and oversized files.
+ Secret hygiene: never log or commit secrets.
+ Git safety: do not rewrite published history for restore workflows.
+ LLM safety: keep provider configuration explicit, avoid logging full prompts/responses with sensitive data, and support mock/test modes.

## Code style
Prefer small, readable changes that follow the existing project structure:

+ Backend HTTP handlers should stay thin.
+ Business logic belongs in service modules.
+ Frontend API calls belong in frontend/src/api.
+ Shared frontend UI belongs in frontend/src/components.
+ Tests should cover security-sensitive behavior whenever possible.

## License
By contributing, you agree that your contributions will be licensed under the MIT License.
