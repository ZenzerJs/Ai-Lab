"""
retry.py - Reference seeded full-jitter exponential backoff for BENCH-008.
"""
import random
from typing import Optional


def compute_backoff(
    attempt: int,
    base: float = 0.1,
    cap: float = 5.0,
    rng: Optional[random.Random] = None,
) -> float:
    """
    Compute deterministic seeded full-jitter exponential backoff clamped to [0.0, cap].
    """
    if isinstance(attempt, bool) or not isinstance(attempt, int):
        raise ValueError("attempt must be an integer")
    if attempt < 0:
        raise ValueError(f"attempt must be >= 0, got {attempt}")
    if base < 0:
        raise ValueError(f"base must be >= 0, got {base}")
    if cap < 0:
        raise ValueError(f"cap must be >= 0, got {cap}")

    if base == 0.0 or cap == 0.0:
        return 0.0

    try:
        raw = float(base) * (2.0 ** attempt)
    except OverflowError:
        raw = float(cap)

    upper = min(float(cap), raw)
    generator = rng if rng is not None else random.Random()
    delay = float(generator.uniform(0.0, upper))
    return min(float(cap), max(0.0, delay))
