"""Memtable."""
from models import Entry, TOMBSTONE


class MemTable:
    def __init__(self):
        self._entries = {}

    def put(self, entry):
        self._entries[entry.key] = entry

    def delete(self, seq, key):
        self.put(Entry(seq, key, TOMBSTONE))

    def get(self, key):
        return self._entries.get(key)

    def __len__(self):
        return len(self._entries)

    def iter_entries(self):
        return list(self._entries.values())   # unordered

    def clear(self):
        self._entries.clear()
