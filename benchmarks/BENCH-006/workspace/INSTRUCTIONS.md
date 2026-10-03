# BENCH-006: Test Quality Through Faulty Variants

## Assignment
Write a comprehensive pytest unit test suite in `tests/test_accounting.py` to test the token billing helper `compute_token_bill` defined in `accounting_validator.py`.

## Rules & Constraints
1. **DO NOT MODIFY** `accounting_validator.py`. Your job is strictly to author test cases in `tests/test_accounting.py`.
2. Tests must be hermetic and offline. Do not invoke external networks, file systems outside workspace, or provider APIs.
3. Tests must not inspect internal module object IDs or hidden mutation labels.

## Function Specification: `compute_token_bill`

Signature:
```python
compute_token_bill(
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
    rate_card: dict,
) -> dict
```

Behavior & Contract:
- **Input Validation**:
  - `input_tokens`, `output_tokens`, and `cache_read_tokens` must be non-negative integers (`>= 0`).
  - If any count is negative or not an int, raise `ValueError` (e.g. `"{name} must be a non-negative integer"`).
- **Cache Validation**:
  - `cache_read_tokens` must not exceed `input_tokens`.
  - If `cache_read_tokens > input_tokens`, raise `ValueError` (e.g. `"cache_read_tokens cannot exceed input_tokens"`).
- **Rate Card**:
  - `rate_card` must be a dictionary containing keys: `"input_per_million"`, `"output_per_million"`, `"cache_per_million"`.
  - If any key is missing, raise `KeyError`.
- **Calculation**:
  - `billable_uncached_input = input_tokens - cache_read_tokens`
  - `cost_usd = (billable_uncached_input * rate_card["input_per_million"] + cache_read_tokens * rate_card["cache_per_million"] + output_tokens * rate_card["output_per_million"]) / 1_000_000`
  - Returns:
    ```python
    {
        "cost_usd": round(cost_usd, 6),
        "billable_uncached_input": billable_uncached_input,
        "cache_tokens": cache_read_tokens,
        "output_tokens": output_tokens,
    }
    ```
- **Boundary**:
  - `input_tokens=0, output_tokens=0, cache_read_tokens=0` must return `{"cost_usd": 0.0, ...}` without error.
