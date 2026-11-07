"""Queue Engine Schema & State Definitions."""
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional


class JobState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class Priority(int, Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3


@dataclass
class Job:
    id: str
    tenant_id: str
    payload: Dict[str, Any]
    state: JobState = JobState.PENDING
    priority: Priority = Priority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    attempts: int = 0
    max_attempts: int = 3
    created_at: float = field(default_factory=time.time)
    leased_until: Optional[float] = None
    last_error: Optional[str] = None
