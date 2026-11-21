"""RateLimiter: per-subject quota enforcement across window kinds."""
from models import Decision
from bucket import TokenBucket
from windows import FixedWindow, SlidingLog


class RateLimiter:
    """Each quota is enforced per subject; ANY exhausted quota denies."""

    def __init__(self, quotas, clock):
        if not quotas:
            raise ValueError("at least one quota required")
        self.quotas = list(quotas)
        self.clock = clock
        self._windows = {}   # (quota.name, subject) -> counter

    def _counter(self, quota, subject):
        key = (quota.name, subject)
        counter = self._windows.get(key)
        if counter is None:
            if quota.kind == "fixed":
                counter = FixedWindow(quota.window_seconds, self.clock)
            elif quota.kind == "sliding":
                counter = SlidingLog(quota.window_seconds, self.clock)
            else:
                counter = TokenBucket(
                    quota.limit, quota.refill_per_second, self.clock)
            self._windows[key] = counter
        return counter

    def allow(self, subject, n=1):
        """Consume n units per quota and decide. Atomic across quotas:
        a denial consumes nothing."""
        counters = [self._counter(q, subject) for q in self.quotas]
        # Pre-check capacity before mutating anything.
        for quota, counter in zip(self.quotas, counters):
            if isinstance(counter, TokenBucket):
                if counter.tokens < n:
                    return Decision.DENY
            elif counter.count() + n > quota.limit:
                return Decision.DENY
        for quota, counter in zip(self.quotas, counters):
            if isinstance(counter, TokenBucket):
                counter.try_consume(n)
            else:
                counter.add(n)
        return Decision.ALLOW

    def remaining(self, quota_name, subject):
        for quota in self.quotas:
            if quota.name == quota_name:
                counter = self._counter(quota, subject)
                if isinstance(counter, TokenBucket):
                    return max(0, int(counter.tokens))
                return max(0, quota.limit - counter.count())
        raise KeyError(quota_name)
