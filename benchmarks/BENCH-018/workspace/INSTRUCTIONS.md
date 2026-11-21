# BENCH-018: Multi-Currency Ledger & FX Reconciliation Engine

Repair only models.py, rates.py, ledger.py, and reconciler.py.
Python stdlib only; no network, sleeps, or paid services.

## API and invariants

- models.as_decimal(value) converts Decimal, integer, string, or float via
  Decimal(str(value)); reject booleans, non-finite or non-decimal values
  with ValueError. Never route through float.
- models.check_currency(code) accepts only /^[A-Z]{3}$/ codes.
- models.quantize(amount) rounds to cents with ROUND_HALF_EVEN (banker's
  rounding): 0.125 -> 0.12, 0.135 -> 0.14, 2.675 -> 2.68.
- models.Money(amount, currency) is frozen; amount normalized via
  as_decimal. add/subtract require equal currencies (else ValueError) and
  quantize the result; negate keeps the currency.
- models.Leg(account, money) is frozen; account nonempty str, money a Money.
- rates.RateTable().set_rate(base, quote, effective_at, rate): distinct
  valid currencies, timezone-aware effective_at, positive finite rate —
  violations raise ValueError.
- rates.rate(base, quote, at): same currency -> Decimal(1); otherwise the
  latest stored rate with effective_at <= at (boundary inclusive); KeyError
  when none qualifies.
- rates.convert(money, target, at): identity returns quantized Money in
  target; otherwise Money(quantize(amount * rate), target).
- ledger.Ledger().post(entry_id, legs): nonempty unique entry_id, at least
  two Leg instances, and per-currency leg sums exactly zero; violations
  raise ValueError without storing. Returns the stored legs tuple.
  entries() yields (entry_id, legs) in posting order; accounts() lists
  distinct accounts in first-use order.
- ledger.balance(account, currency=None): currency -> Money net position
  (zero Money when absent); None -> {currency: Money} sorted by code.
- reconciler.Reconciler(ledger, rates).trial_balance(account, target, at):
  every leg converted at `at` and summed into one quantized Money.
- reconciler.reconcile(expected, at): expected maps (account, currency) ->
  amount, compared against quantized actual balances. Union of keys on
  both sides (missing side = 0). Returns Discrepancy(account, currency,
  expected, actual, difference=actual-expected) sorted by
  (account, currency).

Visible tests are smoke coverage, not the complete specification.
