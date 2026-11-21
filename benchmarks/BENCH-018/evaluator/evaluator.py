"""Protected deterministic checks for BENCH-018."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


T0 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
T2 = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)
T3 = datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc)


def run_checks():
    try:
        from models import Leg, Money, as_decimal, quantize
        from rates import RateTable
        from ledger import Ledger
        from reconciler import Discrepancy, Reconciler

        def model_checks():
            assert as_decimal(0.1) == Decimal("0.1")
            assert as_decimal("0.1234567890123456789") == Decimal("0.1234567890123456789")
            for value in (True, "NaN", "Infinity", "-Infinity", None, "bad"):
                rejected(ValueError, lambda: as_decimal(value))
            assert quantize("0.125") == Decimal("0.12")
            assert quantize("0.135") == Decimal("0.14")
            assert quantize("-0.125") == Decimal("-0.12")
            assert quantize("2.675") == Decimal("2.68")  # no float detour
            for code in ("usd", "US", "USDD", "U1D", "", 123):
                rejected(ValueError, lambda: Money(1, code))
            usd = Money("10.005", "USD")
            eur = Money("1", "EUR")
            rejected(ValueError, lambda: usd.add(eur))
            rejected(ValueError, lambda: usd.subtract(eur))
            assert usd.add(Money("0.005", "USD")) == Money("10.01", "USD")
            assert usd.subtract(Money("10.005", "USD")) == Money("0.00", "USD")
            assert usd.negate() == Money("-10.005", "USD")
            rejected(ValueError, lambda: Leg("", usd))
            rejected(ValueError, lambda: Leg("cash", "not money"))
            rejected(ValueError, lambda: Leg(None, usd))

        def rate_checks():
            table = RateTable()
            table.set_rate("USD", "EUR", T1, "0.90")
            table.set_rate("USD", "EUR", T2, "0.95")
            table.set_rate("USD", "EUR", T1 + timedelta(hours=6), "0.92")
            rejected(KeyError, lambda: table.rate("USD", "EUR", T0))
            rejected(KeyError, lambda: table.rate("EUR", "USD", T3))
            rejected(KeyError, lambda: table.rate("USD", "JPY", T3))
            assert table.rate("USD", "USD", T0) == Decimal(1)
            assert table.rate("USD", "EUR", T1) == Decimal("0.90")
            assert table.rate("USD", "EUR", T1 + timedelta(hours=6)) == Decimal("0.92")
            assert table.rate("USD", "EUR", T2) == Decimal("0.95")
            assert table.rate("USD", "EUR", T3) == Decimal("0.95")
            naive = datetime(2026, 1, 1)
            for args in (("USD", "USD", T1, "1"), ("USD", "EUR", naive, "0.9"),
                         ("USD", "EUR", T1, "0"), ("USD", "EUR", T1, "-1"),
                         ("USD", "EUR", T1, "NaN"), ("usd", "EUR", T1, "0.9")):
                rejected(ValueError, lambda: table.set_rate(*args))
            converted = table.convert(Money("100", "USD"), "EUR", T2)
            assert converted == Money("95.00", "EUR")
            assert table.convert(Money("0.125", "USD"), "EUR",
                                 T1) == Money("0.11", "EUR")  # 0.1125 -> 0.11
            assert table.convert(Money("5", "USD"), "USD", T0) == Money("5.00", "USD")
            rejected(KeyError, lambda: table.convert(Money("1", "JPY"), "EUR", T3))

        def ledger_checks():
            ledger = Ledger()
            legs = [Leg("cash", Money("100", "USD")), Leg("revenue", Money("-100", "USD"))]
            assert ledger.post("e1", legs) == tuple(legs)
            multi = [Leg("cash", Money("50", "USD")), Leg("fee", Money("-50", "USD")),
                     Leg("cash", Money("45", "EUR")), Leg("fee", Money("-45", "EUR"))]
            ledger.post("e2", iter(multi))
            rejected(ValueError, lambda: ledger.post("e1",
                         [Leg("a", Money("1", "USD")), Leg("b", Money("-1", "USD"))]))
            rejected(ValueError, lambda: ledger.post("",
                         [Leg("a", Money("1", "USD")), Leg("b", Money("-1", "USD"))]))
            rejected(ValueError, lambda: ledger.post("e3", [Leg("a", Money("0", "USD"))]))
            rejected(ValueError, lambda: ledger.post("e4",
                         [Leg("a", Money("1", "USD")), Leg("b", Money("-2", "USD"))]))
            rejected(ValueError, lambda: ledger.post("e5",
                         [Leg("a", Money("1", "USD")), Leg("b", Money("-1", "EUR"))]))
            rejected(ValueError, lambda: ledger.post("e6", [("a", Money("1", "USD")),
                                                          ("b", Money("-1", "USD"))]))
            assert ledger.balance("cash", "USD") == Money("150.00", "USD")
            assert ledger.balance("cash", "EUR") == Money("45.00", "EUR")
            assert ledger.balance("revenue", "USD") == Money("-100.00", "USD")
            assert ledger.balance("ghost", "USD") == Money("0.00", "USD")
            assert ledger.balance("cash") == {"EUR": Money("45.00", "EUR"),
                                              "USD": Money("150.00", "USD")}
            assert ledger.accounts() == ["cash", "revenue", "fee"]
            assert [entry_id for entry_id, _ in ledger.entries()] == ["e1", "e2"]

        def reconcile_checks():
            table = RateTable()
            table.set_rate("USD", "EUR", T1, "0.50")
            table.set_rate("EUR", "USD", T1, "2.0")
            ledger = Ledger()
            ledger.post("j1", [Leg("cash", Money("200", "USD")),
                               Leg("rev", Money("-200", "USD"))])
            ledger.post("j2", [Leg("cash", Money("30", "EUR")),
                               Leg("rev", Money("-30", "EUR"))])
            rec = Reconciler(ledger, table)
            assert rec.trial_balance("cash", "USD", T2) == Money("260.00", "USD")
            assert rec.trial_balance("cash", "EUR", T2) == Money("130.00", "EUR")
            assert rec.trial_balance("rev", "USD", T2) == Money("-260.00", "USD")
            expected = {("cash", "USD"): "200.00", ("cash", "EUR"): "30.00",
                        ("rev", "USD"): "-200.00", ("rev", "EUR"): "-30.00"}
            assert rec.reconcile(expected, T2) == []
            drift = dict(expected)
            drift[("cash", "USD")] = "199.99"
            drift[("rev", "EUR")] = "-31.00"
            drift[("ghost", "USD")] = "7.50"
            result = rec.reconcile(drift, T2)
            assert result == [
                Discrepancy("cash", "USD", Decimal("199.99"), Decimal("200.00"),
                            Decimal("0.01")),
                Discrepancy("ghost", "USD", Decimal("7.50"), Decimal("0.00"),
                            Decimal("-7.50")),
                Discrepancy("rev", "EUR", Decimal("-31.00"), Decimal("-30.00"),
                            Decimal("1.00")),
            ]
            ledger.post("j3", [Leg("new", Money("5", "USD")),
                               Leg("rev", Money("-5", "USD"))])
            result = rec.reconcile(expected, T2)
            assert [(d.account, d.currency) for d in result] == [
                ("new", "USD"), ("rev", "USD")]
            assert result[0].difference == Decimal("5.00")
            assert result[1].difference == Decimal("-5.00")

        for check in (model_checks, rate_checks, ledger_checks, reconcile_checks):
            try:
                check()
            except Exception as exc:
                fail(f"{check.__name__}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        fail(f"import_error: {exc}")
    print("ALL CHECKS PASSED")


def fail(detail):
    print("REASON: ledger_fx_invariant_violation", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
