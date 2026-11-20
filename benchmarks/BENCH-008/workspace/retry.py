"""
retry.py - Broken backoff calculation for BENCH-008.
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
    BROKEN: Accepts negative attempts, omits seeded jitter, and fails to clamp to cap.
    """
    return float(base * (2 ** attempt))
