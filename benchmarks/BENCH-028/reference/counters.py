"""Convergent counters: GCounter (grow-only) and PNCounter."""
from vclock import VectorClock


class GCounter:
    """Per-node counts; value is the sum; merge is elementwise max."""

    def __init__(self, counts=None):
        self.counts = dict(counts or {})

    def increment(self, node: str, amount: int = 1) -> "GCounter":
        out = GCounter(self.counts)
        out.counts[node] = out.counts.get(node, 0) + amount
        return out

    @property
    def value(self) -> int:
        return sum(self.counts.values())

    def merge(self, other: "GCounter") -> "GCounter":
        keys = set(self.counts) | set(other.counts)
        return GCounter({k: max(self.counts.get(k, 0),
                                other.counts.get(k, 0))
                         for k in keys})


class PNCounter:
    """Counter supporting increments and decrements via two GCounters."""

    def __init__(self, p=None, n=None):
        self.p = p if p is not None else GCounter()
        self.n = n if n is not None else GCounter()

    def increment(self, node: str, amount: int = 1) -> "PNCounter":
        return PNCounter(self.p.increment(node, amount), self.n)

    def decrement(self, node: str, amount: int = 1) -> "PNCounter":
        return PNCounter(self.p, self.n.increment(node, amount))

    @property
    def value(self) -> int:
        return self.p.value - self.n.value

    def merge(self, other: "PNCounter") -> "PNCounter":
        return PNCounter(self.p.merge(other.p), self.n.merge(other.n))
