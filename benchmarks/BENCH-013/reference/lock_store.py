"""In-memory lease store issuing monotonic fencing tokens."""
import threading

from models import LockConflictError, LockRecord, OwnershipError, StaleTokenError


class LockStore:
    def __init__(self, clock):
        self.clock = clock
        self._locks = {}
        self._next_token = 1
        self._mutex = threading.Lock()

    def _live(self, resource):
        record = self._locks.get(resource)
        if record is not None and record.expires_at <= self.clock.now():
            record = None
        return record

    def _check_ttl(self, ttl):
        if isinstance(ttl, bool) or not isinstance(ttl, int) or ttl <= 0:
            raise ValueError("ttl must be a positive integer")

    def acquire(self, resource, owner, ttl):
        self._check_ttl(ttl)
        with self._mutex:
            if self._live(resource) is not None:
                raise LockConflictError(resource)
            now = self.clock.now()
            record = LockRecord(resource, owner, self._next_token, now, now + ttl)
            self._locks[resource] = record
            self._next_token += 1
            return record

    def _lookup(self, resource, owner, token):
        record = self._live(resource)
        if record is None:
            raise KeyError(resource)
        if record.fencing_token != token:
            raise StaleTokenError(resource)
        if record.owner != owner:
            raise OwnershipError(resource)
        return record

    def renew(self, resource, owner, token, ttl):
        self._check_ttl(ttl)
        record = self._lookup(resource, owner, token)
        renewed = LockRecord(resource, owner, record.fencing_token,
                             record.acquired_at, self.clock.now() + ttl)
        self._locks[resource] = renewed
        return renewed

    def release(self, resource, owner, token):
        self._lookup(resource, owner, token)
        del self._locks[resource]

    def owner(self, resource):
        record = self._live(resource)
        return None if record is None else record.owner
