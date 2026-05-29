import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.payments.models import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_order(self, order_id: uuid.UUID) -> Payment | None:
        stmt = select(Payment).where(Payment.order_id == order_id)
        result: Payment | None = await self._session.scalar(stmt)
        return result

    async def add(self, payment: Payment) -> Payment:
        self._session.add(payment)
        await self._session.commit()
        return payment
