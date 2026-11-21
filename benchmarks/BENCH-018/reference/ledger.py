"""Balanced multi-leg journal ledger."""
from collections import OrderedDict
from decimal import Decimal

from models import Leg, Money, quantize


class Ledger:
    """Append-only journal; entries must balance per currency."""

    def __init__(self):
        self._entries = OrderedDict()

    def post(self, entry_id, legs):
        """Validate and store a balanced journal entry; returns its legs."""
        if not isinstance(entry_id, str) or not entry_id:
            raise ValueError("entry_id must be a nonempty string")
        if entry_id in self._entries:
            raise ValueError(f"duplicate entry_id: {entry_id!r}")
        legs = tuple(legs)
        if len(legs) < 2:
            raise ValueError("journal entry requires at least two legs")
        totals = {}
        for leg in legs:
            if not isinstance(leg, Leg):
                raise ValueError("legs must be Leg instances")
            totals[leg.money.currency] = totals.get(leg.money.currency,
                                                    Decimal(0)) + leg.money.amount
        if any(total != 0 for total in totals.values()):
            raise ValueError("journal entry is not balanced")
        self._entries[entry_id] = legs
        return legs

    def entries(self):
        """(entry_id, legs) pairs in posting order."""
        return list(self._entries.items())

    def balance(self, account, currency=None):
        """Money or {currency: Money} holding the account's net position."""
        totals = {}
        for legs in self._entries.values():
            for leg in legs:
                if leg.account == account:
                    key = leg.money.currency
                    totals[key] = totals.get(key, Decimal(0)) + leg.money.amount
        if currency is not None:
            return Money(quantize(totals.get(currency, Decimal(0))), currency)
        return {code: Money(quantize(amount), code)
                for code, amount in sorted(totals.items())}

    def accounts(self):
        seen = []
        for legs in self._entries.values():
            for leg in legs:
                if leg.account not in seen:
                    seen.append(leg.account)
        return seen
