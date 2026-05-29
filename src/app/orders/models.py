import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class OrderPriority(enum.StrEnum):
    VIP = "vip"
    APP = "app"
    WALK_IN = "walk_in"


class OrderStatus(enum.StrEnum):
    PENDING_PAYMENT = "pending_payment"
    QUEUED = "queued"
    BAKING = "baking"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


def _enum_values(e: type[enum.StrEnum]) -> list[str]:
    return [m.value for m in e]


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    priority_level: Mapped[OrderPriority] = mapped_column(
        SAEnum(
            OrderPriority,
            name="priority_level",
            values_callable=_enum_values,
        )
    )
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(
            OrderStatus,
            name="order_status",
            values_callable=_enum_values,
        )
    )
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estimated_ready_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_baking_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ready_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderItem(Base):
    __tablename__ = "order_item"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE")
    )
    menu_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("menu_item.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    order: Mapped[Order] = relationship(back_populates="items")
