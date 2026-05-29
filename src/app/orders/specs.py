from app.kitchen.engine import TaskSpec
from app.menu.repository import MenuRepository
from app.orders.factory import build_task_specs
from app.orders.models import Order


class MissingMenuItemError(Exception):
    """A menu item referenced by an order no longer exists."""


async def order_specs(order: Order, menu: MenuRepository) -> list[TaskSpec]:
    """Rebuild bake-task specs from an order's items via current menu bake times."""
    lines: list[tuple[int, int]] = []
    for item in order.items:
        menu_item = await menu.get(item.menu_item_id)
        if menu_item is None:
            raise MissingMenuItemError(str(item.menu_item_id))
        lines.append((menu_item.effective_bake_seconds, item.quantity))
    return build_task_specs(order.priority_level, lines)
