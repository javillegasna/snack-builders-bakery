from decimal import Decimal

import pytest

from app.payments.models import PaymentMethod, PaymentStatus
from app.payments.strategies import CardPayment, CashPayment, get_strategy


@pytest.mark.parametrize("method", list(PaymentMethod))
def test_get_strategy_charges_confirmed(method: PaymentMethod) -> None:
    assert get_strategy(method).charge(Decimal("9.99")) is PaymentStatus.CONFIRMED


def test_strategy_selection() -> None:
    assert isinstance(get_strategy(PaymentMethod.CASH), CashPayment)
    assert isinstance(get_strategy(PaymentMethod.CARD), CardPayment)
