"""Ready queue: FIFO."""


class ReadyQueue:
    def __init__(self):
        self._items = []

    def push(self, task):
        self._items.append(task)

    def pop(self):
        return self._items.pop(0)

    def __len__(self):
        return len(self._items)
