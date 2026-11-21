"""Scheduling decisions derived from dependency states."""
class Scheduler:
    def __init__(self, graph):
        self.graph = graph

    def plan(self):
        return self.graph.topological_order()

    def should_skip(self, task):
        return any(self.graph.tasks[dep].status == "failed"
                   for dep in task.dependencies)
