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
  ETA; other orders' ETAs are recomputed and persisted.
- The kitchen **persists progress** and **rebuilds its queue on restart** from
  active orders.

Bake time defaults per category and can be overridden per menu item.

## Stack

- **FastAPI** (async) + **Pydantic**
- **PostgreSQL** + **SQLAlchemy** (async) + **Alembic**
- Pure-Python scheduler core (`heapq`) with an injectable clock for deterministic,
  fast-forwardable tests
- **pytest** (unit) + black-box **e2e** (httpx flows + Schemathesis)
- **Docker Compose**; **OpenTelemetry → OpenObserve** for logs, metrics and traces

Exact versions live in [`pyproject.toml`](pyproject.toml).

## Layout

Modular monolith, organized by feature (vertical slices) — each owns its router,
service, repository, models and schemas:

```
src/app/
  core/      # config, db, clock, logging, telemetry
  menu/      # browse + manage items
  orders/    # place, track, pickup, state machine
  payments/  # cash / card (Strategy)
  kitchen/   # scheduler + live engine
src/migrations/   # Alembic migrations
src/tests/        # unit tests, by module
src/e2e/          # black-box tests against a running API
```

The scheduler never reads the wall clock directly — time is passed in — so the
trickiest logic is easy to test and the suite can simulate "20 minutes from now"
without waiting.

> **Best way to understand the system:** read the black-box e2e tests in
> [`src/e2e/`](src/e2e/). They exercise the real use cases end-to-end (place → pay →
> bake → pickup, VIP queue-jumping, menu rules) against a running API, so they double
> as executable, always-current documentation of how the app behaves.

## Getting started

Prerequisites: **Docker** (+ Compose) and **uv**.

```bash
make up
```

- API: http://localhost:8000
- **Interactive API docs (all endpoints): http://localhost:8000/docs**
- Postgres is not exposed to the host.

## Commands

```bash
make help     # list every available command
```

Common ones: `make up` / `make down`, `make test`, `make check`, `make e2e`,
`make migrate`.

## Design decisions

- **Patterns:** Repository (data access), Strategy (payment method + bake policy),
  State Machine (order lifecycle), Factory (order → bake tasks). The scheduler is a
  pure function of `(oven state, queue, now)`, kept free of I/O so it stays testable.
- **One engine, one lock.** All oven/queue mutations go through a single in-memory
  engine behind an `asyncio` lock — that's how double-booked trays and lost orders
  are avoided. DB writes happen outside the lock. Trade-off: one process owns the
  queue, so it doesn't scale horizontally yet.
- **Enqueue on payment, not placement.** Unpaid orders never hold an oven; placement
  only returns a provisional estimate.
- **No preemption.** A baking item always finishes; a VIP reorders only the *waiting*
  queue, and everyone behind it gets re-estimated and persisted.
- **Injectable clock** so tests fast-forward time deterministically.
- **Migrations ship in their own PR**, merged before the code that needs the schema.
- Money is `Decimal`; prices are snapshotted onto the order at placement time.

For the reasoning behind each, the PR history walks through the decisions one
feature at a time.
