import uuid
from datetime import datetime
from typing import cast

from sqlalchemy import CursorResult, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.orders.models import Order, OrderStatus

_ALLOWED_PREV: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.BAKING: [OrderStatus.QUEUED],
    OrderStatus.READY: [OrderStatus.QUEUED, OrderStatus.BAKING],
}
_TIMESTAMP_FIELD: dict[OrderStatus, str] = {
    OrderStatus.BAKING: "started_baking_at",
    OrderStatus.READY: "ready_at",
}


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, order_id: uuid.UUID) -> Order | None:
        return await self._session.get(Order, order_id)

    async def add(self, order: Order) -> Order:
        self._session.add(order)
        await self._session.commit()
        return order

    async def update_estimates(self, etas: dict[uuid.UUID, datetime]) -> None:
        """Refresh estimated_ready_time for active orders. Caller commits."""
        for order_id, eta in etas.items():
            await self._session.execute(
                update(Order)
                .where(
                    Order.id == order_id,
                    Order.status.in_([OrderStatus.QUEUED, OrderStatus.BAKING]),
                )
                .values(estimated_ready_time=eta)
            )

    async def advance_status(
        self, order_id: uuid.UUID, status: OrderStatus, at: datetime
    ) -> bool:
        """Forward-only status transition with timestamp. Returns True if applied."""
        result = cast(
            "CursorResult[None]",
            await self._session.execute(
                update(Order)
                .where(Order.id == order_id, Order.status.in_(_ALLOWED_PREV[status]))
                .values(status=status, **{_TIMESTAMP_FIELD[status]: at})
            ),
        )
        return result.rowcount > 0
