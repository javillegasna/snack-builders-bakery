.DEFAULT_GOAL := help

.PHONY: help
help:  ## List available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install:  ## Install dependencies (uv sync --extra dev)
	uv sync --extra dev

.PHONY: lint
lint:  ## Run ruff linter
	uv run ruff check .

.PHONY: format
format:  ## Format code with ruff
	uv run ruff format .

.PHONY: typecheck
typecheck:  ## Run mypy type checker
	uv run mypy src/app

.PHONY: test
test:  ## Run unit tests in the compose network
	docker compose --profile test run --build --rm tests

.PHONY: check
check:  ## Lint + format check + type check + unit tests
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src/app
	docker compose --profile test run --build --rm tests

.PHONY: run
run:  ## Run the API locally with reload
	uv run uvicorn app.main:app --reload

.PHONY: up
up:  ## Build + run the full stack (API, Postgres, OpenObserve)
	docker compose up --build

.PHONY: obs
obs:  ## Run OpenObserve only
	docker compose up openobserve

.PHONY: dashboards
dashboards:  ## Seed OpenObserve dashboards
	uv run python src/observability/seed_dashboards.py

.PHONY: e2e
e2e:  ## Run e2e flows + Schemathesis contract tests
	docker compose up -d --build api
	E2E_BASE_URL=http://localhost:8000 uv run pytest src/e2e -q
	uv run schemathesis run http://localhost:8000/openapi.json --checks not_a_server_error --phases coverage,stateful

.PHONY: e2e-flows
e2e-flows:  ## Run e2e httpx flows only
	docker compose up -d --build api
	E2E_BASE_URL=http://localhost:8000 uv run pytest src/e2e -q

.PHONY: e2e-fuzz-full
e2e-fuzz-full:  ## Run full Schemathesis fuzzing
	docker compose up -d --build api
	uv run schemathesis run http://localhost:8000/openapi.json

.PHONY: down
down:  ## Stop the stack
	docker compose down

.PHONY: migrate
migrate:  ## Apply migrations (alembic upgrade head)
	uv run alembic upgrade head

.PHONY: migrate-down
migrate-down:  ## Roll back the last migration
	uv run alembic downgrade -1

.PHONY: migration
migration:  ## Create a migration: make migration m="message"
	uv run alembic revision -m "$(m)"
