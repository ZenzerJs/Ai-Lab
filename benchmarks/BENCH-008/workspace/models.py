"""
models.py - Broken job data models and transitions for BENCH-008.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Union


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


def validate_transition(
    from_status: Union[JobStatus, str],
    to_status: Union[JobStatus, str],
) -> None:
    """BROKEN: Permits arbitrary state transitions without validation."""
    return None


@dataclass
class Job:
    """
    BROKEN: Missing lease_owner/lease_expires_at fields and lacks attempt
    or lease invariant validation.
    """
    job_id: str
    payload: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    available_at: float = 0.0
    last_error: Optional[str] = None
    created_at: float = 0.0
    updated_at: float = 0.0
