#!/bin/bash
set -euo pipefail

APP_DIR="/app/backend"
DATA_DIR="$APP_DIR/data"
SSH_DIR="/root/.ssh"

mkdir -p "$DATA_DIR/git/skill-repos"

# --- SSH key setup (for Git push/pull to AntCode) ---
if [ -n "${SSH_PRIVATE_KEY:-}" ]; then
    echo "[INFO] Setting up SSH key from SSH_PRIVATE_KEY..."
    mkdir -p "$SSH_DIR"
    chmod 700 "$SSH_DIR"

    # 使用 SKILL_GIT_SSH_KEY 指定的文件名，默认 id_rsa
    SSH_KEY_FILE="${SKILL_GIT_SSH_KEY:-$SSH_DIR/id_rsa}"

    if echo "$SSH_PRIVATE_KEY" | base64 -d > "$SSH_KEY_FILE.tmp" 2>/dev/null; then
        mv "$SSH_KEY_FILE.tmp" "$SSH_KEY_FILE"
    else
        rm -f "$SSH_KEY_FILE.tmp"
        printf '%s\n' "$SSH_PRIVATE_KEY" > "$SSH_KEY_FILE"
    fi
    chmod 600 "$SSH_KEY_FILE"

    touch "$SSH_DIR/known_hosts"
    chmod 600 "$SSH_DIR/known_hosts"

    if [ -n "${ANTCODE_HOST:-code.myxiaojin.cn}" ]; then
        ssh-keyscan -H "${ANTCODE_HOST:-code.myxiaojin.cn}" >> "$SSH_DIR/known_hosts" 2>/dev/null || true
    fi

    export GIT_SSH_COMMAND="ssh -i $SSH_KEY_FILE -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$SSH_DIR/known_hosts"
    export SKILL_GIT_SSH_KEY="$SSH_KEY_FILE"
    echo "[INFO] SSH key installed at $SSH_KEY_FILE"
fi

# --- Database migration ---
echo "[INFO] Running database migrations..."
cd "$APP_DIR"
alembic upgrade head

echo "[INFO] Starting application on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
