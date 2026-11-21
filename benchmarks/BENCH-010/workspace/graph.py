"""Validated dependency graph with deterministic ordering."""
import heapq

from models import CycleError


class Graph:
    def __init__(self, tasks):
        self.tasks = {}
        for task in tasks:
            if task.name in self.tasks:
                raise ValueError("duplicate task")
            self.tasks[task.name] = task
        for task in self.tasks.values():
            if any(dep not in self.tasks for dep in task.dependencies):
                raise ValueError("unknown dependency")

    def topological_order(self):
        return list(self.tasks)
