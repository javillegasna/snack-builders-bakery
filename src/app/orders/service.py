import uuid
from decimal import Decimal

from app.core.clock import Clock
from app.kitchen.engine import KitchenEngine
from app.menu.models import Category, MenuItem
from app.menu.repository import MenuRepository
from app.orders.factory import build_task_specs
from app.orders.models import Order, OrderItem, OrderStatus
from app.orders.repository import OrderRepository
from app.orders.schemas import OrderCreate


class OrderItemError(Exception):
    """Raised when an order references a missing or unavailable menu item."""


class OrderNotFoundError(Exception):
    """Raised when an order id does not exist."""


class OrderNotReadyError(Exception):
    """Raised when an order cannot be picked up because it is not ready."""


class OrderService:
    def __init__(
        self,
        orders: OrderRepository,
        menu: MenuRepository,
        engine: KitchenEngine,
        clock: Clock,
    ) -> None:
        self._orders = orders
        self._menu = menu
        self._engine = engine
        self._clock = clock

    async def place_order(self, data: OrderCreate) -> Order:
        items: list[OrderItem] = []
        lines: list[tuple[Category, int]] = []
        total = Decimal("0")
        for line in data.items:
            menu_item = await self._require_available(line.menu_item_id)
            items.append(
                OrderItem(
                    menu_item_id=menu_item.id,
                    quantity=line.quantity,
                    unit_price=menu_item.price,
                )
            )
            lines.append((menu_item.category, line.quantity))
            total += menu_item.price * line.quantity

        order = Order(
            id=uuid.uuid4(),
            priority_level=data.priority_level,
            status=OrderStatus.PENDING_PAYMENT,
            total_price=total,
            placed_at=self._clock.now(),
            items=items,
        )
        specs = build_task_specs(data.priority_level, lines)
        order.estimated_ready_time = await self._engine.simulate(order.id, specs)
        return await self._orders.add(order)

    async def get_order(self, order_id: uuid.UUID) -> Order:
        order = await self._orders.get(order_id)
        if order is None:
            raise OrderNotFoundError(str(order_id))
        return order

    async def complete_order(self, order_id: uuid.UUID) -> Order:
        order = await self.get_order(order_id)
        if order.status != OrderStatus.READY:
            raise OrderNotReadyError(str(order_id))
        order.status = OrderStatus.COMPLETED
        order.completed_at = self._clock.now()
        return await self._orders.add(order)

    async def _require_available(self, menu_item_id: uuid.UUID) -> MenuItem:
        menu_item = await self._menu.get(menu_item_id)
        if menu_item is None:
            raise OrderItemError(f"menu item {menu_item_id} not found")
        if not menu_item.available:
            raise OrderItemError(f"menu item {menu_item_id} is unavailable")
        return menu_item
