"""
event_parser/validator.py - Flawed validation rules.
Regresses error handling by using standard ValueError instead of documented exception classes.
"""
from typing import Any, Dict


class ParserError(Exception):
    pass


class ValidationError(ParserError):
    pass


class UnsupportedEventVersionError(ParserError):
    pass


def validate_raw_event(data: Dict[str, Any]) -> None:
    # FLAW: Raises ValueError instead of ValidationError / UnsupportedEventVersionError
    for req in ("event_id", "event_type", "version", "timestamp", "payload"):
        if req not in data or data[req] is None:
            raise ValueError(f"Missing required field: {req}")

    if data.get("version") not in ("1.0", "2.0"):
        raise ValueError(f"Unsupported version: {data.get('version')}")
