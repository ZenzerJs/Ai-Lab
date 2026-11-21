"""Write-ahead log."""
import os
from models import decode_frame, encode_frame


class WAL:
    def __init__(self, path):
        self.path = path
        self._fh = open(path, "a+")

    def append(self, entry):
        self._fh.write(encode_frame(entry) + "\n")
        self._fh.flush()

    def recover(self):
        self._fh.flush()
        if not os.path.exists(self.path):
            return []
        with open(self.path) as fh:
            return [decode_frame(line) for line in fh if line.strip()]

    def truncate(self):
        self._fh.close()
        open(self.path, "w").close()
        self._fh = open(self.path, "a+")

    def close(self):
        self._fh.close()
