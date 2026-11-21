"""Multi-leg journal ledger."""
from collections import OrderedDict
from decimal import Decimal

from models import Leg, Money, quantize


class Ledger:
    """Append-only journal."""

    def __init__(self):
        self._entries = OrderedDict()

    def post(self, entry_id, legs):
        """Store a journal entry; returns its legs."""
        if not isinstance(entry_id, str) or not entry_id:
            raise ValueError("entry_id must be a nonempty string")
        legs = tuple(legs)
        if not legs:
            raise ValueError("journal entry requires legs")
        for leg in legs:
            if not isinstance(leg, Leg):
                raise ValueError("legs must be Leg instances")
        self._entries[entry_id] = legs
        return legs

    def entries(self):
        return list(self._entries.items())

    def balance(self, account, currency=None):
        totals = {}
        for legs in self._entries.values():
            for leg in legs:
                if leg.account == account:
                    key = leg.money.currency
                    totals[key] = totals.get(key, Decimal(0)) + leg.money.amount
        if currency is not None:
            return Money(totals.get(currency, Decimal(0)), currency)
        return {code: Money(amount, code) for code, amount in totals.items()}

    def accounts(self):
        seen = []
        for legs in self._entries.values():
            for leg in legs:
                if leg.account not in seen:
                    seen.append(leg.account)
        return seen
