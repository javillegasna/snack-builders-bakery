from app.menu.models import Category


def test_bake_seconds_per_category() -> None:
    assert Category.COOKIE.bake_seconds == 300
    assert Category.PASTRY.bake_seconds == 600
    assert Category.BREAD.bake_seconds == 1200
