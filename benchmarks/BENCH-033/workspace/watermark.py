"""Watermarks: a lower bound on future event times."""


class Watermark:
    def __init__(self, lateness):
        self.lateness = lateness
        self.max_ts = None

    def observe(self, ts):
        # BUG: watermark follows LAST event's ts, not the max —
        # out-of-order events move the watermark backwards
        self.max_ts = ts
        return self.max_ts - self.lateness

    def current(self):
        return None if self.max_ts is None else self.max_ts - self.lateness

    def is_late(self, ts):
        wm = self.current()
        return wm is not None and ts < wm
