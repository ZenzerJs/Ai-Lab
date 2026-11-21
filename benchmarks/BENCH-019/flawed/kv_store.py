"""Crash-recoverable key-value store backed by the WAL."""
from pathlib import Path

import wal
from models import Record


class KVStore:
    """In-memory store that mirrors every mutation into its WAL file."""

    def __init__(self, wal_path=None):
        self._data = {}
        self._wal_path = Path(wal_path) if wal_path is not None else None

    def put(self, key, value):
        record = Record("put", key, value)
        if self._wal_path is not None:
            wal.append(self._wal_path, record)
        self._data[key] = value

    def get(self, key):
        """Value bytes for `key`; KeyError when absent or deleted."""
        return self._data[key]

    def delete(self, key):
        if key not in self._data:
            raise KeyError(key)
        if self._wal_path is not None:
            wal.append(self._wal_path, Record("delete", key))
        del self._data[key]

    def keys(self):
        return sorted(self._data)

    def snapshot(self):
        """Independent copy of live key -> value state."""
        return dict(self._data)

    @classmethod
    def recover(cls, wal_path):
        """Rebuild a store by replaying `wal_path` (corrupt tail truncated)."""
        store = cls()
        for record in wal.replay(wal_path):
            if record.op == "put":
                store._data[record.key] = record.value
            else:
                store._data.pop(record.key, None)
        return store
