"""Sliding Window Rate Limiter Module with Burst Allowance and Thread Safety.

This module provides an in-memory sliding window rate limiter implementation
capable of handling burst traffic, multi-key partitioning, and high-concurrency
access safely using threading primitives.
"""

from collections import defaultdict, deque
import threading
import time
from typing import Deque, Dict, Optional, Tuple


class SlidingWindowRateLimiter:
    """An in-memory sliding window rate limiter with burst allowance and thread safety.

    Attributes:
        limit: The sustained maximum number of requests allowed in the sliding window.
        window_seconds: Duration of the sliding window in seconds.
        burst_allowance: Number of extra requests allowed beyond `limit` in a single window.
        max_capacity: The total effective request allowance (limit + burst_allowance).
    """

    def __init__(
        self,
        limit: int,
        window_seconds: float,
        burst_allowance: int = 0,
    ) -> None:
        """Initialize the sliding window rate limiter.

        Args:
            limit: Maximum sustained requests permitted within `window_seconds`. Must be > 0.
            window_seconds: Window duration in seconds. Must be > 0.
            burst_allowance: Extra requests permitted beyond `limit`. Must be >= 0.

        Raises:
            ValueError: If limit <= 0, window_seconds <= 0, or burst_allowance < 0.
        """
        if limit <= 0:
            raise ValueError(f"limit must be positive, got {limit}")
        if window_seconds <= 0:
            raise ValueError(f"window_seconds must be positive, got {window_seconds}")
        if burst_allowance < 0:
            raise ValueError(f"burst_allowance must be non-negative, got {burst_allowance}")

        self.limit: int = limit
        self.window_seconds: float = float(window_seconds)
        self.burst_allowance: int = burst_allowance
        self.max_capacity: int = limit + burst_allowance

        # Internal state: mapping of key -> deque of (timestamp, cost)
        self._windows: Dict[str, Deque[Tuple[float, int]]] = defaultdict(deque)
        # Lock ensuring thread safety across all key checks and mutations
        self._lock: threading.Lock = threading.Lock()

    def _expire(self, key: str, current_time: float) -> None:
        """Remove expired entries outside the sliding window for a given key.

        Note: Must be called while holding self._lock.
        """
        cutoff: float = current_time - self.window_seconds
        queue = self._windows[key]
        while queue and queue[0][0] <= cutoff:
            queue.popleft()

    def allow_request(
        self,
        key: str = "default",
        cost: int = 1,
        timestamp: Optional[float] = None,
    ) -> bool:
        """Check if a request with given cost is allowed under the rate limit.

        If allowed, records the request timestamp and returns True. Otherwise,
        returns False without mutating state.

        Args:
            key: Partition identifier (e.g. user_id, ip_address).
            cost: Number of tokens/requests consumed by this call. Must be > 0.
            timestamp: Optional explicit timestamp (seconds). Uses time.time() if None.

        Returns:
            bool: True if request is allowed, False otherwise.

        Raises:
            ValueError: If cost <= 0.
        """
        if cost <= 0:
            raise ValueError(f"cost must be positive, got {cost}")

        now: float = time.time() if timestamp is None else float(timestamp)

        with self._lock:
            self._expire(key, now)
            queue = self._windows[key]
            current_usage: int = sum(entry[1] for entry in queue)

            if current_usage + cost <= self.max_capacity:
                queue.append((now, cost))
                return True
            return False

    def get_remaining_allowance(
        self,
        key: str = "default",
        timestamp: Optional[float] = None,
    ) -> int:
        """Return the remaining capacity available for the given key in the current window.

        Args:
            key: Partition identifier.
            timestamp: Optional explicit timestamp. Uses time.time() if None.

        Returns:
            int: Remaining units allowed in current window (>= 0).
        """
        now: float = time.time() if timestamp is None else float(timestamp)

        with self._lock:
            self._expire(key, now)
            queue = self._windows[key]
            current_usage: int = sum(entry[1] for entry in queue)
            remaining: int = self.max_capacity - current_usage
            return max(0, remaining)

    def reset(self, key: Optional[str] = None) -> None:
        """Reset the rate limiter history for a given key or all keys.

        Args:
            key: The key to reset. If None, resets all rate limiter history.
        """
        with self._lock:
            if key is None:
                self._windows.clear()
            elif key in self._windows:
                del self._windows[key]
