"""Injectable-clock circuit breaker with half-open probing."""
import threading
import time

from models import State


class CircuitBreaker:
    """closed -> open after `failure_threshold` consecutive failures;
    open -> half-open once `recovery_timeout` of injected clock time has
    elapsed; half-open allows at most `half_open_max_probes` concurrent
    probes, closing on success and re-opening on failure."""

    def __init__(self, failure_threshold=3, recovery_timeout=30.0,
                 half_open_max_probes=1, clock=time.monotonic):
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be positive")
        if recovery_timeout < 0:
            raise ValueError("recovery_timeout must be nonnegative")
        if half_open_max_probes < 1:
            raise ValueError("half_open_max_probes must be positive")
        if not callable(clock):
            raise ValueError("clock must be callable")
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_probes = half_open_max_probes
        self.clock = clock
        self._state = State.CLOSED
        self._failures = 0
        self._opened_at = None
        self._probes = 0
        self._lock = threading.RLock()

    @property
    def state(self):
        with self._lock:
            if self._state is State.OPEN \
                    and self.clock() - self._opened_at >= self.recovery_timeout:
                self._state = State.HALF_OPEN
                self._probes = 0
            return self._state

    def allow(self):
        """True when a call may proceed now; consumes a half-open probe slot."""
        with self._lock:
            current = self.state
            if current is State.CLOSED:
                return True
            if current is State.OPEN:
                return False
            if self._probes >= self.half_open_max_probes:
                return False
            self._probes += 1
            return True

    def on_success(self):
        with self._lock:
            self._state = State.CLOSED
            self._failures = 0
            self._opened_at = None
            self._probes = 0

    def on_failure(self):
        with self._lock:
            if self._state is State.HALF_OPEN:
                self._state = State.CLOSED
                self._failures = 0
                self._opened_at = None
                self._probes = 0
                return
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = State.OPEN
                self._opened_at = self.clock()
                self._probes = 0
