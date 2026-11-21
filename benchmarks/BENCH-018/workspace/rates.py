"""Foreign-exchange rate table."""
from datetime import datetime

from models import Money, as_decimal, check_currency


class RateTable:
    """Point-in-time FX quotes: (base, quote, effective_at) -> rate."""

    def __init__(self):
        self._quotes = {}

    def set_rate(self, base, quote, effective_at, rate):
        check_currency(base)
        check_currency(quote)
        value = as_decimal(rate)
        self._quotes.setdefault((base, quote), []).append((effective_at, value))

    def rate(self, base, quote, at):
        """Latest rate for the pair; KeyError when none exist."""
        check_currency(base)
        check_currency(quote)
        if base == quote:
            return as_decimal(1)
        entries = self._quotes.get((base, quote), ())
        if not entries:
            raise KeyError(f"no rate {base}/{quote}")
        return max(entries, key=lambda entry: entry[0])[1]

    def convert(self, money, target, at):
        """Convert a Money into `target` currency."""
        check_currency(target)
        if money.currency == target:
            return money
        return Money(money.amount * self.rate(money.currency, target, at), target)
