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

        for name in sorted(self.tasks):
            visit(name)
        remaining = {name: set(task.dependencies) for name, task in self.tasks.items()}
        ready = [name for name, deps in remaining.items() if not deps]
        heapq.heapify(ready)
        order = []
        while ready:
            name = heapq.heappop(ready)
            order.append(name)
            for child in sorted(remaining):
                if name in remaining[child]:
                    remaining[child].remove(name)
                    if not remaining[child]:
                        heapq.heappush(ready, child)
        return order
