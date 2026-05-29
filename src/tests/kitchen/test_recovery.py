import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import FakeClock
from app.kitchen.engine import KitchenEngine
from app.kitchen.recovery import recover_orders
from app.menu.models import Category, MenuItem
from app.orders.models import Order, OrderItem, OrderPriority, OrderStatus

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


async def _seed(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    status: OrderStatus,
    quantity: int = 2,
) -> uuid.UUID:
    order_id = uuid.uuid4()
    async with sessionmaker() as session:
        item = MenuItem(
            name="Recover Cookie",
            category=Category.COOKIE,
            price=Decimal("1.50"),
            available=True,
        )
        session.add(item)
        await session.flush()
        session.add(
            Order(
                id=order_id,
                priority_level=OrderPriority.WALK_IN,
                status=status,
                total_price=Decimal("1.50") * quantity,
                placed_at=NOW,
                items=[
                    OrderItem(
                        menu_item_id=item.id,
                        quantity=quantity,
                        unit_price=Decimal("1.50"),
                    )
                ],
            )
        )
        await session.commit()
    return order_id


async def test_recover_reenqueues_active_order(
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    order_id = await _seed(db_sessionmaker, status=OrderStatus.QUEUED, quantity=2)
    engine = KitchenEngine(FakeClock(NOW), session_factory=db_sessionmaker)

    async with db_sessionmaker() as session:
        await recover_orders(engine, session)

    status = await engine.status()
    busy = [
        tray
        for oven in status.ovens
        for tray in oven.trays
        if tray.order_id == order_id
    ]
    assert len(busy) == 2  # both cookie units back on trays

    async with db_sessionmaker() as session:
        order = await session.get(Order, order_id)
        assert order is not None
        assert order.estimated_ready_time is not None


async def test_recover_skips_terminal_orders(
    db_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    await _seed(db_sessionmaker, status=OrderStatus.COMPLETED)
    await _seed(db_sessionmaker, status=OrderStatus.READY)
    engine = KitchenEngine(FakeClock(NOW), session_factory=db_sessionmaker)

    async with db_sessionmaker() as session:
        await recover_orders(engine, session)

    status = await engine.status()
    busy = [t for oven in status.ovens for t in oven.trays if t.order_id is not None]
    assert busy == []
    assert status.queue == []
