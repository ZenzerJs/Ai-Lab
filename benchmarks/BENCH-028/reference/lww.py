"""Last-Writer-Wins register with deterministic (ts, node) ordering."""


class LWWRegister:
    """Register resolving concurrent writes by (timestamp, node) max.

    The node id is a strict tiebreak so equal timestamps still converge
    to the same winner on every replica regardless of merge order.
    """

    def __init__(self, value=None, ts: int = 0, node: str = ""):
        self.value = value
        self.ts = ts
        self.node = node

    def set(self, value, ts: int, node: str) -> "LWWRegister":
        """Write only wins when (ts, node) exceeds the current stamp."""
        if (ts, node) > (self.ts, self.node):
            return LWWRegister(value, ts, node)
        return self

    def merge(self, other: "LWWRegister") -> "LWWRegister":
        if (other.ts, other.node) > (self.ts, self.node):
            return other
        return self
