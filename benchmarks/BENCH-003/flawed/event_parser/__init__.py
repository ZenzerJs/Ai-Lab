"""
event_parser - Flawed package implementation with regressed error handling.
"""
import json
from typing import Any, Dict, Iterable, List, Union

from event_parser.models import EventRecord
from event_parser.validator import (
    ParserError,
    ValidationError,
    UnsupportedEventVersionError,
    validate_raw_event,
)
from event_parser.normalizer import normalize_timestamp, normalize_payload

__all__ = [
    "EventRecord",
    "ParserError",
    "ValidationError",
    "UnsupportedEventVersionError",
    "parse_event",
    "parse_event_stream",
]


def parse_event(raw: Union[str, bytes, Dict[str, Any]]) -> EventRecord:
    if isinstance(raw, (bytes, bytearray)):
        data = json.loads(raw.decode("utf-8"))
    elif isinstance(raw, str):
        data = json.loads(raw)
    elif isinstance(raw, dict):
        data = dict(raw)
    else:
        raise ValueError("Invalid type")

    # Flawed validation raises ValueError, not ValidationError!
    validate_raw_event(data)

    return EventRecord(
        event_id=str(data["event_id"]),
        event_type=str(data["event_type"]),
        version=str(data["version"]),
        timestamp=normalize_timestamp(data["timestamp"]),
        payload=normalize_payload(data["payload"]),
        metadata=dict(data.get("metadata") or {}),
    )


def parse_event_stream(stream: Iterable[Union[str, bytes, Dict[str, Any]]]) -> List[EventRecord]:
    return [parse_event(x) for x in stream]
