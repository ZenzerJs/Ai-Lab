"""Scheduler models: tasks, states, exceptions."""
from dataclasses import dataclass, field
from enum import Enum


class TaskState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class CycleError(ValueError):
    """Raised with the detected dependency cycle as a node list."""


class DependencyError(ValueError):
    """Raised for unknown dependency references."""


class ResourceCapacityError(ValueError):
    """Raised when a task requests more than a pool's capacity."""


class DeadlockError(RuntimeError):
    """Raised when pending tasks can never be scheduled."""


@dataclass(frozen=True)
class Task:
    """priority: larger runs first; ties break on lexicographic id.
    resources: {pool_name: units} held for the duration of one run."""

    task_id: str
    deps: tuple = ()
    priority: int = 0
    resources: tuple = field(default_factory=tuple)

    def __post_init__(self):
        if not isinstance(self.task_id, str) or not self.task_id:
            raise ValueError("task_id must be a nonempty string")
        if isinstance(self.priority, bool) \
                or not isinstance(self.priority, int):
            raise ValueError("priority must be an int")
        if not isinstance(self.deps, tuple):
            raise ValueError("deps must be a tuple")
        if len(set(self.deps)) != len(self.deps):
            raise ValueError("duplicate deps")
        if self.task_id in self.deps:
            raise ValueError("self-dependency")
        if not isinstance(self.resources, tuple):
            raise ValueError("resources must be a tuple")
        for spec in self.resources:
            if not isinstance(spec, tuple) or len(spec) != 2 \
                    or not isinstance(spec[0], str) \
                    or isinstance(spec[1], bool) \
                    or not isinstance(spec[1], int) or spec[1] < 1:
                raise ValueError(
                    "resources must be (name, positive_int) pairs")
