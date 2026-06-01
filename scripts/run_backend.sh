#!/usr/bin/env bash
# 启动后端开发服务。需先 pip install -e ".[dev]" 与 alembic upgrade head。
set -euo pipefail
cd "$(dirname "$0")/../backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
pip install -q -e ".[dev]" >/dev/null
alembic upgrade head
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
