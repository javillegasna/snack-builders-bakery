import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.orders.models import OrderPriority, OrderStatus

QuantityField = Annotated[int, Field(gt=0, le=100)]


class OrderItemCreate(BaseModel):
    menu_item_id: uuid.UUID
    quantity: QuantityField


class OrderCreate(BaseModel):
    items: Annotated[list[OrderItemCreate], Field(min_length=1, max_length=50)]
    priority_level: OrderPriority = OrderPriority.WALK_IN


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    menu_item_id: uuid.UUID
    quantity: int
    unit_price: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    priority_level: OrderPriority
    status: OrderStatus
    total_price: Decimal
    placed_at: datetime
    estimated_ready_time: datetime | None
    items: list[OrderItemRead]
