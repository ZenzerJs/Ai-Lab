"""Dependency graph + topological ranks."""
from cell import Computed


def dependents(cells):
    """cell -> list of computed cells that read it."""
    deps = {}
    for c in cells:
        if isinstance(c, Computed):
            for d in c.deps:
                deps.setdefault(d, []).append(c)
    return deps


def topo_order(dirty):
    """Kahn's order over the dirty subgraph, edges dep -> dependent.

    Ranks: a cell's rank = max(dep.rank) + 1 over dirty deps, so a cell
    is always scheduled strictly AFTER every dirty dependency it reads
    (glitch-free ordering). Clean cells keep rank 0.
    """
    order, rank = [], {}
    remaining = set(dirty)
    # iterate until stable; dirty deps may feed other dirty cells
    while remaining:
        ready = [c for c in remaining
                 if all(d not in remaining or d in rank
                        for d in getattr(c, "deps", []))]
        if not ready:
            raise ValueError("dependency cycle")
        for c in ready:
            rank[c] = max([rank.get(d, getattr(d, "rank", 0))
                           for d in getattr(c, "deps", [])],
                          default=0) + 1
            c.rank = rank[c]
            order.append(c)
            remaining.discard(c)
    return order
