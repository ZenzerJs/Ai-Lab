"""Tumbling windows keyed by (key, window_index)."""


def window_of(ts, size):
    # BUG: rounds instead of flooring — events land in the wrong window
    return round(ts / size)


def window_bounds(index, size):
    return index * size, index * size + size


class WindowState:
    def __init__(self, key, index, aggregator):
        self.key = key
        self.index = index
        self.agg = aggregator
        self.fired = False

    def add(self, value):
        self.agg.add(value)
