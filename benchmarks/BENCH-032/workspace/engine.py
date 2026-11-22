"""Glitch-free propagation engine."""
from batch import Batch
from cell import Computed
from topo import topo_order


class Engine:
    def __init__(self, graph):
        self.graph = graph
        self.recompute_count = 0

    def propagate(self):
        dirty = [c for c in self.graph.cells.values()
                 if isinstance(c, Computed) and c.dirty]
        for c in topo_order(dirty):
            c.compute()
            self.recompute_count += 1

    def set(self, name, value):
        src = self.graph.cells[name]
        src.set(value)
        self.graph.dirty_from(src)
        self.propagate()

    def batch(self):
        return Batch()
