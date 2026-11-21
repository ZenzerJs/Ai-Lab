"""Effective-dated foreign-exchange rate table."""
from datetime import datetime

from models import Money, as_decimal, check_currency, quantize


class RateTable:
    """Point-in-time FX quotes: (base, quote, effective_at) -> rate."""

    def __init__(self):
        self._quotes = {}

    def set_rate(self, base, quote, effective_at, rate):
        check_currency(base)
        check_currency(quote)
        if base == quote:
            raise ValueError("identity rate is implicit")
        if not isinstance(effective_at, datetime) or effective_at.tzinfo is None:
            raise ValueError("effective_at must be a timezone-aware datetime")
        value = as_decimal(rate)
        if value <= 0:
            raise ValueError("rate must be positive")
        self._quotes.setdefault((base, quote), []).append((effective_at, value))

    def rate(self, base, quote, at):
        """Latest rate effective at or before `at`; KeyError when none."""
        check_currency(base)
        check_currency(quote)
        if base == quote:
            return as_decimal(1)
        candidates = [entry for entry in self._quotes.get((base, quote), ())
                      if entry[0] <= at]
        if not candidates:
            raise KeyError(f"no rate {base}/{quote} at {at!r}")
        return max(candidates, key=lambda entry: entry[0])[1]

    def convert(self, money, target, at):
        """Convert a Money into `target` currency, quantized half-even."""
        check_currency(target)
        if money.currency == target:
            return Money(quantize(money.amount), target)
        return Money(quantize(money.amount * self.rate(money.currency, target, at)),
                     target)
