"""Vector clocks for causality tracking."""


class VectorClock:
    def __init__(self, entries=None):
        self.entries = dict(entries or {})

    def increment(self, node):
        out = VectorClock(self.entries)
        out.entries[node] = out.entries.get(node, 0) + 1
        return out

    def merge(self, other):
        keys = set(self.entries) | set(other.entries)
        return VectorClock({k: min(self.entries.get(k, 0),
                                   other.entries.get(k, 0))
                            for k in keys})

    def compare(self, other):
        keys = set(self.entries) | set(other.entries)
        le = all(self.entries.get(k, 0) <= other.entries.get(k, 0)
                 for k in keys)
        ge = all(self.entries.get(k, 0) >= other.entries.get(k, 0)
                 for k in keys)
        if le and ge:
            return "eq"
        if le:
            return "lt"
        if ge:
            return "gt"
        return "concurrent"

    def __eq__(self, other):
        return self.entries == other.entries
