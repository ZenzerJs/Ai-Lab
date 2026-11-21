"""Ledger-vs-expected reconciliation."""
from dataclasses import dataclass
from decimal import Decimal

from models import Money, as_decimal, check_currency, quantize


@dataclass(frozen=True)
class Discrepancy:
    account: str
    currency: str
    expected: Decimal
    actual: Decimal
    difference: Decimal


class Reconciler:
    def __init__(self, ledger, rates):
        self.ledger = ledger
        self.rates = rates

    def trial_balance(self, account, target, at):
        balances = self.ledger.balance(account)
        total = Decimal(0)
        for money in balances.values():
            total += self.rates.convert(money, target, at).amount
        return Money(total, target)

    def reconcile(self, expected, at):
        discrepancies = []
        for account, currency in sorted(expected):
            want = as_decimal(expected[(account, currency)])
            have = self.ledger.balance(account, currency).amount
            if want != have:
                discrepancies.append(Discrepancy(account, currency, want, have,
                                                 want - have))
        return discrepancies
