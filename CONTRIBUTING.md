# Contributing to skillmng

Thank you for your interest in contributing to skillmng.

skillmng is a management system for Agent Skills, including Skill creation, validation, versioning, LLM-assisted editing, Git-backed publishing, import/export, and audit workflows.

## Ways to contribute

You can help by:

- Reporting bugs
- Suggesting new Skill management workflows
- Improving documentation
- Adding tests
- Improving frontend usability
- Improving backend validation, security, or Git workflows
- Adding examples of real-world Skills

## Development setup

Backend:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
pytest -q
