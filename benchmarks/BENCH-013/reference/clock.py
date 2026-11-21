"""Injectable time source."""
import time


class Clock:
    """Wraps a callable time source; now() returns the current instant."""

    def __init__(self, source=None):
        self._source = source if source is not None else (
            lambda: int(time.monotonic()))

    def now(self):
        value = self._source()
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("clock source must return integer instants")
        return value
