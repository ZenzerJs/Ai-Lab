"""Dependency graph."""
from models import DependencyError


class DependencyGraph:
    def __init__(self):
        self.tasks = {}
        self.dependents = {}

    def add(self, task):
        self.tasks[task.task_id] = task
        for dep in task.deps:
            self.dependents.setdefault(dep, set()).add(task.task_id)
        self.dependents.setdefault(task.task_id, set())

    def validate(self):
        for task in self.tasks.values():
            for dep in task.deps:
                if dep not in self.tasks:
                    raise DependencyError(f"unknown dep {dep!r}")

    def find_cycle(self):
        return None

    def topo_order(self):
        return list(self.tasks)
