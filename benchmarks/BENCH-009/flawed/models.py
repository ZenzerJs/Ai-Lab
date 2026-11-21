"""Validated token-bucket state."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


def as_decimal(value):
    try:
        if isinstance(value, bool):
            raise ValueError("boolean amount")
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("invalid decimal") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("expected finite nonnegative value")
    return result


@dataclass
class BucketState:
    capacity: Decimal
    refill_rate: Decimal
    tokens: Decimal
    updated_at: Decimal

    def __post_init__(self):
        for name in ("capacity", "refill_rate", "tokens", "updated_at"):
            setattr(self, name, as_decimal(getattr(self, name)))
        if self.capacity == 0 or self.tokens > self.capacity:
            raise ValueError("invalid capacity or balance")
