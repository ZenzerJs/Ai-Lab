"""Lease record model and lock errors."""
from dataclasses import dataclass


class LockConflictError(RuntimeError):
    """Resource is already leased under a live lock."""


class StaleTokenError(ValueError):
    """Presented fencing token does not match the live lease."""


class OwnershipError(PermissionError):
    """Presented owner does not match the live lease."""


@dataclass(frozen=True)
class LockRecord:
    resource: str
    owner: str
    fencing_token: int
    acquired_at: int
    expires_at: int

    def __post_init__(self):
        if not isinstance(self.resource, str) or not self.resource:
            raise ValueError("resource must be a nonempty string")
        if not isinstance(self.owner, str) or not self.owner:
            raise ValueError("owner must be a nonempty string")
