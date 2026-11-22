"""Stream events: (timestamp, key, value)."""


class Event:
    """Immutable-ish record; ts in ms, key groups windows."""

    __slots__ = ("ts", "key", "value")

    def __init__(self, ts, key, value):
        self.ts = ts
        self.key = key
        self.value = value

    def __repr__(self):
        return f"Event(ts={self.ts}, key={self.key!r}, value={self.value!r})"
