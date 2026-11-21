"""Append-only checksummed write-ahead log."""
from pathlib import Path

from models import Record, encode, scan


def append(path, record):
    """Append one framed record at the end of `path`'s valid prefix.

    A corrupt or truncated tail is dropped first, so appended records are
    always reachable by replay().
    """
    if not isinstance(record, Record):
        raise ValueError("append requires a Record")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        data = path.read_bytes()
        end = 0
        for _record, frame_end in scan(data):
            end = frame_end
        if end < len(data):
            with open(path, "r+b") as handle:
                handle.truncate(end)
    with open(path, "ab") as handle:
        handle.write(encode(record))


def replay(path):
    """Records from `path` up to the first corrupt or incomplete frame.

    A missing file replays to an empty list; a corrupt tail is truncated:
    bytes at and after the first bad frame are ignored, never surfaced.
    """
    path = Path(path)
    if not path.exists():
        return []
    data = path.read_bytes()
    return [record for record, _end in scan(data)]


def truncate(path):
    """Drop the corrupt tail of `path` in place; returns records kept."""
    path = Path(path)
    if not path.exists():
        return 0
    data = path.read_bytes()
    kept = 0
    end = 0
    for _record, frame_end in scan(data):
        kept += 1
        end = frame_end
    path.write_bytes(data[:end])
    return kept
