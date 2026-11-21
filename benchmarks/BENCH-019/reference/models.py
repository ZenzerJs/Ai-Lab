"""WAL record model and CRC32 frame codec."""
from dataclasses import dataclass
import zlib

OPS = frozenset({"put", "delete"})
_OP_BYTES = {"put": b"\x01", "delete": b"\x02"}
_BYTE_OPS = {v: k for k, v in _OP_BYTES.items()}
MAX_KEY_BYTES = 1024
MAX_VALUE_BYTES = 1 << 20
HEADER_SIZE = 8  # crc32 (4) + payload length (4), big-endian


@dataclass(frozen=True)
class Record:
    op: str
    key: str
    value: bytes = b""

    def __post_init__(self):
        if self.op not in OPS:
            raise ValueError(f"invalid op: {self.op!r}")
        if not isinstance(self.key, str) or not self.key:
            raise ValueError("key must be a nonempty string")
        if not isinstance(self.value, bytes):
            raise ValueError("value must be bytes")
        if len(self.key.encode("utf-8")) > MAX_KEY_BYTES:
            raise ValueError("key too long")
        if len(self.value) > MAX_VALUE_BYTES:
            raise ValueError("value too long")
        if self.op == "delete" and self.value:
            raise ValueError("delete records carry no value")


def payload_of(record):
    """Deterministic record payload: op | key_len(u16) | key | value_len(u32) | value."""
    key_bytes = record.key.encode("utf-8")
    return (_OP_BYTES[record.op]
            + len(key_bytes).to_bytes(2, "big") + key_bytes
            + len(record.value).to_bytes(4, "big") + record.value)


def encode(record):
    """Frame a record: crc32(payload) | len(payload) | payload."""
    payload = payload_of(record)
    header = zlib.crc32(payload).to_bytes(4, "big") + len(payload).to_bytes(4, "big")
    return header + payload


def decode_payload(payload):
    """Parse a payload back into a Record; ValueError on malformed bytes."""
    if len(payload) < 7:
        raise ValueError("payload too short")
    op = _BYTE_OPS.get(payload[:1])
    if op is None:
        raise ValueError("unknown op byte")
    key_len = int.from_bytes(payload[1:3], "big")
    if len(payload) < 7 + key_len:
        raise ValueError("truncated key")
    key = payload[3:3 + key_len].decode("utf-8")
    value_len = int.from_bytes(payload[3 + key_len:7 + key_len], "big")
    value = payload[7 + key_len:]
    if len(value) != value_len:
        raise ValueError("truncated value")
    return Record(op, key, value)


def scan(data):
    """Yield (record, offset_after) per valid frame; stop at first corruption."""
    pos = 0
    while pos + HEADER_SIZE <= len(data):
        crc = int.from_bytes(data[pos:pos + 4], "big")
        length = int.from_bytes(data[pos + 4:pos + HEADER_SIZE], "big")
        end = pos + HEADER_SIZE + length
        if length <= 0 or end > len(data):
            break
        payload = data[pos + HEADER_SIZE:end]
        if zlib.crc32(payload) != crc:
            break
        try:
            record = decode_payload(payload)
        except ValueError:
            break
        yield record, end
        pos = end
