"""Ready queue: (priority desc, task_id asc) deterministic ordering."""
import heapq


class ReadyQueue:
    def __init__(self):
        self._heap = []

    def push(self, task):
        heapq.heappush(self._heap, (-task.priority, task.task_id, task))

    def pop(self):
        return heapq.heappop(self._heap)[2]

    def __len__(self):
        return len(self._heap)
