"""In-memory lease store issuing fencing tokens."""
from models import LockConflictError, LockRecord


class LockStore:
    def __init__(self, clock):
        self.clock = clock
        self._locks = {}

    def acquire(self, resource, owner, ttl):
        if resource in self._locks:
            raise LockConflictError(resource)
        now = self.clock.now()
        record = LockRecord(resource, owner, len(self._locks) + 1, now, now + ttl)
        self._locks[resource] = record
        return record

    def renew(self, resource, owner, token, ttl):
        record = self._locks.get(resource)
        if record is None:
            raise KeyError(resource)
        renewed = LockRecord(resource, owner, record.fencing_token,
                             record.acquired_at, self.clock.now() + ttl)
        self._locks[resource] = renewed
        return renewed

    def release(self, resource, owner, token):
        record = self._locks.get(resource)
        if record is None:
            raise KeyError(resource)
        if record.owner != owner:
            raise PermissionError(resource)
        del self._locks[resource]

    def owner(self, resource):
        record = self._locks.get(resource)
        return None if record is None else record.owner
