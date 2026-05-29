import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.menu.models import Category

_MAX_PRICE = Decimal("99999999.99")
_MAX_BAKE_SECONDS = 86400


def _reject_null_bytes(value: str) -> str:
    if "\x00" in value:
        raise ValueError("must not contain null bytes")
    return value


NameField = Annotated[
    str, Field(min_length=1, max_length=120), AfterValidator(_reject_null_bytes)
]
PriceField = Annotated[
    Decimal,
    Field(
        gt=0,
        le=_MAX_PRICE,
        max_digits=10,
        decimal_places=2,
        json_schema_extra={"multipleOf": 0.01},
    ),
]
BakeSecondsField = Annotated[int, Field(gt=0, le=_MAX_BAKE_SECONDS)]


class MenuItemCreate(BaseModel):
    name: NameField
    category: Category
    price: PriceField
    available: bool = True
    bake_seconds: BakeSecondsField | None = None


class MenuItemUpdate(BaseModel):
    name: NameField | None = None
    category: Category | None = None
    price: PriceField | None = None
    available: bool | None = None
    bake_seconds: BakeSecondsField | None = None


class MenuItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: Category
    price: Decimal
    available: bool
    bake_seconds: int = Field(validation_alias="effective_bake_seconds")
