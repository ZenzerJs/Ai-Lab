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
    """max_attempts total tries, delay_i = base_delay * multiplier**i."""
    max_attempts: int = 3
    base_delay: float = 0.0
    multiplier: float = 1.0
    retriable: tuple = ()

    def delay(self, retry_index):
        """Delay before retry `retry_index` (0-based)."""
        return self.base_delay * retry_index
