"""Injectable time source."""
import time


class Clock:
    """Wraps a callable time source; now() returns the current instant."""

    def __init__(self, source=time.monotonic):
        self._source = source

    def now(self):
        return int(self._source() or time.monotonic())
