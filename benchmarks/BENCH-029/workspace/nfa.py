"""NFA state graph."""


class State:
    __slots__ = ("eps", "edges")

    def __init__(self):
        self.eps = []
        self.edges = []


class NFA:
    def __init__(self, start, accept):
        self.start = start
        self.accept = accept
