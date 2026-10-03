"""
event_parser/normalizer.py - Normalization helpers.
"""
from typing import Any, Dict


def normalize_timestamp(ts: str) -> str:
    return str(ts).strip()


def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return dict(payload)
