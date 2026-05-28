# Snack Builders Bakery — Backend API

A backend for a bakery that sells cookies, pastries and breads. It handles the
storefront (menu), customer orders and payments, and — the interesting part — a
**priority-based kitchen scheduler** that decides what gets baked, when, across a
limited set of ovens.

> Coding exercise. This README is the entry point; deeper design notes live with
> the code as the project grows.

## The problem in one paragraph

The kitchen has **2 ovens × 3 trays = 6 items baking at once**. Orders come in at
three priority tiers (VIP, app/delivery, walk-in). When a tray frees up, the
highest-priority item waiting goes in next — but anything already baking is left
alone (no pulling things out of a hot oven). Each order gets an estimated ready
time the moment it's placed, and when a VIP jumps the line, everyone behind them
sees their estimate pushed back. Bake times depend on the snack: cookies 5 min,
pastries 10 min, breads 20 min.

## Stack

- **FastAPI** (async) + **Pydantic v2**
- **PostgreSQL** + **SQLAlchemy 2.0 (async)** + Alembic
- Pure-Python scheduler core (`heapq`, no framework deps)
- **pytest** for tests, with an injectable clock so we can fast-forward time
- **Docker Compose** for one-command setup, Prometheus + structured logs for visibility

## Architecture

A **modular monolith** organized by feature (vertical slices) rather than by
technical layer — each feature owns its router, service, models and schemas:

```
app/
  core/      # config, db, clock, logging, metrics
  menu/      # browse + manage items
  orders/    # place + track
  payments/  # cash / card
  kitchen/   # the scheduler lives here
```

The scheduler is kept deliberately pure — it never reads the wall clock directly;
time is passed in. That keeps the trickiest logic easy to test and lets the suite
simulate "what happens 20 minutes from now" without waiting 20 minutes.

## Planned endpoints

| Method | Endpoint | Who | What |
|--------|----------|-----|------|
| GET    | `/menu` | anyone | browse available items |
| POST   | `/menu/items` | manager | add an item |
| PATCH  | `/menu/items/{id}` | manager | update an item |
| DELETE | `/menu/items/{id}` | manager | remove an item |
| POST   | `/orders` | customer | place an order → ticket with price + ETA |
| GET    | `/orders/{id}` | customer | track status + ETA |
| POST   | `/orders/{id}/payment` | customer | pay (cash or card) → enters the kitchen queue |
| GET    | `/kitchen/status` | manager | what's in each oven + what's waiting |
| GET    | `/metrics` | ops | Prometheus metrics |
| GET    | `/health` | ops | liveness |

## Key design decisions

- **Scheduling unit is one snack, one tray.** An order of 3 cookies takes 3 trays.
  Maps cleanly to the 6 slots and to "which item is in which oven".
- **Orders enter the queue on payment,** not on placement — so unpaid orders never
  hold up the kitchen. Placement still returns a provisional estimate.
- **No preemption.** A baking item always finishes; VIPs only reorder the *waiting*
  queue. This keeps the model honest and the simulation simple.
- **Estimates are a pure simulation** over the current oven state + queue, so they're
  deterministic and cheap to recompute whenever the queue changes.
- **One scheduler, one lock.** All queue/oven changes go through a single guarded
  path, which is how we avoid double-booked trays and lost orders under load.

## Status

Early development. Building incrementally:

1. Project scaffold + Docker Compose + health check
2. Menu
3. Scheduler core (with tests, no API yet)
4. Orders → provisional ETA
5. Payments → enqueue
6. Kitchen monitoring endpoint
7. VIP dynamic re-estimation
8. Concurrency tests + observability

## Running it

> Coming with the scaffold step.

```bash
docker compose up --build
```
