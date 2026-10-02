"""
event_parser.py - Monolithic legacy implementation for BENCH-003.
BROKEN STATE: Monolithic single file without modular package structure.
"""
from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import Any, Dict, Iterable, List, Union


class ParserError(Exception):
    """Base parser error."""
    pass


class ValidationError(ParserError):
    """Raised when event schema validation fails."""
    pass


class UnsupportedEventVersionError(ParserError):
    """Raised when event version is not supported."""
    pass


@dataclass
class EventRecord:
    event_id: str
    event_type: str
    version: str
    timestamp: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


SUPPORTED_VERSIONS = {"1.0", "2.0"}
REQUIRED_FIELDS = {"event_id", "event_type", "version", "timestamp", "payload"}


def _validate_raw_event(data: Dict[str, Any]) -> None:
    for req in REQUIRED_FIELDS:
        if req not in data or data[req] is None:
            raise ValidationError(f"Missing required field: '{req}'")

    if not isinstance(data["event_id"], str) or not data["event_id"].strip():
        raise ValidationError("event_id must be a non-empty string")

    if not isinstance(data["event_type"], str) or not data["event_type"].strip():
        raise ValidationError("event_type must be a non-empty string")

    version = str(data["version"])
    if version not in SUPPORTED_VERSIONS:
        raise UnsupportedEventVersionError(f"Unsupported event version '{version}'. Supported: {sorted(SUPPORTED_VERSIONS)}")

    if not isinstance(data["payload"], dict):
        raise ValidationError("payload must be a JSON dictionary")


def _normalize_timestamp(ts: str) -> str:
    if not isinstance(ts, str):
        raise ValidationError("timestamp must be an ISO format string")
    return ts.strip()


def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Preserve Unicode keys and values
    return dict(payload)


def parse_event(raw: Union[str, bytes, Dict[str, Any]]) -> EventRecord:
    """Parse single event record from string, bytes, or dictionary."""
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

    _validate_raw_event(data)

    event_id = str(data["event_id"]).strip()
    event_type = str(data["event_type"]).strip()
    version = str(data["version"]).strip()
    timestamp = _normalize_timestamp(data["timestamp"])
    payload = _normalize_payload(data["payload"])
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
    records = []
    for item in stream:
        records.append(parse_event(item))
    return records
