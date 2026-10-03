"""Unit tests for SlidingWindowRateLimiter."""

from concurrent.futures import ThreadPoolExecutor
import threading
import time
import unittest
from typing import List

from src.rate_limiter import SlidingWindowRateLimiter


class TestSlidingWindowRateLimiter(unittest.TestCase):
    """Test suite covering sliding window, burst allowance, and thread safety."""

    def test_initialization_validation(self) -> None:
        """Validate input arguments during initialization."""
        with self.assertRaises(ValueError):
            SlidingWindowRateLimiter(limit=0, window_seconds=1.0)
        with self.assertRaises(ValueError):
            SlidingWindowRateLimiter(limit=-5, window_seconds=1.0)
        with self.assertRaises(ValueError):
            SlidingWindowRateLimiter(limit=10, window_seconds=0)
        with self.assertRaises(ValueError):
            SlidingWindowRateLimiter(limit=10, window_seconds=-1.0)
        with self.assertRaises(ValueError):
            SlidingWindowRateLimiter(limit=10, window_seconds=1.0, burst_allowance=-1)

        limiter = SlidingWindowRateLimiter(limit=5, window_seconds=2.0, burst_allowance=3)
        self.assertEqual(limiter.limit, 5)
        self.assertEqual(limiter.window_seconds, 2.0)
        self.assertEqual(limiter.burst_allowance, 3)
        self.assertEqual(limiter.max_capacity, 8)

    def test_basic_rate_limiting(self) -> None:
        """Verify requests up to limit are allowed and subsequent requests are rejected."""
        limiter = SlidingWindowRateLimiter(limit=3, window_seconds=10.0, burst_allowance=0)
        self.assertTrue(limiter.allow_request(timestamp=100.0))
        self.assertTrue(limiter.allow_request(timestamp=101.0))
        self.assertTrue(limiter.allow_request(timestamp=102.0))
        self.assertFalse(limiter.allow_request(timestamp=103.0))

    def test_burst_allowance(self) -> None:
        """Verify burst allowance enables requests beyond limit up to limit + burst_allowance."""
        limiter = SlidingWindowRateLimiter(limit=2, window_seconds=10.0, burst_allowance=2)
        # Limit is 2, burst allowance is 2 => max capacity is 4
        self.assertTrue(limiter.allow_request(timestamp=100.0))
        self.assertTrue(limiter.allow_request(timestamp=100.0))
        # Sustained limit reached, burst kicks in:
        self.assertTrue(limiter.allow_request(timestamp=100.0))
        self.assertTrue(limiter.allow_request(timestamp=100.0))
        # Now at capacity (4):
        self.assertFalse(limiter.allow_request(timestamp=100.0))

    def test_sliding_window_expiration(self) -> None:
        """Verify expired requests are purged from the sliding window."""
        limiter = SlidingWindowRateLimiter(limit=2, window_seconds=5.0)
        t0 = 100.0
        self.assertTrue(limiter.allow_request(timestamp=t0))
        self.assertTrue(limiter.allow_request(timestamp=t0 + 1.0))
        self.assertFalse(limiter.allow_request(timestamp=t0 + 2.0))

        # At t0 + 5.0, first request at t0 is expired (t0 <= (t0 + 5.0) - 5.0)
        self.assertTrue(limiter.allow_request(timestamp=t0 + 5.001))
        # Second request at t0 + 1.0 is not yet expired at t0 + 5.001
        self.assertFalse(limiter.allow_request(timestamp=t0 + 5.001))

        # At t0 + 6.001, second request at t0 + 1.0 is also expired
        self.assertTrue(limiter.allow_request(timestamp=t0 + 6.001))

    def test_custom_cost(self) -> None:
        """Verify custom request costs and cost validation."""
        limiter = SlidingWindowRateLimiter(limit=5, window_seconds=10.0)
        with self.assertRaises(ValueError):
            limiter.allow_request(cost=0)
        with self.assertRaises(ValueError):
            limiter.allow_request(cost=-1)

        self.assertTrue(limiter.allow_request(cost=3, timestamp=100.0))
        self.assertEqual(limiter.get_remaining_allowance(timestamp=100.0), 2)
        # Exceeding remaining allowance:
        self.assertFalse(limiter.allow_request(cost=3, timestamp=100.0))
        # Fitting exact remaining allowance:
        self.assertTrue(limiter.allow_request(cost=2, timestamp=100.0))
        self.assertEqual(limiter.get_remaining_allowance(timestamp=100.0), 0)

    def test_key_isolation(self) -> None:
        """Verify independent keys maintain isolated rate limit windows."""
        limiter = SlidingWindowRateLimiter(limit=1, window_seconds=10.0)
        self.assertTrue(limiter.allow_request(key="user_alice", timestamp=100.0))
        self.assertFalse(limiter.allow_request(key="user_alice", timestamp=100.0))

        # Bob should still have full quota
        self.assertTrue(limiter.allow_request(key="user_bob", timestamp=100.0))
        self.assertFalse(limiter.allow_request(key="user_bob", timestamp=100.0))

    def test_reset(self) -> None:
        """Verify resetting a single key or all keys restores allowance."""
        limiter = SlidingWindowRateLimiter(limit=1, window_seconds=10.0)
        limiter.allow_request(key="k1", timestamp=100.0)
        limiter.allow_request(key="k2", timestamp=100.0)
        self.assertFalse(limiter.allow_request(key="k1", timestamp=100.0))
        self.assertFalse(limiter.allow_request(key="k2", timestamp=100.0))

        # Reset specific key
        limiter.reset(key="k1")
        self.assertTrue(limiter.allow_request(key="k1", timestamp=100.0))
        self.assertFalse(limiter.allow_request(key="k2", timestamp=100.0))

        # Reset all keys
        limiter.reset()
        self.assertTrue(limiter.allow_request(key="k1", timestamp=100.0))
        self.assertTrue(limiter.allow_request(key="k2", timestamp=100.0))

    def test_concurrent_thread_safety(self) -> None:
        """Verify thread safety under heavy concurrent access with exact quota admission."""
        limit = 50
        burst = 25
        total_capacity = limit + burst  # 75
        limiter = SlidingWindowRateLimiter(limit=limit, window_seconds=60.0, burst_allowance=burst)

        num_threads = 20
        requests_per_thread = 10  # 200 total attempts
        barrier = threading.Barrier(num_threads)
        results: List[bool] = []
        results_lock = threading.Lock()

        def worker() -> None:
            barrier.wait()  # Align start of all threads for maximum contention
            for _ in range(requests_per_thread):
                allowed = limiter.allow_request(key="concurrent_test")
                with results_lock:
                    results.append(allowed)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 200)
        allowed_count = sum(1 for r in results if r)
        rejected_count = sum(1 for r in results if not r)

        self.assertEqual(allowed_count, total_capacity)
        self.assertEqual(rejected_count, 200 - total_capacity)
        self.assertEqual(limiter.get_remaining_allowance(key="concurrent_test"), 0)


if __name__ == "__main__":
    unittest.main()
