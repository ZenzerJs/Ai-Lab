"""Deterministic ledger-vs-expected reconciliation."""
from dataclasses import dataclass
from decimal import Decimal

from models import Money, as_decimal, check_currency, quantize


@dataclass(frozen=True)
class Discrepancy:
    account: str
    currency: str
    expected: Decimal
    actual: Decimal
    difference: Decimal  # actual - expected


class Reconciler:
    def __init__(self, ledger, rates):
        self.ledger = ledger
        self.rates = rates

    def trial_balance(self, account, target, at):
        """Net position of `account` converted into `target` at `at`."""
        check_currency(target)
        balances = self.ledger.balance(account)
        total = Decimal(0)
        for money in balances.values():
            total += self.rates.convert(money, target, at).amount
        return Money(quantize(total), target)

    def reconcile(self, expected, at):
        """Compare expected {(account, currency): amount} to actual balances.

        Returns Discrepancy records sorted by (account, currency) for every
        key whose expected and actual amounts differ, including keys absent
        on either side (the missing side counts as zero).
        """
        keys = set(expected)
        for legs in self.ledger.entries():
            for leg in legs:
                keys.add((leg.account, leg.money.currency))
        discrepancies = []
        for account, currency in sorted(keys):
            want = quantize(as_decimal(expected.get((account, currency), Decimal(0))))
            have = quantize(self.ledger.balance(account, currency).amount)
            if want != have:
                discrepancies.append(Discrepancy(account, currency, want, have,
                                                 have - want))
        return discrepancies
