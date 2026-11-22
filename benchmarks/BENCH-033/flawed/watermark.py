"""Watermarks: a lower bound on future event times."""


class Watermark:
    """Tracks max event ts seen; watermark = max_ts - lateness.

    lateness (ms) is how far behind the stream the watermark trails.
    An event with ts <= watermark is 'late' and must be dropped.
    """

    def __init__(self, lateness):
        self.lateness = lateness
        self.max_ts = None

    def observe(self, ts):
        """Update max_ts; return current watermark (None before data)."""
        self.max_ts = ts if self.max_ts is None else \
            max(self.max_ts, ts)
        return self.max_ts - self.lateness

    def current(self):
        return None if self.max_ts is None else self.max_ts - self.lateness

    def is_late(self, ts):
        wm = self.current()
        return wm is not None and ts < wm
