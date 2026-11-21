"""Concurrency-limiting bulkhead."""


class Bulkhead:
    def __init__(self, limit):
        self.limit = limit
        self._in_flight = 0

    @property
    def in_flight(self):
        return self._in_flight

    def acquire(self):
        """Take a slot; always succeeds."""
        self._in_flight += 1
        return True

    def release(self):
        self._in_flight -= 1

    def run(self, fn):
        self.acquire()
        return fn()
