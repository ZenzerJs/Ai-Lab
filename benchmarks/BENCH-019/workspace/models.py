"""WAL record model and frame codec."""
from dataclasses import dataclass

OPS = frozenset({"put", "delete"})
_OP_BYTES = {"put": b"\x01", "delete": b"\x02"}
_BYTE_OPS = {v: k for k, v in _OP_BYTES.items()}
HEADER_SIZE = 4  # payload length only


@dataclass(frozen=True)
class Record:
    op: str
    key: str
    value: bytes = b""


def payload_of(record):
    """Record payload: op | key_len(u16) | key | value_len(u32) | value."""
    key_bytes = record.key.encode("utf-8")
    return (_OP_BYTES[record.op]
            + len(key_bytes).to_bytes(2, "big") + key_bytes
            + len(record.value).to_bytes(4, "big") + record.value)


def encode(record):
    """Frame a record: len(payload) | payload."""
    payload = payload_of(record)
    return len(payload).to_bytes(4, "big") + payload


def decode_payload(payload):
    """Parse a payload back into a Record."""
    if len(payload) < 7:
        raise ValueError("payload too short")
    op = _BYTE_OPS.get(payload[:1])
    if op is None:
        raise ValueError("unknown op byte")
    key_len = int.from_bytes(payload[1:3], "big")
    key = payload[3:3 + key_len].decode("utf-8")
    value_len = int.from_bytes(payload[3 + key_len:7 + key_len], "big")
    value = payload[7 + key_len:]
    return Record(op, key, value)


def scan(data):
    """Yield (record, offset_after) per frame."""
    pos = 0
    while pos + HEADER_SIZE <= len(data):
        length = int.from_bytes(data[pos:pos + HEADER_SIZE], "big")
        end = pos + HEADER_SIZE + length
        if end > len(data):
            break
        payload = data[pos + HEADER_SIZE:end]
        yield decode_payload(payload), end
        pos = end
