"""Tumbling windows keyed by (key, window_index)."""


def window_of(ts, size):
    """Tumbling window index for ts: floor(ts / size)."""
    return ts // size


def window_bounds(index, size):
    """(start, end) half-open bounds of window `index`."""
    return index * size, index * size + size


class WindowState:
    """Accumulator for one (key, window) pair; wraps an aggregator."""

    def __init__(self, key, index, aggregator):
        self.key = key
        self.index = index
        self.agg = aggregator
        self.fired = False     # trigger already emitted a result

    def add(self, value):
        self.agg.add(value)
