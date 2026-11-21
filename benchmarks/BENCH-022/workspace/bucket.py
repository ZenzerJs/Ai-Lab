"""Token bucket."""
from models import ConfigError


class TokenBucket:
    def __init__(self, capacity, refill_per_second, clock):
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self.clock = clock
        self._tokens = float(capacity)
        self._last = clock()

    @property
    def tokens(self):
        self._refill()
        return self._tokens

    def _refill(self):
        now = self.clock()
        elapsed = now - self._last
        self._tokens += elapsed * self.refill_per_second
        self._last = now

    def try_consume(self, n=1):
        self._refill()
        if self._tokens >= n:
            self._tokens -= n
            return True
        return False
