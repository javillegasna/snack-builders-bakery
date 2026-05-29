from app.orders.models import OrderStatus

_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING_PAYMENT: frozenset({OrderStatus.QUEUED, OrderStatus.CANCELLED}),
    OrderStatus.QUEUED: frozenset({OrderStatus.BAKING}),
    OrderStatus.BAKING: frozenset({OrderStatus.READY}),
    OrderStatus.READY: frozenset({OrderStatus.COMPLETED}),
    OrderStatus.COMPLETED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


class IllegalTransitionError(Exception):
    """Raised when an order status change is not allowed by the state machine."""


def can_transition(current: OrderStatus, target: OrderStatus) -> bool:
    return target in _TRANSITIONS[current]


def assert_transition(current: OrderStatus, target: OrderStatus) -> None:
    if not can_transition(current, target):
        raise IllegalTransitionError(f"{current} -> {target}")
