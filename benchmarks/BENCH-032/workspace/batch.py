"""Batched source updates."""


class Batch:
    def __init__(self):
        self.writes = []

    def set(self, source, value):
        self.writes.append((source, value))

    def flush(self, engine):
        for s, v in self.writes:
            s.set(v)
            # BUG: propagates per write — intermediate glitches visible
            engine.propagate()
