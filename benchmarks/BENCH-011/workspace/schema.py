"""Versioned event envelopes."""
from dataclasses import dataclass


class ConflictError(ValueError):
    pass


@dataclass
class Event:
    event_type: str
    payload: dict
    schema_version: int = 3
    stream_version: int = 0

    def __post_init__(self):
        if self.event_type != "increment" or not isinstance(self.payload, dict):
            raise ValueError("invalid event")
        if type(self.stream_version) is not int or self.stream_version < 0:
            raise ValueError("invalid stream version")
