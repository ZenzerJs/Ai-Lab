"""Vector clocks for causality tracking across replicas."""


class VectorClock:
    """Immutable node->counter map; merge is elementwise max."""

    def __init__(self, entries=None):
        self.entries = dict(entries or {})

    def increment(self, node: str) -> "VectorClock":
        """Return a new clock with `node`'s counter bumped by one."""
        out = VectorClock(self.entries)
        out.entries[node] = out.entries.get(node, 0) + 1
        return out

    def merge(self, other: "VectorClock") -> "VectorClock":
        """Elementwise max over the union of both clocks' keys."""
        keys = set(self.entries) | set(other.entries)
        return VectorClock({k: max(self.entries.get(k, 0),
                                   other.entries.get(k, 0))
                            for k in keys})

    def compare(self, other: "VectorClock") -> str:
        """'eq' | 'lt' | 'gt' | 'concurrent' partial order."""
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
