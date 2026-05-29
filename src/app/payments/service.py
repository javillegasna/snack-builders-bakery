import uuid

from app.core.clock import Clock
from app.kitchen.engine import KitchenEngine
from app.menu.models import Category
from app.menu.repository import MenuRepository
from app.orders.factory import build_task_specs
from app.orders.models import Order, OrderStatus
from app.orders.repository import OrderRepository
from app.orders.state_machine import assert_transition
from app.payments.models import Payment, PaymentMethod, PaymentStatus
from app.payments.repository import PaymentRepository
from app.payments.strategies import get_strategy


class OrderNotFoundError(Exception):
    """Raised when the order to pay does not exist."""


class PaymentStateError(Exception):
    """Raised when an order is not awaiting payment."""


class PaymentService:
    def __init__(
        self,
        payments: PaymentRepository,
        orders: OrderRepository,
        menu: MenuRepository,
        engine: KitchenEngine,
        clock: Clock,
    ) -> None:
        self._payments = payments
        self._orders = orders
        self._menu = menu
        self._engine = engine
        self._clock = clock

    async def pay(self, order_id: uuid.UUID, method: PaymentMethod) -> Payment:
        order = await self._orders.get(order_id)
        if order is None:
            raise OrderNotFoundError(str(order_id))
        if order.status != OrderStatus.PENDING_PAYMENT:
            raise PaymentStateError(f"order {order_id} is not awaiting payment")

        status = get_strategy(method).charge(order.total_price)
        payment = Payment(
            id=uuid.uuid4(),
            order_id=order.id,
            method=method,
            amount=order.total_price,
            status=status,
            paid_at=self._clock.now(),
        )

        if status is PaymentStatus.CONFIRMED:
            assert_transition(order.status, OrderStatus.QUEUED)
            order.status = OrderStatus.QUEUED
            specs = build_task_specs(order.priority_level, await self._lines(order))
            order.estimated_ready_time = await self._engine.enqueue(order.id, specs)

        return await self._payments.add(payment)

    async def _lines(self, order: Order) -> list[tuple[Category, int]]:
        lines: list[tuple[Category, int]] = []
        for item in order.items:
            menu_item = await self._menu.get(item.menu_item_id)
            if menu_item is None:
                raise PaymentStateError(f"menu item {item.menu_item_id} is gone")
            lines.append((menu_item.category, item.quantity))
        return lines
