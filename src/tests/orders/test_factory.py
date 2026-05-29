from app.kitchen.models import PriorityLevel
from app.orders.factory import build_task_specs, to_priority_level
from app.orders.models import OrderPriority


def test_priority_mapping() -> None:
    assert to_priority_level(OrderPriority.VIP) is PriorityLevel.VIP
    assert to_priority_level(OrderPriority.APP) is PriorityLevel.APP
    assert to_priority_level(OrderPriority.WALK_IN) is PriorityLevel.WALK_IN


def test_quantity_expanded_into_one_spec_per_unit() -> None:
    fast, slow = 5, 20
    specs = build_task_specs(OrderPriority.WALK_IN, [(fast, 2), (slow, 1)])
    assert len(specs) == 3
    assert specs == [
        (PriorityLevel.WALK_IN, fast),
        (PriorityLevel.WALK_IN, fast),
        (PriorityLevel.WALK_IN, slow),
    ]


def test_all_specs_carry_order_priority() -> None:
    bake_seconds = 10
    specs = build_task_specs(OrderPriority.VIP, [(bake_seconds, 3)])
    assert all(level is PriorityLevel.VIP for level, _ in specs)
