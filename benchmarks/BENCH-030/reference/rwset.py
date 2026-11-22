"""Read/write set tracking for optimistic validation."""


class ReadWriteSet:
    """reads: key -> Version seen; writes: key -> value or TOMBSTONE."""

    def __init__(self):
        self.reads = {}
        self.writes = {}

    def add_read(self, key, version) -> None:
        self.reads[key] = version

    def add_write(self, key, value) -> None:
        self.writes[key] = value
