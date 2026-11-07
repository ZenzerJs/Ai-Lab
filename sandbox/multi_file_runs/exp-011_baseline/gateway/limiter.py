"""Dual-Strategy API Rate Limiter."""
from collections import defaultdict
import time
from typing import Dict, List, Optional


class SlidingWindowLimiter:
    """Sliding log window rate limiter with burst control."""

    def __init__(self, max_requests: int = 100, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: Dict[str, List[float]] = defaultdict(list)

    def allow(self, tenant_id: str, now: Optional[float] = None) -> bool:
        """Allow request if tenant is strictly within sliding window burst quota."""
        t = now if now is not None else time.time()
        cutoff = t - self.window_seconds
        active = [ts for ts in self._history[tenant_id] if ts >= cutoff]
        self._history[tenant_id] = active

        if len(active) >= self.max_requests:
            return False

        self._history[tenant_id].append(t)
        return True
