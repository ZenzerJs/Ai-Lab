"""Read/write set tracking."""


class ReadWriteSet:
    def __init__(self):
        self.reads = {}
        self.writes = {}

    def add_read(self, key, version):
        self.reads[key] = version

    def add_write(self, key, value):
        self.writes[key] = value
