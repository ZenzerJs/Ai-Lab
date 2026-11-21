"""Memtable: a sorted in-memory buffer keyed by str."""
import bisect
from models import Entry, TOMBSTONE


class MemTable:
    def __init__(self):
        self._keys = []
        self._entries = {}        # key -> Entry

    def put(self, entry):
        if entry.key not in self._entries:
            bisect.insort(self._keys, entry.key)
        self._entries[entry.key] = entry

    def delete(self, seq, key):
        self.put(Entry(seq, key, TOMBSTONE))

    def get(self, key):
        return self._entries.get(key)

    def __len__(self):
        return len(self._keys)

    def iter_entries(self):
        """Entries ordered by key, tombstones included."""
        return [self._entries[k] for k in self._keys]

    def clear(self):
        self._keys.clear()
        self._entries.clear()
