.PHONY: install
install:
	uv sync --extra dev

.PHONY: lint
lint:
	uv run ruff check .

.PHONY: format
format:
	uv run ruff format .

.PHONY: typecheck
typecheck:
	uv run mypy src/app

.PHONY: test
test:
	docker compose --profile test run --build --rm tests

.PHONY: check
check:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src/app
	docker compose --profile test run --build --rm tests

.PHONY: run
run:
	uv run uvicorn app.main:app --reload

.PHONY: up
up:
	docker compose up --build

.PHONY: obs
obs:
	docker compose up openobserve

.PHONY: dashboards
dashboards:
	uv run python src/observability/seed_dashboards.py

.PHONY: e2e
e2e:
	docker compose up -d --build api
	E2E_BASE_URL=http://localhost:8000 uv run pytest src/e2e -q
	uv run schemathesis run http://localhost:8000/openapi.json --checks not_a_server_error --phases coverage,stateful

.PHONY: e2e-flows
e2e-flows:
	docker compose up -d --build api
	E2E_BASE_URL=http://localhost:8000 uv run pytest src/e2e -q

.PHONY: e2e-fuzz-full
e2e-fuzz-full:
	docker compose up -d --build api
	uv run schemathesis run http://localhost:8000/openapi.json

.PHONY: down
down:
	docker compose down

.PHONY: migrate
migrate:
	uv run alembic upgrade head

.PHONY: migrate-down
migrate-down:
	uv run alembic downgrade -1

.PHONY: migration
migration:
	uv run alembic revision -m "$(m)"
