"""Fixed-window and sliding-log counters over an injected clock."""
import bisect


class FixedWindow:
    """Counts events per fixed window [start, start + window_seconds).

    An event at exactly `start + window_seconds` lands in the NEXT window.
    """

    def __init__(self, window_seconds, clock):
        self.window_seconds = window_seconds
        self.clock = clock
        self._buckets = {}

    def _start(self, ts):
        return ts - (ts % self.window_seconds)

    def add(self, n=1):
        start = self._start(self.clock())
        self._buckets[start] = self._buckets.get(start, 0) + n
        return self._buckets[start]

    def count(self):
        return self._buckets.get(self._start(self.clock()), 0)


class SlidingLog:
    """Counts events whose timestamps are strictly inside
    (now - window_seconds, now]."""

    def __init__(self, window_seconds, clock):
        self.window_seconds = window_seconds
        self.clock = clock
        self._times = []

    def add(self, n=1):
        ts = self.clock()
        for _ in range(n):
            bisect.insort(self._times, ts)

    def count(self):
        now = self.clock()
        lo = bisect.bisect_left(self._times, now - self.window_seconds)
        hi = bisect.bisect_right(self._times, now)
        return hi - lo
