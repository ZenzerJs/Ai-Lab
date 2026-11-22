"""Glitch-free propagation engine."""
from batch import Batch
from cell import Computed
from topo import topo_order


class Engine:
    """Owns a Graph; propagate() recomputes dirty cells in topo order.

    Glitch-free guarantee: each dirty cell recomputes exactly once per
    wave, after all its dirty dependencies — intermediate (glitch)
    values are never observable inside fn during the wave.
    """

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
        """Write a source, mark dependents dirty, propagate."""
        src = self.graph.cells[name]
        src.set(value)
        self.graph.dirty_from(src)
        self.propagate()

    def batch(self):
        return Batch()
