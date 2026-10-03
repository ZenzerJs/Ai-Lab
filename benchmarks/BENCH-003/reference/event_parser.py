"""
event_parser.py - Backward compatibility shim.
"""
from event_parser import (
    EventRecord,
    ParserError,
    ValidationError,
    UnsupportedEventVersionError,
    parse_event,
    parse_event_stream,
)

__all__ = [
    "EventRecord",
    "ParserError",
    "ValidationError",
    "UnsupportedEventVersionError",
    "parse_event",
    "parse_event_stream",
]
