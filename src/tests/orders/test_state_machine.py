import pytest

from app.orders.models import OrderStatus
from app.orders.state_machine import (
    IllegalTransitionError,
    assert_transition,
    can_transition,
)

LEGAL = [
    (OrderStatus.PENDING_PAYMENT, OrderStatus.QUEUED),
    (OrderStatus.PENDING_PAYMENT, OrderStatus.CANCELLED),
    (OrderStatus.QUEUED, OrderStatus.BAKING),
    (OrderStatus.BAKING, OrderStatus.READY),
    (OrderStatus.READY, OrderStatus.COMPLETED),
]

ILLEGAL = [
    (OrderStatus.PENDING_PAYMENT, OrderStatus.BAKING),
    (OrderStatus.QUEUED, OrderStatus.CANCELLED),
    (OrderStatus.BAKING, OrderStatus.COMPLETED),
    (OrderStatus.COMPLETED, OrderStatus.READY),
    (OrderStatus.CANCELLED, OrderStatus.QUEUED),
]


@pytest.mark.parametrize(("current", "target"), LEGAL)
def test_legal_transitions_allowed(current: OrderStatus, target: OrderStatus) -> None:
    assert can_transition(current, target)
    assert_transition(current, target)


@pytest.mark.parametrize(("current", "target"), ILLEGAL)
def test_illegal_transitions_rejected(
    current: OrderStatus, target: OrderStatus
) -> None:
    assert not can_transition(current, target)
    with pytest.raises(IllegalTransitionError):
        assert_transition(current, target)


def test_terminal_states_have_no_exits() -> None:
    for terminal in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
        assert all(not can_transition(terminal, target) for target in OrderStatus)
