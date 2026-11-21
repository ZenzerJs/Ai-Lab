"""Crash-recoverable key-value store backed by the WAL."""
from pathlib import Path

import wal
from models import Record


class KVStore:
    """In-memory store that mirrors mutations into its WAL file."""

    def __init__(self, wal_path=None):
        self._data = {}
        self._wal_path = Path(wal_path) if wal_path is not None else None

    def put(self, key, value):
        if self._wal_path is not None:
            wal.append(self._wal_path, Record("put", key, value))
        self._data[key] = value

    def get(self, key):
        """Value bytes for `key`, or None when absent."""
        return self._data.get(key)

    def delete(self, key):
        if self._wal_path is not None:
            wal.append(self._wal_path, Record("delete", key))
        self._data.pop(key, None)

    def keys(self):
        return sorted(self._data)

    def snapshot(self):
        """Live key -> value state."""
        return self._data

    @classmethod
    def recover(cls, wal_path):
        """Rebuild a store by replaying `wal_path`."""
        store = cls()
        for record in wal.replay(wal_path):
            if record.op == "put":
                store._data[record.key] = record.value
        return store
