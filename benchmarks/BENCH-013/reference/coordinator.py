"""Guarded lease operations with fencing-safe release."""
from contextlib import contextmanager

from models import OwnershipError, StaleTokenError


class LockCoordinator:
    def __init__(self, store):
        self.store = store

    @contextmanager
    def hold(self, resource, owner, ttl):
        record = self.store.acquire(resource, owner, ttl)
        try:
            yield record
        finally:
            try:
                self.store.release(resource, owner, record.fencing_token)
            except (KeyError, OwnershipError, StaleTokenError):
                pass
