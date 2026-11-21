"""Scheduler."""
from graph import DependencyGraph
from models import TaskState
from ready import ReadyQueue
from resources import ResourcePool


class Scheduler:
    def __init__(self, graph, pool):
        graph.validate()
        self.graph = graph
        self.pool = pool
        self.states = {tid: TaskState.PENDING for tid in graph.tasks}
        self.results = {}
        self.order = []

    def run(self, handler):
        pending = set(self.graph.tasks)
        while pending:
            queue = ReadyQueue()
            for tid in pending:
                task = self.graph.tasks[tid]
                if all(self.states[d] is TaskState.DONE for d in task.deps):
                    queue.push(task)
            if len(queue) == 0:
                break
            task = queue.pop()
            self.pool.try_acquire(task.resources)
            try:
                handler(task)
                self.states[task.task_id] = TaskState.DONE
                self.results[task.task_id] = None
            except Exception as exc:
                self.states[task.task_id] = TaskState.FAILED
                self.results[task.task_id] = exc
            self.pool.release(task.resources)
            pending.discard(task.task_id)
            self.order.append(task.task_id)
        return dict(self.states)
