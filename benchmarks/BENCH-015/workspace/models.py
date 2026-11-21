"""Webhook delivery models and errors."""
from dataclasses import dataclass


class SignatureError(PermissionError):
    """Signature or timestamp verification failed."""


class ConflictError(RuntimeError):
    """Idempotency key replayed with a different payload."""


@dataclass(frozen=True)
class Delivery:
    event_id: str
    payload: bytes
    timestamp: int
    signature: str

    def __post_init__(self):
        if not isinstance(self.event_id, str) or not self.event_id:
            raise ValueError("event_id must be a nonempty string")


@dataclass(frozen=True)
class Receipt:
    event_id: str
    status: str
    digest: str
