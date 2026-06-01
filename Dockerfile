# ============================================================
# Skill Management System - Multi-stage Docker Build
# ============================================================

# ---------- Stage 1: Frontend build ----------
FROM reg.docker.alibaba-inc.com/dockerhub_common/node:21-alpine3.18 AS frontend-builder

ENV NPM_CONFIG_REGISTRY=https://registry.npm.alibaba-inc.com/

WORKDIR /build/frontend
RUN npm install -g pnpm@9

COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend/ ./
RUN pnpm build

# ---------- Stage 2: Runtime ----------
FROM reg.docker.alibaba-inc.com/ant-base/linkex-python-service:3.10.0-20260113165355

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install git & ssh if missing (compatible with yum/microdnf/apt base images)
RUN set -eux; \
    if command -v git >/dev/null 2>&1 && command -v ssh >/dev/null 2>&1; then \
        echo "git and ssh already installed"; \
    elif command -v yum >/dev/null 2>&1; then \
        yum install -y git openssh-clients && yum clean all; \
    elif command -v microdnf >/dev/null 2>&1; then \
        microdnf install -y git openssh-clients && microdnf clean all; \
    elif command -v apt-get >/dev/null 2>&1; then \
        apt-get update && apt-get install -y --no-install-recommends git openssh-client && rm -rf /var/lib/apt/lists/*; \
    else \
        echo "WARNING: no package manager found, git/ssh must be pre-installed"; \
    fi

WORKDIR /app

# Install Python dependencies (use Aliyun mirror for speed)
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip config set global.trusted-host mirrors.aliyun.com \
    && pip install --no-cache-dir --upgrade pip setuptools wheel
COPY backend/pyproject.toml backend/
RUN cd backend && pip install --no-cache-dir .

# Copy backend source (overwrite with full source)
COPY backend/ backend/

# Copy frontend build output
COPY --from=frontend-builder /build/frontend/dist backend/static

# Create data directories
RUN mkdir -p backend/data/git/skill-repos

# Copy entrypoint
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /app/backend

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
