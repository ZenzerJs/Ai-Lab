"""Convergent counters: GCounter and PNCounter."""
from vclock import VectorClock


class GCounter:
    def __init__(self, counts=None):
        self.counts = dict(counts or {})

    def increment(self, node, amount=1):
        out = GCounter(self.counts)
        out.counts[node] = out.counts.get(node, 0) + amount
        return out

    @property
    def value(self):
        return sum(self.counts.values())

    def merge(self, other):
        keys = set(self.counts) | set(other.counts)
        return GCounter({k: self.counts.get(k, 0)
                         + other.counts.get(k, 0) for k in keys})


class PNCounter:
    def __init__(self, p=None, n=None):
        self.p = p if p is not None else GCounter()
        self.n = n if n is not None else GCounter()

    def increment(self, node, amount=1):
        return PNCounter(self.p.increment(node, amount), self.n)

    def decrement(self, node, amount=1):
        return PNCounter(self.p, self.n.increment(node, amount))

    @property
    def value(self):
        return self.p.value - self.n.value

    def merge(self, other):
        return PNCounter(self.p.merge(other.p), self.n.merge(other.n))
