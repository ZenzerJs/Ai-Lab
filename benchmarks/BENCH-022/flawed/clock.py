"""Injectable clocks. All timing flows through a callable."""
import time


def monotonic():
    return time.monotonic


class ManualClock:
    """Deterministic clock driven by .advance()."""

    def __init__(self, value=0.0):
        self.value = value

    def __call__(self):
        return self.value

    def advance(self, seconds):
        if seconds < 0:
            raise ValueError("cannot advance backwards")
        self.value += seconds
