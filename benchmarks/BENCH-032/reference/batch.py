"""Batched source updates applied as one propagation wave."""


class Batch:
    """Collect source writes; flush applies them then propagates once."""

    def __init__(self):
        self.writes = []

    def set(self, source, value):
        self.writes.append((source, value))

    def flush(self, engine):
        """Apply writes in order, then propagate a single wave."""
        for s, v in self.writes:
            s.set(v)
            engine.graph.dirty_from(s)
        engine.propagate()
