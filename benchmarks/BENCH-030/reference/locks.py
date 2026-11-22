"""Per-key write locks for first-committer-wins serialization."""
import threading


class LockTable:
    """Re-entrant per-key lock ownership by transaction id."""

    def __init__(self):
        self._locks = {}
        self._mu = threading.Lock()

    def acquire(self, key, txn_id: str) -> bool:
        """Take key's write lock for txn_id; False if another live txn
        holds it. Re-acquiring your own lock succeeds."""
        with self._mu:
            holder = self._locks.get(key)
            if holder is None or holder == txn_id:
                self._locks[key] = txn_id
                return True
            return False

    def release(self, key, txn_id: str) -> None:
        with self._mu:
            if self._locks.get(key) == txn_id:
                del self._locks[key]

    def owner(self, key):
        return self._locks.get(key)
