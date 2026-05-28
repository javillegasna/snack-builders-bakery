import enum
import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Category(enum.StrEnum):
    COOKIE = "cookie"
    PASTRY = "pastry"
    BREAD = "bread"

    @property
    def bake_seconds(self) -> int:
        return _BAKE_SECONDS[self]


_BAKE_SECONDS: dict[Category, int] = {
    Category.COOKIE: 5 * 60,
    Category.PASTRY: 10 * 60,
    Category.BREAD: 20 * 60,
}


class MenuItem(Base):
    __tablename__ = "menu_item"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[Category] = mapped_column(
        SAEnum(
            Category, name="category", values_callable=lambda e: [m.value for m in e]
        )
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    available: Mapped[bool] = mapped_column(Boolean, default=True)
