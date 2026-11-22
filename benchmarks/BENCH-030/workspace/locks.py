"""Per-key write locks."""
import threading


class LockTable:
    def __init__(self):
        self._locks = {}
        self._mu = threading.Lock()

    def acquire(self, key, txn_id):
        with self._mu:
            holder = self._locks.get(key)
            if holder is None or holder == txn_id:
                self._locks[key] = txn_id
                return True
            return False

    def release(self, key, txn_id):
        with self._mu:
            if self._locks.get(key) == txn_id:
                del self._locks[key]

    def owner(self, key):
        return self._locks.get(key)
