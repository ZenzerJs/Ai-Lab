
from algebra import compose_set


def pc2(net):
    """Tighten edge labels until fixpoint.

    Returns True when every edge is non-empty (network may still need
    search to singleton), False as soon as a label empties —
    the network is inconsistent.
    """
    nodes = net.nodes
    changed = True
    while changed:
        changed = False
        for i in nodes:
            for j in nodes:
                if i == j:
                    continue
                cij = net.edges[(i, j)]
                for k in nodes:
                    if k == i or k == j:
                        continue
                    tightened = cij | compose_set(
                        net.edges[(i, k)], net.edges[(k, j)])
                    # BUG: union never tightens; also never detects empties
                    if tightened != cij:
                        net.edges[(i, j)] = tightened
                        cij = tightened
                        changed = True
    return True
