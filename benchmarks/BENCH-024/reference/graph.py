"""Dependency graph: topological validation and cycle detection."""
from models import CycleError, DependencyError


class DependencyGraph:
    def __init__(self):
        self.tasks = {}          # task_id -> Task
        self.dependents = {}     # task_id -> set of dependents

    def add(self, task):
        if task.task_id in self.tasks:
            raise DependencyError(f"duplicate task {task.task_id}")
        self.tasks[task.task_id] = task
        for dep in task.deps:
            self.dependents.setdefault(dep, set()).add(task.task_id)
        self.dependents.setdefault(task.task_id, set())

    def validate(self):
        """Unknown deps and cycles are rejected before scheduling."""
        for task in self.tasks.values():
            for dep in task.deps:
                if dep not in self.tasks:
                    raise DependencyError(f"unknown dep {dep!r}")
        cycle = self.find_cycle()
        if cycle is not None:
            raise CycleError(" -> ".join(cycle))

    def find_cycle(self):
        """DFS returning one cycle as a node list, or None."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {tid: WHITE for tid in self.tasks}
        stack = []

        def visit(tid):
            color[tid] = GRAY
            stack.append(tid)
            for dep in self.tasks[tid].deps:
                if color[dep] == GRAY:
                    return stack[stack.index(dep):] + [dep]
                if color[dep] == WHITE:
                    found = visit(dep)
                    if found is not None:
                        return found
            stack.pop()
            color[tid] = BLACK
            return None

        for tid in self.tasks:
            if color[tid] == WHITE:
                found = visit(tid)
                if found is not None:
                    return found
        return None

    def topo_order(self):
        """Kahn's algorithm; deterministic via the ready ordering rule."""
        indegree = {tid: len(t.deps) for tid, t in self.tasks.items()}
        ready = sorted(tid for tid, d in indegree.items() if d == 0)
        order = []
        while ready:
            tid = ready.pop(0)
            order.append(tid)
            for child in sorted(self.dependents[tid]):
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
            ready.sort()
        if len(order) != len(self.tasks):
            raise CycleError("unschedulable tasks remain")
        return order
