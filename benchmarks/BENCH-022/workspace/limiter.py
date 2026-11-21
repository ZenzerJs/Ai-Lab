"""RateLimiter."""
from models import Decision
from bucket import TokenBucket
from windows import FixedWindow, SlidingLog


class RateLimiter:
    def __init__(self, quotas, clock):
        self.quotas = list(quotas)
        self.clock = clock
        self._windows = {}

    def _counter(self, quota, subject):
        key = quota.name
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
        decision = Decision.ALLOW
        for quota in self.quotas:
            counter = self._counter(quota, subject)
            if isinstance(counter, TokenBucket):
                if not counter.try_consume(n):
                    decision = Decision.DENY
            elif counter.count() + n > quota.limit:
                decision = Decision.DENY
            else:
                counter.add(n)
        return decision

    def remaining(self, quota_name, subject):
        for quota in self.quotas:
            if quota.name == quota_name:
                counter = self._counter(quota, subject)
                if isinstance(counter, TokenBucket):
                    return int(counter.tokens)
                return quota.limit - counter.count()
        raise KeyError(quota_name)
