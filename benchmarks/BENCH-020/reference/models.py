"""Resilience primitives: breaker states, retry policy, errors."""
from dataclasses import dataclass
from enum import Enum


class State(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class TransientError(Exception):
    """Failure class a retry policy may retry."""


class CircuitOpen(Exception):
    """Raised when the breaker rejects a call while open."""


class BulkheadFull(Exception):
    """Raised when no bulkhead slot is available."""


@dataclass(frozen=True)
class RetryPolicy:
    """max_attempts total tries, delay_i = base_delay * multiplier**i, retriable classes."""
    max_attempts: int = 3
    base_delay: float = 0.0
    multiplier: float = 1.0
    retriable: tuple = (TransientError,)

    def __post_init__(self):
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int) \
                or self.max_attempts < 1:
            raise ValueError("max_attempts must be a positive int")
        if isinstance(self.base_delay, bool) or self.base_delay < 0:
            raise ValueError("base_delay must be nonnegative")
        if isinstance(self.multiplier, bool) or self.multiplier < 1:
            raise ValueError("multiplier must be >= 1")
        if not isinstance(self.retriable, tuple) or not self.retriable \
                or not all(isinstance(cls, type) and issubclass(cls, BaseException)
                           for cls in self.retriable):
            raise ValueError("retriable must be a nonempty tuple of exception classes")

    def delay(self, retry_index):
        """Delay before retry `retry_index` (0-based)."""
        return self.base_delay * (self.multiplier ** retry_index)
