"""
models.py - Reference job data models and transition invariants for BENCH-008.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Set, Union


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    DLQ = "DLQ"


class InvalidTransitionError(ValueError):
    """Raised when a disallowed state transition is attempted."""
    pass


class LeaseError(RuntimeError):
    """Raised when lease ownership validation fails."""
    pass


VALID_TRANSITIONS: Dict[JobStatus, Set[JobStatus]] = {
    JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.DLQ},
    JobStatus.RUNNING: {
        JobStatus.COMPLETED,
        JobStatus.PENDING,
        JobStatus.DLQ,
        JobStatus.RUNNING,
    },
    JobStatus.COMPLETED: set(),
    JobStatus.DLQ: set(),
}


def validate_transition(
    from_status: Union[JobStatus, str],
    to_status: Union[JobStatus, str],
) -> None:
    """Validate allowed state transitions between JobStatus values."""
    src = JobStatus(from_status)
    dst = JobStatus(to_status)
    if dst not in VALID_TRANSITIONS[src]:
        raise InvalidTransitionError(
            f"Disallowed transition from {src.value} to {dst.value}"
        )


@dataclass
class Job:
    """Job record with validated attempts, max_attempts, and lease invariants."""
    job_id: str
    payload: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    lease_owner: Optional[str] = None
    lease_expires_at: Optional[float] = None
    available_at: float = 0.0
    last_error: Optional[str] = None
    created_at: float = 0.0
    updated_at: float = 0.0

    def __post_init__(self) -> None:
        self.status = JobStatus(self.status)
        if isinstance(self.attempts, bool) or not isinstance(self.attempts, int):
            raise ValueError("attempts must be an integer")
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int):
            raise ValueError("max_attempts must be an integer")
        if self.attempts < 0:
            raise ValueError(f"attempts must be >= 0, got {self.attempts}")
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {self.max_attempts}")
        if self.attempts > self.max_attempts:
            raise ValueError(
                f"attempts ({self.attempts}) cannot exceed max_attempts ({self.max_attempts})"
            )

        if self.status == JobStatus.RUNNING:
            if not self.lease_owner or not isinstance(self.lease_owner, str):
                raise ValueError("RUNNING job must have a non-empty lease_owner")
            if self.lease_expires_at is None:
                raise ValueError("RUNNING job must have lease_expires_at set")
        else:
            if self.lease_owner is not None or self.lease_expires_at is not None:
                raise ValueError(
                    f"{self.status.value} job must not hold lease_owner or lease_expires_at"
                )

    def can_transition_to(self, target: Union[JobStatus, str]) -> bool:
        """Return True if transitioning from current status to target is allowed."""
        try:
            validate_transition(self.status, target)
            return True
        except (ValueError, InvalidTransitionError):
            return False

    def transition_to(
        self,
        target: Union[JobStatus, str],
        *,
        lease_owner: Optional[str] = None,
        lease_expires_at: Optional[float] = None,
    ) -> None:
        """Transition job status after validating transition and lease invariants."""
        dst = JobStatus(target)
        validate_transition(self.status, dst)
        if dst == JobStatus.RUNNING:
            if not lease_owner:
                raise ValueError("Transition to RUNNING requires lease_owner")
            if lease_expires_at is None:
                raise ValueError("Transition to RUNNING requires lease_expires_at")
            self.lease_owner = lease_owner
            self.lease_expires_at = lease_expires_at
        else:
            self.lease_owner = None
            self.lease_expires_at = None
        self.status = dst
