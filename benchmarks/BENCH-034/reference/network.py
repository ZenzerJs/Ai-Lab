"""Constraint networks over the Allen relations."""
from algebra import converse_set
from relations import ALL


class Network:
    """nodes: interval names; edges[i][j] = allowed relations (frozenset).

    Consistency of the undirected shape is enforced: setting c[i][j]
    also sets c[j][i] to its converse.
    """

    def __init__(self, nodes):
        self.nodes = list(nodes)
        self.edges = {}
        for i in self.nodes:
            for j in self.nodes:
                if i != j:
                    self.edges[(i, j)] = ALL

    def set_label(self, i, j, label):
        label = frozenset(label)
        self.edges[(i, j)] = label
        self.edges[(j, i)] = converse_set(label)

    def label(self, i, j):
        return self.edges[(i, j)]

    def clone(self):
        n = Network(self.nodes)
        n.edges = dict(self.edges)
        return n
