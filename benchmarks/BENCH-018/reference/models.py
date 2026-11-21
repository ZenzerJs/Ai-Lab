"""Money and journal-leg value types."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import re

CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
CENTS = Decimal("0.01")


def as_decimal(value):
    """Exact Decimal conversion; rejects booleans and non-finite values."""
    if isinstance(value, bool):
        raise ValueError("boolean amount")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("invalid decimal") from exc
    if not result.is_finite():
        raise ValueError("expected finite value")
    return result


def check_currency(code):
    if not isinstance(code, str) or not CURRENCY_RE.match(code):
        raise ValueError(f"invalid currency code: {code!r}")
    return code


def quantize(amount):
    """Round to cents with banker's (half-even) rounding."""
    return as_decimal(amount).quantize(CENTS, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self):
        object.__setattr__(self, "amount", as_decimal(self.amount))
        check_currency(self.currency)

    def add(self, other):
        if self.currency != other.currency:
            raise ValueError("cross-currency addition")
        return Money(quantize(self.amount + other.amount), self.currency)

    def subtract(self, other):
        if self.currency != other.currency:
            raise ValueError("cross-currency subtraction")
        return Money(quantize(self.amount - other.amount), self.currency)

    def negate(self):
        return Money(-self.amount, self.currency)


@dataclass(frozen=True)
class Leg:
    account: str
    money: Money

    def __post_init__(self):
        if not isinstance(self.account, str) or not self.account:
            raise ValueError("account must be a nonempty string")
        if not isinstance(self.money, Money):
            raise ValueError("leg requires a Money value")
