#!/bin/bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
STATIC_DIR="$BACKEND_DIR/static"
PID_FILE="$APP_DIR/.uvicorn.pid"
PORT="${PORT:-80}"

# Load .env
if [ -f "$APP_DIR/.env" ]; then
    set -a
    source "$APP_DIR/.env"
    set +a
fi

# --- SSH setup (for Git operations) ---
setup_ssh() {
    if [ -n "${SSH_PRIVATE_KEY:-}" ]; then
        mkdir -p ~/.ssh
        chmod 700 ~/.ssh
        if echo "$SSH_PRIVATE_KEY" | base64 -d > ~/.ssh/id_rsa.tmp 2>/dev/null; then
            mv ~/.ssh/id_rsa.tmp ~/.ssh/id_rsa
        else
            rm -f ~/.ssh/id_rsa.tmp
            printf '%s\n' "$SSH_PRIVATE_KEY" > ~/.ssh/id_rsa
        fi
        chmod 600 ~/.ssh/id_rsa
        ssh-keyscan -H code.myxiaojin.cn >> ~/.ssh/known_hosts 2>/dev/null || true
        export GIT_SSH_COMMAND="ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=accept-new"
        export SKILL_GIT_SSH_KEY=~/.ssh/id_rsa
        echo "[INFO] SSH key configured."
    fi
}

# --- Stop ---
stop() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "[INFO] Stopping uvicorn (PID $pid)..."
            kill "$pid"
            sleep 2
        fi
        rm -f "$PID_FILE"
    fi
    echo "[INFO] Stopped."
}

# --- Start ---
start() {
    stop

    # 1) Python venv
    echo "[INFO] Setting up Python environment..."
    cd "$BACKEND_DIR"
    if [ ! -d .venv ]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    pip install -q -e ".[dev]"

    # 2) Database migration
    echo "[INFO] Running database migrations..."
    alembic upgrade head

    # 3) Build frontend
    echo "[INFO] Building frontend..."
    cd "$FRONTEND_DIR"
    if ! command -v pnpm >/dev/null 2>&1; then
        npm install -g pnpm
    fi
    pnpm install --frozen-lockfile
    pnpm build

    # 4) Copy frontend dist to backend/static
    echo "[INFO] Deploying frontend to backend/static..."
    rm -rf "$STATIC_DIR"
    cp -r "$FRONTEND_DIR/dist" "$STATIC_DIR"

    # 5) SSH
    setup_ssh

    # 6) Start uvicorn
    echo "[INFO] Starting uvicorn on port $PORT..."
    cd "$BACKEND_DIR"
    source .venv/bin/activate
    nohup uvicorn app.main:app --host 0.0.0.0 --port "$PORT" > "$APP_DIR/uvicorn.log" 2>&1 &
    echo $! > "$PID_FILE"
    echo "[INFO] Server started (PID $(cat "$PID_FILE")), listening on http://0.0.0.0:$PORT"
    echo "[INFO] Logs: tail -f $APP_DIR/uvicorn.log"
}

# --- Restart ---
restart() {
    start
}

# --- Status ---
status() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Running (PID $(cat "$PID_FILE")), port $PORT"
    else
        echo "Stopped"
    fi
}

# --- Main ---
case "${1:-start}" in
    start)   start ;;
    stop)    stop ;;
    restart) restart ;;
    status)  status ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
