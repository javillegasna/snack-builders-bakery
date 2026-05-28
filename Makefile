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
	uv run pytest -q

.PHONY: check
check:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src/app
	uv run pytest -q

.PHONY: run
run:
	uv run uvicorn app.main:app --reload

.PHONY: up
up:
	docker compose up --build

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
