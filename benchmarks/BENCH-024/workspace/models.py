"""Scheduler models."""
from dataclasses import dataclass, field
from enum import Enum


class TaskState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class CycleError(ValueError):
    pass


class DependencyError(ValueError):
    pass


class ResourceCapacityError(ValueError):
    pass


class DeadlockError(RuntimeError):
    pass


@dataclass(frozen=True)
class Task:
    task_id: str
    deps: tuple = ()
    priority: int = 0
    resources: tuple = field(default_factory=tuple)
