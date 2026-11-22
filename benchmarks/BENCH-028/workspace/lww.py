"""Last-Writer-Wins register ordered by timestamp."""


class LWWRegister:
    def __init__(self, value=None, ts=0, node=""):
        self.value = value
        self.ts = ts
        self.node = node

    def set(self, value, ts, node):
        if ts > self.ts:
            return LWWRegister(value, ts, node)
        return self

    def merge(self, other):
        if other.ts > self.ts:
            return other
        return self
