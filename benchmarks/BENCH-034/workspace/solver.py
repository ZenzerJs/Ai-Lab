
from network import Network
from relations import ALL
from search import solve


class Solver:
    def __init__(self, nodes):
        self.net = Network(nodes)

    def constrain(self, i, j, label):
        
        cur = self.net.label(i, j) & frozenset(label)
        if not cur:
            raise ValueError(f"empty label on {i}->{j}")
        self.net.set_label(i, j, cur)

    def solve(self):
        
        solved = solve(self.net)
        if solved is None:
            return None
        return {e: next(iter(l)) for e, l in solved.edges.items()}
