FROM python:3.12-alpine AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md alembic.ini ./
COPY src/app ./src/app
COPY src/migrations ./src/migrations
RUN uv pip install --system .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

FROM runtime AS test

RUN uv pip install --system ".[dev]"

COPY src/tests ./src/tests

CMD ["pytest", "-q"]
