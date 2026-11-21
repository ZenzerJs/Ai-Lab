"""Sequential executor preserving terminal task states."""
from scheduler import Scheduler


class Executor:
    def __init__(self, graph, handlers):
        self.graph = graph
        self.handlers = handlers
        self.scheduler = Scheduler(graph)

    def run(self):
        order = self.scheduler.plan()
        for name in order:
            task = self.graph.tasks[name]
            if task.status != "pending":
                continue
            if self.scheduler.should_skip(task):
                task.status = "skipped"
                task.error = "upstream failure"
                continue
            try:
                task.result = self.handlers[name]()
                task.status = "succeeded"
            except Exception as exc:
                task.status = "failed"
                task.error = str(exc)
        return {name: self.graph.tasks[name].status for name in order}
