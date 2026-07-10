# =============================================================================
# Enterprise AutoML Platform — developer task runner
# =============================================================================
.DEFAULT_GOAL := help
SHELL := /bin/bash

BACKEND := backend
VENV := $(BACKEND)/.venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# --- Backend -----------------------------------------------------------------
.PHONY: install
install: ## Create venv and install backend dev + ml dependencies
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e "$(BACKEND)[dev,ml]"

.PHONY: run
run: ## Run the API with autoreload
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: worker
worker: ## Run the Celery worker
	cd $(BACKEND) && .venv/bin/celery -A app.worker.celery_app worker --loglevel=info

.PHONY: migrate
migrate: ## Apply database migrations
	cd $(BACKEND) && .venv/bin/alembic upgrade head

.PHONY: revision
revision: ## Autogenerate a migration (usage: make revision m="message")
	cd $(BACKEND) && .venv/bin/alembic revision --autogenerate -m "$(m)"

# --- Quality -----------------------------------------------------------------
.PHONY: lint
lint: ## Run ruff, black --check and mypy
	cd $(BACKEND) && .venv/bin/ruff check app tests
	cd $(BACKEND) && .venv/bin/black --check app tests
	cd $(BACKEND) && .venv/bin/mypy app

.PHONY: format
format: ## Auto-format with black and ruff
	cd $(BACKEND) && .venv/bin/ruff check --fix app tests
	cd $(BACKEND) && .venv/bin/black app tests

.PHONY: test
test: ## Run the test suite with coverage
	cd $(BACKEND) && .venv/bin/pytest --cov=app --cov-report=term-missing

# --- Docker ------------------------------------------------------------------
.PHONY: up
up: ## Start the full stack with docker compose
	docker compose up -d --build

.PHONY: down
down: ## Stop the stack
	docker compose down

.PHONY: logs
logs: ## Tail service logs
	docker compose logs -f
