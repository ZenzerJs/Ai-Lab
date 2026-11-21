"""Guarded lease operations."""
from contextlib import contextmanager


class LockCoordinator:
    def __init__(self, store):
        self.store = store

    @contextmanager
    def hold(self, resource, owner, ttl):
        record = self.store.acquire(resource, owner, ttl)
        yield record
        self.store.release(resource, owner, record.fencing_token)
