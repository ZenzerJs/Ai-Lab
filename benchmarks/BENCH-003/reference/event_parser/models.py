"""
event_parser/models.py - Event data models.
"""
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class EventRecord:
    """Parsed and validated event record."""
    event_id: str
    event_type: str
    version: str
    timestamp: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
