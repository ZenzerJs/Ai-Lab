"""Resilient client: breaker gating, bulkhead isolation, idempotent retry."""
import time

from models import CircuitOpen, RetryPolicy


class ResilientClient:
    """call(fn, idempotency_key=None): gated by the breaker and bulkhead,
    retried only when `idempotency_key` is present (idempotent-only retry)
    and only on `policy.retriable` errors. Backoff delays are computed via
    the policy and appended to `.delays`; nothing is ever slept on.
    `.attempted_at` records the injected-clock instant of each attempt."""

    def __init__(self, breaker, bulkhead, policy=None, clock=time.monotonic):
        self.breaker = breaker
        self.bulkhead = bulkhead
        self.policy = policy if policy is not None else RetryPolicy()
        if not callable(clock):
            raise ValueError("clock must be callable")
        self.clock = clock
        self.delays = []
        self.attempted_at = []

    def call(self, fn, idempotency_key=None):
        attempts = self.policy.max_attempts if idempotency_key is not None else 1
        last_error = None
        for index in range(attempts):
            if not self.breaker.allow():
                raise CircuitOpen("breaker open")
            self.attempted_at.append(self.clock())
            try:
                result = self.bulkhead.run(fn)
            except Exception as exc:
                last_error = exc
                self.breaker.on_failure()
                if not isinstance(exc, self.policy.retriable) \
                        or index + 1 >= attempts:
                    raise
                self.delays.append(self.policy.delay(index))
            else:
                self.breaker.on_success()
                return result
        raise last_error
