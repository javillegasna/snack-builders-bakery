import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import SystemClock
from app.core.db import get_session
from app.kitchen.engine import KitchenEngine
from app.kitchen.router import get_engine
from app.menu.repository import MenuRepository
from app.orders.repository import OrderRepository
from app.payments.repository import PaymentRepository
from app.payments.schemas import PaymentCreate, PaymentRead
from app.payments.service import (
    OrderNotFoundError,
    PaymentService,
    PaymentStateError,
)

router = APIRouter(prefix="/orders", tags=["payments"])


def get_payment_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    engine: Annotated[KitchenEngine, Depends(get_engine)],
) -> PaymentService:
    return PaymentService(
        PaymentRepository(session),
        OrderRepository(session),
        MenuRepository(session),
        engine,
        SystemClock(),
    )


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]


@router.post(
    "/{order_id}/payment",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Order not found"},
        409: {"description": "Order is not awaiting payment"},
    },
)
async def pay_order(
    order_id: uuid.UUID, data: PaymentCreate, service: PaymentServiceDep
) -> PaymentRead:
    try:
        return PaymentRead.model_validate(await service.pay(order_id, data.method))
    except OrderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="order not found"
        ) from None
    except PaymentStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from None
