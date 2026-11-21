"""Circuit breaker with half-open probing."""
import time

from models import State


class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=30.0,
                 half_open_max_probes=1, clock=None):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_probes = half_open_max_probes
        self.clock = clock or time.monotonic
        self._state = State.CLOSED
        self._failures = 0
        self._opened_at = None
        self._probes = 0

    @property
    def state(self):
        if self._state is State.OPEN \
                and self.clock() - self._opened_at >= self.recovery_timeout:
            self._state = State.CLOSED
            self._failures = 0
        return self._state

    def allow(self):
        """True when a call may proceed now."""
        return self.state is not State.OPEN

    def on_success(self):
        self._state = State.CLOSED
        self._failures = 0
        self._opened_at = None
        self._probes = 0

    def on_failure(self):
        if self._state is State.HALF_OPEN:
            self._state = State.CLOSED
            self._failures = 0
            return
        self._failures += 1
        if self._failures > self.failure_threshold:
            self._state = State.OPEN
            self._opened_at = self.clock()
