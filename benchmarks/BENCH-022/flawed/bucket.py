"""Token bucket with lazy refill — delays are computed, never slept."""
from models import ConfigError


class TokenBucket:
    """capacity tokens max; refills at refill_per_second of injected time."""

    def __init__(self, capacity, refill_per_second, clock):
        if isinstance(capacity, bool) or not isinstance(capacity, int) \
                or capacity < 1:
            raise ConfigError("capacity must be a positive int")
        if (not isinstance(refill_per_second, (int, float))
                or isinstance(refill_per_second, bool)
                or refill_per_second <= 0):
            raise ConfigError("refill_per_second must be positive")
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
        if elapsed > 0:
            self._tokens = min(
                float(self.capacity),
                self._tokens + elapsed * self.refill_per_second,
            )
            self._last = now

    def try_consume(self, n=1):
        """True when n tokens were available and consumed."""
        if n < 1:
            raise ConfigError("consume count must be positive")
        self._refill()
        if self._tokens >= n:
            self._tokens -= n
            return True
        return False
