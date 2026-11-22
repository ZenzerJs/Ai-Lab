"""Reactive cells: sources hold values; computed cells derive them."""


class Cell:
    def __init__(self, name):
        self.name = name
        self.value = None
        self.rank = 0


class Source(Cell):
    def set(self, v):
        self.value = v


class Computed(Cell):
    def __init__(self, name, fn, deps):
        super().__init__(name)
        self.fn = fn
        self.deps = list(deps)
        self.dirty = True

    def compute(self):
        self.value = self.fn(*[d.value for d in self.deps])
        self.dirty = False
