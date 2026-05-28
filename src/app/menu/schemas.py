import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.menu.models import Category


class MenuItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: Category
    price: Decimal = Field(gt=0)
    available: bool = True


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: Category | None = None
    price: Decimal | None = Field(default=None, gt=0)
    available: bool | None = None


class MenuItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: Category
    price: Decimal
    available: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def bake_seconds(self) -> int:
        return self.category.bake_seconds
