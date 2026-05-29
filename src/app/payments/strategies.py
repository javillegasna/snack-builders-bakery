from decimal import Decimal
from typing import Protocol

from app.payments.models import PaymentMethod, PaymentStatus


class PaymentStrategy(Protocol):
    def charge(self, amount: Decimal) -> PaymentStatus: ...


class CashPayment:
    def charge(self, amount: Decimal) -> PaymentStatus:
        return PaymentStatus.CONFIRMED


class CardPayment:
    def charge(self, amount: Decimal) -> PaymentStatus:
        return PaymentStatus.CONFIRMED


_STRATEGIES: dict[PaymentMethod, PaymentStrategy] = {
    PaymentMethod.CASH: CashPayment(),
    PaymentMethod.CARD: CardPayment(),
}


def get_strategy(method: PaymentMethod) -> PaymentStrategy:
    return _STRATEGIES[method]
