import uuid
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.orders.models import Order, OrderStatus


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
