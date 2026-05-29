import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class PaymentMethod(enum.StrEnum):
    CASH = "cash"
    CARD = "card"


class PaymentStatus(enum.StrEnum):
    CONFIRMED = "confirmed"
    FAILED = "failed"


def _enum_values(e: type[enum.StrEnum]) -> list[str]:
    return [m.value for m in e]


class Payment(Base):
    __tablename__ = "payment"
    __table_args__ = (UniqueConstraint("order_id", name="uq_payment_order_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE")
    )
    method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(PaymentMethod, name="payment_method", values_callable=_enum_values)
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status", values_callable=_enum_values)
    )
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
