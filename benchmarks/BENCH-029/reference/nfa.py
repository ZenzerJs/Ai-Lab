"""NFA state graph for Thompson construction."""


class State:
    """A state with epsilon targets and labelled edges.

    `eps` holds epsilon-transition targets; `edges` holds
    (predicate, target) pairs where predicate is a one-char callable.
    """
    __slots__ = ("eps", "edges")

    def __init__(self):
        self.eps = []
        self.edges = []


class NFA:
    """A fragment with one start state and one accept state."""

    def __init__(self, start, accept):
        self.start = start
        self.accept = accept
