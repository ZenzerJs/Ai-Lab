"""
accounting_validator.py - Token billing calculation helper.
GENUINE IMPLEMENTATION: Adheres to all specification contracts.
DO NOT MODIFY THIS FILE.
"""
from typing import Any, Dict


def compute_token_bill(
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
    rate_card: Dict[str, float],
) -> Dict[str, Any]:
    """Compute token billing and validate token counters."""
    # 1. Non-negative integer checks
    for name, val in (
        ("input_tokens", input_tokens),
        ("output_tokens", output_tokens),
        ("cache_read_tokens", cache_read_tokens),
    ):
        if not isinstance(val, int) or isinstance(val, bool) or val < 0:
            raise ValueError(f"{name} must be a non-negative integer, got {val!r}")

    # 2. Cache bounds check
    if cache_read_tokens > input_tokens:
        raise ValueError(
            f"cache_read_tokens ({cache_read_tokens}) cannot exceed input_tokens ({input_tokens})"
        )

    # 3. Rate card keys
    required_keys = ("input_per_million", "output_per_million", "cache_per_million")
    for req in required_keys:
        if req not in rate_card:
            raise KeyError(f"Missing required rate_card key: '{req}'")

    # 4. Calculation
    uncached_input = input_tokens - cache_read_tokens
    cost = (
        uncached_input * rate_card["input_per_million"]
        + cache_read_tokens * rate_card["cache_per_million"]
        + output_tokens * rate_card["output_per_million"]
    ) / 1_000_000.0

    return {
        "cost_usd": round(cost, 6),
        "billable_uncached_input": uncached_input,
        "cache_tokens": cache_read_tokens,
        "output_tokens": output_tokens,
    }
