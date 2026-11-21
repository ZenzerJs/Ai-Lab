"""SSTable files."""
import os
from models import decode_frame, encode_frame


def write_segment(path, entries):
    with open(path, "w") as fh:
        for entry in entries:
            fh.write(encode_frame(entry) + "\n")


def read_segment(path):
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return [decode_frame(line) for line in fh if line.strip()]


def merge_segments(paths, drop_tombstones=True):
    latest = {}
    for path in paths:
        for entry in read_segment(path):
            latest[entry.key] = entry   # last-write wins, not seq
    keys = sorted(latest)
    if drop_tombstones:
        keys = [k for k in keys if latest[k].value is not None]
    return [latest[k] for k in keys]
