"""LSM store models: entries, WAL frames, errors."""
import json
from dataclasses import dataclass

TOMBSTONE = None


class StorageError(ValueError):
    """Corrupt frame, bad checksum, or invalid API use."""


class NotFoundError(KeyError):
    """Key absent or deleted."""


@dataclass(frozen=True)
class Entry:
    seq: int
    key: str
    value: object    # str, or None tombstone


def encode_frame(entry):
    """One WAL line: {"seq":..,"key":..,"val":..,"ck":crc32}."""
    body = json.dumps({"seq": entry.seq, "key": entry.key,
                       "val": entry.value}, sort_keys=True)
    import zlib
    ck = zlib.crc32(body.encode("utf-8"))
    return body + "|" + str(ck)


def decode_frame(line):
    """Parse a WAL line; bad checksums raise StorageError."""
    import zlib
    body, sep, ck = line.rstrip("\n").rpartition("|")
    if not sep:
        raise StorageError("malformed frame")
    if zlib.crc32(body.encode("utf-8")) != int(ck):
        raise StorageError("checksum mismatch")
    payload = json.loads(body)
    return Entry(payload["seq"], payload["key"], payload["val"])
