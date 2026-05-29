import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import FakeClock
from app.kitchen.engine import KitchenEngine
from app.kitchen.models import PriorityLevel
from app.orders.models import Order, OrderPriority, OrderStatus

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
COOKIE = 300


async def _seed_queued_order(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> uuid.UUID:
    order_id = uuid.uuid4()
    async with sessionmaker() as session:
        session.add(
            Order(
                id=order_id,
                priority_level=OrderPriority.WALK_IN,
                status=OrderStatus.QUEUED,
                total_price=Decimal("1.00"),
                placed_at=NOW,
            )
        )
        await session.commit()
    return order_id


async def _status(
    sessionmaker: async_sessionmaker[AsyncSession], order_id: uuid.UUID
) -> Order:
    async with sessionmaker() as session:
        order = await session.get(Order, order_id)
        assert order is not None
        return order


async def test_progression_persists_baking_then_ready(
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    clock = FakeClock(NOW)
    engine = KitchenEngine(clock, session_factory=db_sessionmaker)
    order_id = await _seed_queued_order(db_sessionmaker)

    await engine.enqueue(order_id, [(PriorityLevel.WALK_IN, COOKIE)])
    await engine._reconcile()
    baking = await _status(db_sessionmaker, order_id)
    assert baking.status is OrderStatus.BAKING
    assert baking.started_baking_at == NOW
    assert baking.ready_at is None

    clock.advance(COOKIE)
    await engine._reconcile()
    ready = await _status(db_sessionmaker, order_id)
    assert ready.status is OrderStatus.READY
    assert ready.ready_at is not None
    assert (ready.ready_at - NOW).total_seconds() == COOKIE


async def test_reconcile_waits_for_durable_queued(
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    clock = FakeClock(NOW)
    engine = KitchenEngine(clock, session_factory=db_sessionmaker)
    # order baking in the engine but never persisted as QUEUED in the DB
    order_id = uuid.uuid4()

    await engine.enqueue(order_id, [(PriorityLevel.WALK_IN, COOKIE)])
    await engine._reconcile()
    async with db_sessionmaker() as session:
        assert await session.get(Order, order_id) is None  # guard matched nothing


async def test_no_session_factory_is_noop(
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    clock = FakeClock(NOW)
    engine = KitchenEngine(clock)  # no persistence
    order_id = await _seed_queued_order(db_sessionmaker)

    await engine.enqueue(order_id, [(PriorityLevel.WALK_IN, COOKIE)])
    await engine._reconcile()
    unchanged = await _status(db_sessionmaker, order_id)
    assert unchanged.status is OrderStatus.QUEUED
