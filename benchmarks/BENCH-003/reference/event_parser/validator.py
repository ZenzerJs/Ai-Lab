"""
event_parser/validator.py - Validation rules and custom exceptions.
"""
from typing import Any, Dict


class ParserError(Exception):
    """Base parser error."""
    pass


class ValidationError(ParserError):
    """Raised when event schema validation fails."""
    pass


class UnsupportedEventVersionError(ParserError):
    """Raised when event version is not supported."""
    pass


SUPPORTED_VERSIONS = {"1.0", "2.0"}
REQUIRED_FIELDS = {"event_id", "event_type", "version", "timestamp", "payload"}


def validate_raw_event(data: Dict[str, Any]) -> None:
    """Validate dictionary structure according to schema contract."""
    for req in REQUIRED_FIELDS:
        if req not in data or data[req] is None:
            raise ValidationError(f"Missing required field: '{req}'")

    if not isinstance(data["event_id"], str) or not data["event_id"].strip():
        raise ValidationError("event_id must be a non-empty string")

    if not isinstance(data["event_type"], str) or not data["event_type"].strip():
        raise ValidationError("event_type must be a non-empty string")

    version = str(data["version"])
    if version not in SUPPORTED_VERSIONS:
        raise UnsupportedEventVersionError(
            f"Unsupported event version '{version}'. Supported: {sorted(SUPPORTED_VERSIONS)}"
        )

    if not isinstance(data["payload"], dict):
        raise ValidationError("payload must be a JSON dictionary")
