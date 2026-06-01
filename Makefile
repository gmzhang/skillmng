# Skill Management System - Docker Build & Deploy
-include .env

# --- Container config ---
CONTAINER_NAME ?= skillmng
LOCAL_PORT ?= 80

# --- Image config ---
REGISTRY := reg.antgroup-inc.cn/shining
APP_NAME := skillmng
TIMESTAMP := $(shell date +"%Y%m%d%H%M%S")
NEW_IMAGE := $(REGISTRY)/$(APP_NAME):$(TIMESTAMP)
IMAGE_NAME ?= $(REGISTRY)/$(APP_NAME):latest
BUILD_PLATFORM ?= linux/amd64
BUILD_FORMAT ?= docker

# --- Data persistence ---
DATA_DIR ?= $(HOME)/skillmng-data

.PHONY: build run stop logs exec push clean dev

# ===== Build image =====
build:
	@echo "Building image $(NEW_IMAGE)..."
	podman build --platform $(BUILD_PLATFORM) --format $(BUILD_FORMAT) --layers -t $(NEW_IMAGE) .
	@echo "Updating .env with new IMAGE_NAME=$(NEW_IMAGE)..."
	@if [ -f .env ] && grep -q "^IMAGE_NAME=" .env; then \
		sed -i.bak "s|^IMAGE_NAME=.*|IMAGE_NAME=$(NEW_IMAGE)|" .env; \
	else \
		echo "IMAGE_NAME=$(NEW_IMAGE)" >> .env; \
	fi
	@rm -f .env.bak
	@echo "Build complete! Run 'make push' or 'make run'."

# ===== Run container =====
run:
	@echo "Starting [$(CONTAINER_NAME)] on port $(LOCAL_PORT)..."
	@echo "Using image: $(IMAGE_NAME)"
	@echo "Data dir: $(DATA_DIR)"
	@mkdir -p "$(DATA_DIR)/git/skill-repos"
	@podman rm -f $(CONTAINER_NAME) >/dev/null 2>&1 || true
	podman run -d \
		--name $(CONTAINER_NAME) \
		--restart unless-stopped \
		--network=host \
		-v $(DATA_DIR):/app/backend/data \
		--env-file .env \
		-e PORT=$(LOCAL_PORT) \
		--log-opt max-size=50m \
		--log-opt max-file=2 \
		$(IMAGE_NAME)
	@echo "Instance [$(CONTAINER_NAME)] is running on http://localhost:$(LOCAL_PORT)"
	@echo "SQLite: $(DATA_DIR)/skillmng.sqlite3"

# ===== Stop container =====
stop:
	@echo "Stopping [$(CONTAINER_NAME)]..."
	podman rm -f $(CONTAINER_NAME)

# ===== View logs =====
logs:
	podman logs -f $(CONTAINER_NAME)

# ===== Shell into container =====
exec:
	podman exec -it $(CONTAINER_NAME) bash

# ===== Push image =====
push:
	@echo "Pushing $(IMAGE_NAME)..."
	podman push $(IMAGE_NAME)

# ===== Clean data (DANGEROUS) =====
clean:
	@echo "WARNING: This will delete ALL data in $(DATA_DIR)"
	@read -p "Confirm? [y/N] " confirm; [ "$$confirm" = "y" ] || exit 1
	rm -rf "$(DATA_DIR)"

# ===== Local dev (no docker) =====
dev:
	@echo "Starting backend + frontend for local dev..."
	cd backend && . .venv/bin/activate && alembic upgrade head && uvicorn app.main:app --reload --port 8000 &
	cd frontend && pnpm dev &
	@wait
