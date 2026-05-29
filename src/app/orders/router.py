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
from app.orders.schemas import OrderCreate, OrderRead
from app.orders.service import (
    OrderItemError,
    OrderNotFoundError,
    OrderNotReadyError,
    OrderService,
)

router = APIRouter(prefix="/orders", tags=["orders"])


def get_order_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    engine: Annotated[KitchenEngine, Depends(get_engine)],
) -> OrderService:
    return OrderService(
        OrderRepository(session),
        MenuRepository(session),
        engine,
        SystemClock(),
    )


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={422: {"description": "Unknown or unavailable menu item"}},
)
async def place_order(data: OrderCreate, service: OrderServiceDep) -> OrderRead:
    try:
        return OrderRead.model_validate(await service.place_order(data))
    except OrderItemError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from None


@router.get(
    "/{order_id}",
    responses={404: {"description": "Order not found"}},
)
async def get_order(order_id: uuid.UUID, service: OrderServiceDep) -> OrderRead:
    try:
        return OrderRead.model_validate(await service.get_order(order_id))
    except OrderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="order not found"
        ) from None


@router.post(
    "/{order_id}/pickup",
    responses={
        404: {"description": "Order not found"},
        409: {"description": "Order is not ready for pickup"},
    },
)
async def pickup_order(order_id: uuid.UUID, service: OrderServiceDep) -> OrderRead:
    try:
        return OrderRead.model_validate(await service.complete_order(order_id))
    except OrderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="order not found"
        ) from None
    except OrderNotReadyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="order is not ready for pickup",
        ) from None
