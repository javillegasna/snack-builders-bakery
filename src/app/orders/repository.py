import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.orders.models import Order


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, order_id: uuid.UUID) -> Order | None:
        return await self._session.get(Order, order_id)

    async def add(self, order: Order) -> Order:
        self._session.add(order)
        await self._session.commit()
        return order
