"""Concurrency-limiting bulkhead."""
from models import BulkheadFull


class Bulkhead:
    """At most `limit` concurrent in-flight calls."""

    def __init__(self, limit):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive int")
        self.limit = limit
        self._in_flight = 0

    @property
    def in_flight(self):
        return self._in_flight

    def acquire(self):
        """True when a slot was taken; False when full."""
        if self._in_flight >= self.limit:
            return False
        self._in_flight += 1
        return True

    def release(self):
        if self._in_flight <= 0:
            raise ValueError("release without acquire")
        self._in_flight -= 1

    def run(self, fn):
        """Run `fn` under a slot; BulkheadFull when saturated."""
        if not self.acquire():
            raise BulkheadFull("bulkhead saturated")
        try:
            return fn()
        finally:
            self.release()
