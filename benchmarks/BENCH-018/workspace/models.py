"""Money and journal-leg value types."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re

CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
CENTS = Decimal("0.01")


def as_decimal(value):
    """Decimal conversion."""
    try:
        if isinstance(value, bool):
            raise ValueError("boolean amount")
        result = Decimal(str(float(value)))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("invalid decimal") from exc
    if not result.is_finite():
        raise ValueError("expected finite value")
    return result


def check_currency(code):
    if not isinstance(code, str) or not code:
        raise ValueError(f"invalid currency code: {code!r}")
    return code


def quantize(amount):
    """Round to cents."""
    return as_decimal(amount).quantize(CENTS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self):
        object.__setattr__(self, "amount", as_decimal(self.amount))
        check_currency(self.currency)

    def add(self, other):
        return Money(quantize(self.amount + other.amount), self.currency)

    def subtract(self, other):
        return Money(quantize(self.amount - other.amount), self.currency)

    def negate(self):
        return Money(-self.amount, self.currency)


@dataclass(frozen=True)
class Leg:
    account: str
    money: Money
