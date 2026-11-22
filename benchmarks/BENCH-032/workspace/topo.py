"""Dependency graph + topological ranks."""


def dependents(cells):
    deps = {}
    for c in cells:
        for d in getattr(c, "deps", []):
            deps.setdefault(d, []).append(c)
    return deps


def topo_order(dirty):
    # arbitrary set order — no dependency ranking (glitchy!)
    return list(dirty)
