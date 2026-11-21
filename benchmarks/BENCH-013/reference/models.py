"""Lease record model and lock errors."""
from dataclasses import dataclass


class LockConflictError(RuntimeError):
    """Resource is already leased under a live lock."""


class StaleTokenError(ValueError):
    """Presented fencing token does not match the live lease."""


class OwnershipError(PermissionError):
    """Presented owner does not match the live lease."""


def _as_int(value, field):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


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
        if _as_int(self.fencing_token, "fencing_token") <= 0:
            raise ValueError("fencing token must be a positive integer")
        if _as_int(self.acquired_at, "acquired_at") < 0:
            raise ValueError("acquired_at must be nonnegative")
        if _as_int(self.expires_at, "expires_at") <= self.acquired_at:
            raise ValueError("expires_at must be after acquired_at")
