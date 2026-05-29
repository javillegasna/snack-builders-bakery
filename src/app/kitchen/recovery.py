import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.kitchen.engine import KitchenEngine
from app.menu.repository import MenuRepository
from app.orders.repository import OrderRepository
from app.orders.specs import order_specs


async def recover_orders(engine: KitchenEngine, session: AsyncSession) -> None:
    """Rebuild the kitchen queue from active orders after a restart.

    Re-enqueues every queued/baking order (in-flight bake timers reset) and
    persists the recomputed ETAs.
    """
    orders = OrderRepository(session)
    menu = MenuRepository(session)
    etas: dict[uuid.UUID, datetime] = {}
    for order in await orders.list_active():
        etas = await engine.enqueue(order.id, await order_specs(order, menu))
    if etas:
        await orders.update_estimates(etas)
        await session.commit()
