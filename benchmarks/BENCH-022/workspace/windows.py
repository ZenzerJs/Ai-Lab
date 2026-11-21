"""Window counters."""
import bisect


class FixedWindow:
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
        return sum(self._buckets.values())


class SlidingLog:
    def __init__(self, window_seconds, clock):
        self.window_seconds = window_seconds
        self.clock = clock
        self._times = []

    def add(self, n=1):
        ts = self.clock()
        for _ in range(n):
            bisect.insort(self._times, ts)

    def count(self):
        cutoff = self.clock() - self.window_seconds
        idx = bisect.bisect_left(self._times, cutoff)
        return len(self._times) - idx
