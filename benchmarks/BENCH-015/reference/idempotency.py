"""Dedupe ledger for delivery idempotency keys."""


class IdempotencyStore:
    NEW = "new"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"

    def __init__(self, clock, ttl_seconds=None):
        self.clock = clock
        if ttl_seconds is not None and (
                isinstance(ttl_seconds, bool)
                or not isinstance(ttl_seconds, (int, float))
                or ttl_seconds <= 0):
            raise ValueError("ttl must be a positive number")
        self.ttl = ttl_seconds
        self._entries = {}

    def _fresh(self, entry):
        return entry is not None and (
            self.ttl is None or self.clock() - entry[1] < self.ttl
        )

    def record(self, key, digest):
        if not isinstance(key, str) or not key:
            raise ValueError("key must be a nonempty string")
        if not isinstance(digest, str) or not digest:
            raise ValueError("digest must be a nonempty string")
        entry = self._entries.get(key)
        if self._fresh(entry):
            return self.DUPLICATE if entry[0] == digest else self.CONFLICT
        self._entries[key] = (digest, self.clock())
        return self.NEW

    def lookup(self, key):
        entry = self._entries.get(key)
        if self._fresh(entry):
            return entry[0]
        self._entries.pop(key, None)
        return None
