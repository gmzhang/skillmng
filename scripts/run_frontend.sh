#!/usr/bin/env bash
# 启动前端开发服务。需先 pnpm install。
set -euo pipefail
cd "$(dirname "$0")/../frontend"
if [ ! -d node_modules ]; then
  pnpm install
fi
exec pnpm dev
