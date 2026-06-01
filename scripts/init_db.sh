#!/usr/bin/env bash
# 一次性建表(等价 alembic upgrade head)。
set -euo pipefail
cd "$(dirname "$0")/../backend"
. .venv/bin/activate
alembic upgrade head
