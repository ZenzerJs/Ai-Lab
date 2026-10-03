"""
event_parser/normalizer.py - Normalization helpers.
"""
from typing import Any, Dict
from event_parser.validator import ValidationError


def normalize_timestamp(ts: str) -> str:
    """Normalize and validate timestamp string."""
    if not isinstance(ts, str):
        raise ValidationError("timestamp must be an ISO format string")
    return ts.strip()


def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Preserve Unicode dictionary contents."""
    return dict(payload)
