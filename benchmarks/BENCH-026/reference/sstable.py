"""SSTable: immutable sorted segment files on disk."""
import os
from models import decode_frame, encode_frame


def write_segment(path, entries):
    """Entries must be written strictly ordered by key."""
    ordered = sorted(entries, key=lambda e: e.key)
    with open(path, "w") as fh:
        for entry in ordered:
            fh.write(encode_frame(entry) + "\n")


def read_segment(path):
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return [decode_frame(line) for line in fh if line.strip()]


def merge_segments(paths, drop_tombstones=True):
    """Merge segments oldest-first; the highest seq wins per key.
    Tombstones are dropped when drop_tombstones is set."""
    latest = {}
    for path in paths:                     # paths ordered oldest->newest
        for entry in read_segment(path):
            prev = latest.get(entry.key)
            if prev is None or entry.seq > prev.seq:
                latest[entry.key] = entry
    keys = sorted(latest)
    if drop_tombstones:
        keys = [k for k in keys if latest[k].value is not None]
    return [latest[k] for k in keys]
