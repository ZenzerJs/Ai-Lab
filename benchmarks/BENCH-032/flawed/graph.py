"""The reactive graph container."""
from cell import Cell, Computed, Source
from topo import dependents


class Graph:
    """Named cells; marks dependents dirty when a source changes."""

    def __init__(self):
        self.cells = {}

    def add_source(self, name, value=None):
        c = Source(name)
        c.set(value)
        self.cells[name] = c
        return c

    def add(self, name, fn, deps):
        c = Computed(name, fn, [self.cells[d] for d in deps])
        self.cells[name] = c
        return c

    def dirty_from(self, cell):
        """Transitively mark every dependent of `cell` dirty."""
        deps = dependents(self.cells.values())
        stack = [cell]
        seen = set()
        while stack:
            cur = stack.pop()
            for nxt in deps.get(cur, []):
                if nxt not in seen:
                    seen.add(nxt)
                    nxt.dirty = True
        return seen
