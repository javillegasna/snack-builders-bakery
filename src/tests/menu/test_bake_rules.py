from decimal import Decimal

from app.menu.models import Category, MenuItem


def test_bake_seconds_per_category() -> None:
    assert Category.COOKIE.bake_seconds == 300
    assert Category.PASTRY.bake_seconds == 600
    assert Category.BREAD.bake_seconds == 1200


def _item(bake_seconds: int | None) -> MenuItem:
    return MenuItem(
        name="X",
        category=Category.COOKIE,
        price=Decimal("1.00"),
        available=True,
        bake_seconds=bake_seconds,
    )


def test_effective_falls_back_to_category() -> None:
    assert _item(None).effective_bake_seconds == Category.COOKIE.bake_seconds


def test_effective_uses_item_override() -> None:
    assert _item(1).effective_bake_seconds == 1
