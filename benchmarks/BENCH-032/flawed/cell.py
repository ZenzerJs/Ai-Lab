"""Reactive cells: sources hold values; computed cells derive them."""


class Cell:
    """A named node. `value` is the current cached result."""

    def __init__(self, name):
        self.name = name
        self.value = None
        self.rank = 0          # topological height, set by scheduler


class Source(Cell):
    """Externally settable value."""

    def set(self, v):
        self.value = v


class Computed(Cell):
    """fn(deps) -> value; deps are other cells."""

    def __init__(self, name, fn, deps):
        super().__init__(name)
        self.fn = fn
        self.deps = list(deps)
        self.dirty = True      # recompute on next propagation

    def compute(self):
        self.value = self.fn(*[d.value for d in self.deps])
        self.dirty = False
