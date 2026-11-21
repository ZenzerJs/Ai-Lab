"""Append-only write-ahead log."""
from pathlib import Path

from models import Record, encode, scan


def append(path, record):
    """Append one framed record to the WAL at `path`."""
    path = Path(path)
    with open(path, "ab") as handle:
        handle.write(encode(record))


def replay(path):
    """All records from `path`; raises on any malformed frame."""
    path = Path(path)
    if not path.exists():
        return []
    data = path.read_bytes()
    records = []
    for record, _end in scan(data):
        records.append(record)
    return records


def truncate(path):
    """Rewrite `path` keeping every frame; returns record count."""
    path = Path(path)
    if not path.exists():
        return 0
    records = replay(path)
    path.write_bytes(b"".join(encode(record) for record in records))
    return len(records)
