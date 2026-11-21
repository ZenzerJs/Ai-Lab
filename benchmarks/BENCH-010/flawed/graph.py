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
        visiting, visited, path = set(), set(), []
        order = []

        def visit(name):
            if name in visiting:
                raise CycleError(path[path.index(name):] + [name])
            if name in visited:
                return
            visiting.add(name)
            path.append(name)
            for dep in sorted(self.tasks[name].dependencies):
                visit(dep)
            path.pop()
            visiting.remove(name)
            visited.add(name)
            order.append(name)

        for name in sorted(self.tasks):
            visit(name)
        return order
