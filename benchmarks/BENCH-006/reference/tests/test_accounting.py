"""
test_accounting.py - Reference test suite for BENCH-006.
Comprehensive unit tests covering standard computation, zero boundary cases,
input validation, cache constraints, and KeyError propagation.
"""
import pytest
from accounting_validator import compute_token_bill


@pytest.fixture
def standard_rates():
    return {
        "input_per_million": 2.50,
        "output_per_million": 10.00,
        "cache_per_million": 0.50,
    }


def test_standard_billing_calculation(standard_rates):
    # 10,000 input, 2,000 cached -> 8,000 uncached input
    # 1,000 output
    # Uncached: 8,000 * 2.50 / 1M = 0.020000
    # Cached:   2,000 * 0.50 / 1M = 0.001000
    # Output:   1,000 * 10.00 / 1M = 0.010000
    # Total:    0.031000
    bill = compute_token_bill(
        input_tokens=10000,
        output_tokens=1000,
        cache_read_tokens=2000,
        rate_card=standard_rates,
    )
    assert bill["cost_usd"] == 0.031
    assert bill["billable_uncached_input"] == 8000
    assert bill["cache_tokens"] == 2000
    assert bill["output_tokens"] == 1000


def test_zero_boundary_case(standard_rates):
    """Detects missing_boundary_case mutant."""
    bill = compute_token_bill(0, 0, 0, standard_rates)
    assert bill["cost_usd"] == 0.0
    assert bill["billable_uncached_input"] == 0
    assert bill["cache_tokens"] == 0
    assert bill["output_tokens"] == 0


def test_negative_input_rejection(standard_rates):
    """Detects removed_validation mutant."""
    with pytest.raises(ValueError, match="must be a non-negative integer"):
        compute_token_bill(-100, 50, 0, standard_rates)

    with pytest.raises(ValueError, match="must be a non-negative integer"):
        compute_token_bill(100, -50, 0, standard_rates)

    with pytest.raises(ValueError, match="must be a non-negative integer"):
        compute_token_bill(100, 50, -10, standard_rates)


def test_cache_bounds_validation(standard_rates):
    """Detects reversed_comparison mutant."""
    # When cache_read_tokens > input_tokens, must raise ValueError
    with pytest.raises(ValueError, match="cannot exceed input_tokens"):
        compute_token_bill(input_tokens=500, output_tokens=100, cache_read_tokens=600, rate_card=standard_rates)

    # When cache_read_tokens <= input_tokens, must NOT raise
    bill = compute_token_bill(input_tokens=500, output_tokens=100, cache_read_tokens=500, rate_card=standard_rates)
    assert bill["billable_uncached_input"] == 0


def test_missing_rate_card_key_raises_keyerror():
    """Detects swallowed_error mutant."""
    incomplete_rates = {"input_per_million": 1.0}
    with pytest.raises(KeyError):
        compute_token_bill(100, 50, 0, incomplete_rates)
