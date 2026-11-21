from datetime import datetime, timezone

from models import Leg, Money
from rates import RateTable
from ledger import Ledger


def test_money_smoke():
    cash = Money("10.00", "USD")
    assert cash.add(Money("2.50", "USD")) == Money("12.50", "USD")


def test_ledger_smoke():
    ledger = Ledger()
    ledger.post("e1", [Leg("cash", Money("5", "USD")), Leg("rev", Money("-5", "USD"))])
    assert ledger.balance("cash", "USD") == Money("5.00", "USD")
    table = RateTable()
    table.set_rate("USD", "EUR", datetime(2026, 1, 1, tzinfo=timezone.utc), "0.5")
    assert table.convert(Money("10", "USD"), "EUR",
                         datetime(2026, 2, 1, tzinfo=timezone.utc)) == Money("5.00", "EUR")
