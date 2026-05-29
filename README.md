# Snack Builders Bakery — Backend API

Backend for a bakery (cookies, pastries, breads). It runs the storefront menu,
customer orders and payments, and a **priority-based kitchen scheduler** that
decides what bakes, when, across a limited set of ovens.

## How it works

**The kitchen** has 2 ovens × 3 trays = **6 items baking at once**. The scheduling
unit is one snack on one tray (an order of 3 cookies uses 3 trays).

**Priority queue.** Orders are VIP, app/delivery, or walk-in. When a tray frees,
the highest-priority waiting unit goes in. **No preemption** — anything already
baking finishes; a VIP only jumps the *waiting* line, which pushes later orders'
estimates back.

**Order lifecycle:**

```
PENDING_PAYMENT ──pay──▶ QUEUED ──▶ BAKING ──▶ READY ──pickup──▶ COMPLETED
       │                  └──────── kitchen ────────┘
       └──▶ CANCELLED
```

- **Placement** returns a *provisional* ETA (non-mutating simulation); the order
  doesn't hold an oven yet.
- **Payment** commits the order into the live queue and returns the *authoritative*
  ETA. Other orders' ETAs are recomputed and persisted.
- The kitchen **persists progress** (`BAKING`/`READY` + timestamps) and **rebuilds
  its queue on restart** from active orders.

**Bake time** defaults per category (cookie 5 min, pastry 10 min, bread 20 min) and
can be overridden per menu item (`bake_seconds`).

## Stack

- **FastAPI** (async) + **Pydantic v2**
- **PostgreSQL** + **SQLAlchemy 2.0 (async)** + **Alembic**
- Pure-Python scheduler core (`heapq`) with an injectable clock for deterministic,
  fast-forwardable tests
- **pytest** (unit) + black-box **e2e** (httpx flows + Schemathesis contract tests)
- **Docker Compose** for one-command setup; **OpenTelemetry → OpenObserve** for logs,
  metrics and traces
- **uv** for dependency management

## Layout

Modular monolith, organized by feature (vertical slices) — each owns its router,
service, repository, models and schemas:

```
src/app/
  core/      # config, db, clock, logging, telemetry
  menu/      # browse + manage items
  orders/    # place, track, pickup, state machine
  payments/  # cash / card (Strategy)
  kitchen/   # the scheduler + live engine
src/migrations/   # Alembic migrations
src/tests/        # unit tests, by module
src/e2e/          # black-box tests against a running API
```

The scheduler never reads the wall clock directly — time is passed in — so the
trickiest logic is easy to test and the suite can simulate "20 minutes from now"
without waiting.

## Endpoints

| Method | Endpoint | What |
|--------|----------|------|
| GET    | `/menu` | browse available items |
| POST   | `/menu/items` | add an item (optional `bake_seconds` override) |
| PATCH  | `/menu/items/{id}` | update an item |
| DELETE | `/menu/items/{id}` | remove an item (409 if referenced by orders) |
| POST   | `/orders` | place an order → price + provisional ETA |
| GET    | `/orders/{id}` | track status + ETA + timings |
| POST   | `/orders/{id}/payment` | pay (cash/card) → enqueue + authoritative ETA |
| POST   | `/orders/{id}/pickup` | mark a `READY` order collected → `COMPLETED` |
| GET    | `/kitchen/status` | ovens, trays and the waiting queue |
| GET    | `/health` · `/health/ready` | liveness · readiness (DB) |

Interactive API docs at `/docs` once the app is running.

## Running it

Prerequisites: **Docker** (+ Compose) and **uv**.

```bash
make up        # build + run the full stack (API, Postgres, OpenObserve)
```

API on http://localhost:8000 (docs at `/docs`). Postgres is not exposed to the host.

### Common commands

| Command | What |
|---------|------|
| `make up` | run the whole stack in Docker |
| `make down` | stop the stack |
| `make install` | install dependencies (`uv sync --extra dev`) |
| `make run` | run the API locally with reload |
| `make test` | unit tests (in the compose network) |
| `make check` | lint + format check + type check + unit tests |
| `make e2e` | e2e flows + Schemathesis contract tests |
| `make migrate` | apply migrations (`alembic upgrade head`) |
| `make migration m="..."` | create a new migration |
| `make migrate-down` | roll back the last migration |
| `make obs` / `make dashboards` | run OpenObserve / seed its dashboards |

## Development notes

- **Migrations ship in their own PR**, merged before the code that depends on the
  new schema.
- The kitchen engine is a single in-memory instance guarded by one lock — all
  oven/queue changes go through it, which is how double-booked trays are avoided.
  It does not yet scale horizontally (one process owns the queue).
- Money is `Decimal` (`Numeric(10,2)`); prices are validated and snapshotted onto
  the order at placement time.
