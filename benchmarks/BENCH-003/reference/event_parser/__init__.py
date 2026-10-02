"""
event_parser - Modular event parser package.
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
    """Parse a single event record from string, bytes, or dictionary."""
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw_str = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ParserError(f"Failed to decode bytes as UTF-8: {exc}") from exc
        try:
            data = json.loads(raw_str)
        except json.JSONDecodeError as exc:
            raise ParserError(f"Malformed JSON: {exc}") from exc
    elif isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ParserError(f"Malformed JSON: {exc}") from exc
    elif isinstance(raw, dict):
        data = dict(raw)
    else:
        raise ParserError(f"Unsupported event input type: {type(raw)}")

    if not isinstance(data, dict):
        raise ValidationError("Event record must be a JSON object")

    validate_raw_event(data)

    event_id = str(data["event_id"]).strip()
    event_type = str(data["event_type"]).strip()
    version = str(data["version"]).strip()
    timestamp = normalize_timestamp(data["timestamp"])
    payload = normalize_payload(data["payload"])
    metadata = dict(data.get("metadata") or {})

    return EventRecord(
        event_id=event_id,
        event_type=event_type,
        version=version,
        timestamp=timestamp,
        payload=payload,
        metadata=metadata,
    )


def parse_event_stream(stream: Iterable[Union[str, bytes, Dict[str, Any]]]) -> List[EventRecord]:
    """Parse a stream of event records preserving input order."""
    return [parse_event(item) for item in stream]
