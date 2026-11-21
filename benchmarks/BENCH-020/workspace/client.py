"""Resilient client: breaker gating, bulkhead isolation, retries."""
import time

from models import CircuitOpen, RetryPolicy


class ResilientClient:
    def __init__(self, breaker, bulkhead, policy=None, clock=None):
        self.breaker = breaker
        self.bulkhead = bulkhead
        self.policy = policy if policy is not None else RetryPolicy()
        self.clock = clock or time.monotonic
        self.delays = []
        self.attempted_at = []

    def call(self, fn, idempotency_key=None):
        last_error = None
        for index in range(self.policy.max_attempts):
            if not self.breaker.allow():
                raise CircuitOpen("breaker open")
            self.attempted_at.append(self.clock())
            try:
                result = self.bulkhead.run(fn)
            except Exception as exc:
                last_error = exc
                self.breaker.on_failure()
                if index + 1 >= self.policy.max_attempts:
                    raise
                self.delays.append(self.policy.delay(index))
            else:
                self.breaker.on_success()
                return result
        raise last_error
