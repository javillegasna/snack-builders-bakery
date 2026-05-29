from app.kitchen.models import PriorityLevel
from app.menu.models import Category
from app.orders.factory import build_task_specs, to_priority_level
from app.orders.models import OrderPriority


def test_priority_mapping() -> None:
    assert to_priority_level(OrderPriority.VIP) is PriorityLevel.VIP
    assert to_priority_level(OrderPriority.APP) is PriorityLevel.APP
    assert to_priority_level(OrderPriority.WALK_IN) is PriorityLevel.WALK_IN


def test_quantity_expanded_into_one_spec_per_unit() -> None:
    specs = build_task_specs(
        OrderPriority.WALK_IN,
        [(Category.COOKIE, 2), (Category.BREAD, 1)],
    )
    assert len(specs) == 3
    assert specs == [
        (PriorityLevel.WALK_IN, Category.COOKIE.bake_seconds),
        (PriorityLevel.WALK_IN, Category.COOKIE.bake_seconds),
        (PriorityLevel.WALK_IN, Category.BREAD.bake_seconds),
    ]


def test_all_specs_carry_order_priority() -> None:
    specs = build_task_specs(OrderPriority.VIP, [(Category.PASTRY, 3)])
    assert all(level is PriorityLevel.VIP for level, _ in specs)
