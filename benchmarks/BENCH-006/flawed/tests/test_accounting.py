"""
test_accounting.py - Flawed test suite for BENCH-006.
Only tests standard calculation; omits negative inputs, zero boundaries,
cache bounds, and error propagation. Detects only 1 of 5 faulty variants.
"""
from accounting_validator import compute_token_bill


def test_standard_billing():
    rates = {
        "input_per_million": 2.00,
        "output_per_million": 8.00,
        "cache_per_million": 0.50,
    }
    res = compute_token_bill(1000, 100, 200, rates)
    assert res["cost_usd"] > 0
