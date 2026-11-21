"""Task state and graph errors."""
from dataclasses import dataclass, field


class CycleError(ValueError):
    def __init__(self, cycle):
        self.cycle = list(cycle)
        super().__init__(" -> ".join(self.cycle))


@dataclass
class Task:
    name: str
    dependencies: tuple = field(default_factory=tuple)
    status: str = "pending"
    result: object = None
    error: str = None

    def __post_init__(self):
        if not self.name:
            raise ValueError("empty task name")
        self.dependencies = tuple(self.dependencies)
