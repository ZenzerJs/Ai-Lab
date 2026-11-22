"""Windowed aggregators."""


class Count:
    def __init__(self):
        self.n = 0

    def add(self, v):
        self.n += v      # BUG: counts VALUES, not events

    def result(self):
        return self.n


class Sum:
    def __init__(self):
        self.total = 0

    def add(self, v):
        self.total += v

    def result(self):
        return self.total


class Mean:
    def __init__(self):
        self.total = 0
        self.n = 0

    def add(self, v):
        self.total += v
        self.n += 1

    def result(self):
        return 0 if self.n == 0 else self.total / self.n
