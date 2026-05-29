import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.clock import FakeClock
from app.kitchen.engine import KitchenEngine
from app.kitchen.models import PriorityLevel
from app.main import app

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
COOKIE = 300


def make_engine() -> KitchenEngine:
    return KitchenEngine(FakeClock(NOW))


async def test_enqueue_fills_slots_and_returns_eta() -> None:
    engine = make_engine()
    order_id = uuid.uuid4()
    specs = [(PriorityLevel.WALK_IN, COOKIE)] * 7
    etas = await engine.enqueue(order_id, specs)
    eta = etas.get(order_id)
    assert eta is not None
    assert (eta - NOW).total_seconds() == 2 * COOKIE
    status = await engine.status()
    busy = [t for oven in status.ovens for t in oven.trays if t.order_id is not None]
    assert len(busy) == 6
    assert len(status.queue) == 1


async def test_status_shape_when_empty() -> None:
    status = await make_engine().status()
    assert len(status.ovens) == 2
    assert all(len(oven.trays) == 3 for oven in status.ovens)
    assert all(t.order_id is None for oven in status.ovens for t in oven.trays)
    assert status.queue == []


async def test_next_finish_tracks_earliest_baking_slot() -> None:
    engine = make_engine()
    assert engine._next_finish() is None
    await engine.enqueue(uuid.uuid4(), [(PriorityLevel.WALK_IN, COOKIE)])
    next_finish = engine._next_finish()
    assert next_finish is not None
    assert (next_finish - NOW).total_seconds() == COOKIE


async def test_remaining_seconds_reported() -> None:
    engine = make_engine()
    await engine.enqueue(uuid.uuid4(), [(PriorityLevel.WALK_IN, COOKIE)])
    status = await engine.status()
    busy = [t for oven in status.ovens for t in oven.trays if t.order_id is not None]
    assert busy[0].remaining_seconds == COOKIE


def test_kitchen_status_endpoint() -> None:
    with TestClient(app) as client:
        resp = client.get("/kitchen/status")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["ovens"]) == 2
    assert all(len(oven["trays"]) == 3 for oven in body["ovens"])
    assert body["queue"] == []
