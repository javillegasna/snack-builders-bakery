.PHONY: install lint format typecheck test check run up down

install:
	uv sync --extra dev

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src/app

test:
	uv run pytest -q

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src/app
	uv run pytest -q

run:
	uv run uvicorn app.main:app --reload

up:
	docker compose up --build

down:
	docker compose down
