"""Solver facade: build a network, assert constraints, solve."""
from network import Network
from relations import ALL
from search import solve


class Solver:
    def __init__(self, nodes):
        self.net = Network(nodes)

    def constrain(self, i, j, label):
        """Intersect edge (i,j) with the allowed-relation set."""
        cur = self.net.label(i, j) & frozenset(label)
        if not cur:
            raise ValueError(f"empty label on {i}->{j}")
        self.net.set_label(i, j, cur)

    def solve(self):
        """Return {edge: singleton relation} or None."""
        solved = solve(self.net)
        if solved is None:
            return None
        return {e: next(iter(l)) for e, l in solved.edges.items()}
