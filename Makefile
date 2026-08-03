# OpenClaw multi-agent Telegram mesh
# Python tooling runs in Docker. See AGENTS.md.

SHELL := /bin/bash
.DEFAULT_GOAL := help
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PY_IMAGE := python:3.11-slim
# Run generators as the host user so agents/* is not root-owned.
HOST_UID := $(shell id -u)
HOST_GID := $(shell id -g)
PY_RUN := docker run --rm -u $(HOST_UID):$(HOST_GID) -v "$(ROOT):/app" -w /app $(PY_IMAGE)
PY_RUN_TTY := docker run --rm -it -u $(HOST_UID):$(HOST_GID) -v "$(ROOT):/app" -w /app $(PY_IMAGE)

FROM ?= agent-1
TO_USER ?=
SERVICE ?=

.PHONY: help setup generate up down restart ps logs pull config health \
	test lint fmt test-a2a enable-deepseek enable_deepseek clean \
	chown-agents fix-perms doctor

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n" } \
		/^[a-zA-Z0-9_.-]+:.*##/ { printf "  %-16s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

setup: ## Interactive setup (agents, tokens, owner id, optional DeepSeek)
	$(PY_RUN_TTY) python setup_agents.py

generate: ## Non-interactive default 2-agent placeholder stack
	$(PY_RUN) python generate_stack.py --agents 2 --owner-id OWNER_TELEGRAM_ID --write-live-env

up: fix-perms ## Start all agent gateways
	docker compose up -d
	@echo "up: started. Tip: make health (retries until ready)"

down: ## Stop and remove containers/networks
	docker compose down

restart: down up ## Recreate the stack

ps: ## Show compose service status
	docker compose ps

logs: ## Tail logs (optional SERVICE=agent-1)
	@if [ -n "$(SERVICE)" ]; then docker compose logs -f $(SERVICE); \
	else docker compose logs -f; fi

pull: ## Pull OpenClaw image
	docker compose pull

config: ## Validate generated compose file
	docker compose config -q
	@echo "compose config: OK"

health: ## Check /healthz on host ports 18789..(18788+N)
	docker run --rm --network host -v "$(ROOT):/app" -w /app $(PY_IMAGE) \
		python scripts_health.py

test: ## Run unit tests in Docker (pytest)
	docker run --rm -v "$(ROOT):/app" -w /app $(PY_IMAGE) \
		sh -c "pip install -q -r requirements-dev.txt && pytest -q"

lint: ## Run ruff lint + format check in Docker
	docker run --rm -v "$(ROOT):/app" -w /app $(PY_IMAGE) \
		sh -c "pip install -q -r requirements-dev.txt && ruff check . && ruff format --check ."

fmt: ## Auto-format Python with ruff
	docker run --rm -v "$(ROOT):/app" -w /app $(PY_IMAGE) \
		sh -c "pip install -q -r requirements-dev.txt && ruff check --fix . && ruff format ."

test-a2a: ## Telegram A2A test (FROM=agent-1 TO_USER=optional; auto-picks peer)
	@chmod +x ./test_a2a.sh
	./test_a2a.sh "$(FROM)" "$(TO_USER)"

enable-deepseek: ## Install DeepSeek provider plugin inside each running agent
	@# Must run on host (needs docker CLI); do not wrap in python container.
	python3 enable_deepseek.py

enable_deepseek: enable-deepseek ## Alias for enable-deepseek (underscore)

chown-agents: fix-perms ## Alias for fix-perms

fix-perms: ## Ensure agents/* is writable by OpenClaw uid 1000 (via Docker)
	@docker run --rm -v "$(ROOT)/agents:/agents" busybox:1.36 \
		sh -c 'chown -R 1000:1000 /agents && chmod -R a+rwX /agents'
	@echo "fix-perms: agents/ -> uid 1000"

clean: ## Remove containers; keep configs and secrets
	docker compose down --remove-orphans || true
	@echo "Clean complete. agents/*/.env kept."

doctor: config lint test ## Validate compose + lint + unit tests
	@echo "doctor: all local checks passed"
