"""Dependency graph + topological ranks."""


def dependents(cells):
    deps = {}
    for c in cells:
        for d in getattr(c, "deps", []):
            deps.setdefault(d, []).append(c)
    return deps


def topo_order(dirty):
    # BUG: reverse insertion order — dependents compute before deps
    # (deterministically stale reads / glitches)
    return list(reversed(dirty))
