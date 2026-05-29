from app.kitchen.engine import TaskSpec
from app.kitchen.models import PriorityLevel
from app.orders.models import OrderPriority

_PRIORITY_MAP: dict[OrderPriority, PriorityLevel] = {
    OrderPriority.VIP: PriorityLevel.VIP,
    OrderPriority.APP: PriorityLevel.APP,
    OrderPriority.WALK_IN: PriorityLevel.WALK_IN,
}


def to_priority_level(priority: OrderPriority) -> PriorityLevel:
    return _PRIORITY_MAP[priority]


def build_task_specs(
    priority: OrderPriority, lines: list[tuple[int, int]]
) -> list[TaskSpec]:
    """One bake task per snack unit (quantity expanded), all at the order priority.

    Each line is ``(bake_seconds, quantity)``.
    """
    level = to_priority_level(priority)
    return [
        (level, bake_seconds)
        for bake_seconds, quantity in lines
        for _ in range(quantity)
    ]
