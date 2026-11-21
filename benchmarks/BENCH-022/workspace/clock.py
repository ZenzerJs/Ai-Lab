"""Clock helpers."""
import time


def monotonic():
    return time.monotonic


class ManualClock:
    def __init__(self, value=0.0):
        self.value = value

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds
