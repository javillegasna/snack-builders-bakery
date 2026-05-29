import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.payments.models import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    method: PaymentMethod


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    method: PaymentMethod
    amount: Decimal
    status: PaymentStatus
    paid_at: datetime
