#!/usr/bin/env python3
"""ACU telemetry validation helpers for Devin API sessions.

Per REVIEW.md integrity rules, Devin ACUs are stored strictly as separate
optional metadata (`acus_consumed`) and are NEVER converted into synthetic
dollar `cost_usd` figures. Runs without direct token/API billing remain at
`cost_status = "unavailable"` and `cost_usd = None`.
"""

import math
from typing import Any, Optional


def validate_acus_consumed(value: Any) -> Optional[float]:
    """Validate and normalize a raw `acus_consumed` value.

    Returns `None` for `None` or `0.0` (unmetered/zero ACUs on completed Devin
    sessions are treated as unavailable rather than free). Raises `ValueError`
    for booleans, non-numeric values, NaN/Inf, or negative numbers.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"acus_consumed must be a number, got bool: {value}")
    try:
        fval = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"acus_consumed must be numeric, got {value!r}") from exc
    if math.isnan(fval) or math.isinf(fval):
        raise ValueError(f"acus_consumed must be finite, got {value!r}")
    if fval < 0.0:
        raise ValueError(f"acus_consumed cannot be negative: {fval}")
    if fval == 0.0:
        return None
    return round(fval, 6)
