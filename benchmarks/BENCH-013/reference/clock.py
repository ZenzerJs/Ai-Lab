"""Injectable time source."""
import time


class Clock:
    """Wraps a callable time source; now() returns the current instant."""

    def __init__(self, source=time.monotonic):
        self._source = source

    def now(self):
        value = self._source()
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("clock source must return integer instants")
        return value
