"""Dedupe ledger for delivery idempotency keys."""


class IdempotencyStore:
    NEW = "new"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"

    def __init__(self, clock, ttl_seconds=None):
        self.clock = clock
        self.ttl = ttl_seconds
        self._entries = {}

    def record(self, key, digest):
        if key in self._entries:
            return self.DUPLICATE
        self._entries[key] = (digest, self.clock.now())
        return self.NEW

    def lookup(self, key):
        entry = self._entries.get(key)
        return None if entry is None else entry[0]
