import uuid
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.kitchen.engine import KitchenEngine
from app.menu.repository import MenuRepository
from app.orders.repository import OrderRepository
from app.orders.specs import MissingMenuItemError, order_specs

_logger = structlog.get_logger()


async def recover_orders(engine: KitchenEngine, session: AsyncSession) -> None:
    """Rebuild the kitchen queue from active orders after a restart.

    Re-enqueues every queued/baking order (in-flight bake timers reset) and
    persists the recomputed ETAs. A connection failure propagates (fail fast on
    boot); an individual unrecoverable order is logged and skipped.
    """
    orders = OrderRepository(session)
    menu = MenuRepository(session)
    etas: dict[uuid.UUID, datetime] = {}
    for order in await orders.list_active():
        try:
            specs = await order_specs(order, menu)
        except MissingMenuItemError as exc:
            _logger.warning(
                "skipping unrecoverable order", order_id=str(order.id), reason=str(exc)
            )
            continue
        etas = await engine.enqueue(order.id, specs)
    if etas:
        await orders.update_estimates(etas)
        await session.commit()
