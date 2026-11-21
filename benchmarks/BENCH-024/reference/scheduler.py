"""Scheduler: ordered execution with resource limits and failure
propagation. handler(task) returns True on success, raises on failure."""
from graph import DependencyGraph
from models import DeadlockError, TaskState
from ready import ReadyQueue
from resources import ResourcePool


class Scheduler:
    def __init__(self, graph, pool):
        graph.validate()
        self.graph = graph
        self.pool = pool
        self.states = {tid: TaskState.PENDING for tid in graph.tasks}
        self.results = {}
        self.order = []            # execution order, deterministic

    def _skip_dependents(self, task_id):
        for child in self.graph.dependents[task_id]:
            if self.states[child] in (TaskState.PENDING, TaskState.READY):
                self.states[child] = TaskState.SKIPPED
                self._skip_dependents(child)

    def run(self, handler):
        """Run every schedulable task; returns {task_id: state}."""
        pending = set(self.graph.tasks)
        while pending:
            queue = ReadyQueue()
            for tid in pending:
                task = self.graph.tasks[tid]
                if all(self.states[d] is TaskState.DONE for d in task.deps):
                    queue.push(task)
                    self.states[tid] = TaskState.READY
            if len(queue) == 0:
                # SKIPPED dependents are terminal, not a deadlock.
                if all(self.states[tid] is TaskState.SKIPPED
                       for tid in pending):
                    break
                raise DeadlockError(
                    f"deadlocked: {sorted(pending)}")
            progressed = False
            waiting = []
            while len(queue):
                task = queue.pop()
                if not self.pool.check(task.resources):
                    # Unsatisfiable demand: deadlock is certain.
                    raise DeadlockError(
                        f"{task.task_id} exceeds pool capacity")
                if not self.pool.try_acquire(task.resources):
                    waiting.append(task)
                    continue
                try:
                    handler(task)
                except Exception as exc:
                    self.states[task.task_id] = TaskState.FAILED
                    self.results[task.task_id] = exc
                    self._skip_dependents(task.task_id)
                else:
                    self.states[task.task_id] = TaskState.DONE
                    self.results[task.task_id] = None
                finally:
                    self.pool.release(task.resources)
                    pending.discard(task.task_id)
                self.order.append(task.task_id)
                progressed = True
            # Requeue tasks that could not acquire this round.
            for task in waiting:
                queue.push(task)
            if not progressed and not queue:
                raise DeadlockError(f"deadlocked: {sorted(pending)}")
            if not progressed:
                raise DeadlockError(f"deadlocked: {sorted(pending)}")
        return dict(self.states)
