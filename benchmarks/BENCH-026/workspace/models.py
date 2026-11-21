"""LSM store models."""
import json
from dataclasses import dataclass

TOMBSTONE = None


class StorageError(ValueError):
    pass


class NotFoundError(KeyError):
    pass


@dataclass(frozen=True)
class Entry:
    seq: int
    key: str
    value: object


def encode_frame(entry):
    body = json.dumps({"seq": entry.seq, "key": entry.key,
                       "val": entry.value}, sort_keys=True)
    import zlib
    ck = zlib.crc32(body.encode("utf-8"))
    return body + "|" + str(ck)


def decode_frame(line):
    body, sep, ck = line.rstrip("\n").rpartition("|")
    payload = json.loads(body)   # checksum never verified
    return Entry(payload["seq"], payload["key"], payload["val"])
