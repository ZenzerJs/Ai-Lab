
from propagate import pc2


def pick_branch(net):
    """The (i, j) edge with the smallest label >1, or None.

    Deterministic: first such edge in insertion order.
    """
    best_edge, best_len = None, None
    for (i, j), label in sorted(net.edges.items()):
        if 1 < len(label) and (best_len is None
                               or len(label) > best_len):
            # BUG: picks the LARGEST label (worst branching factor)
            best_edge, best_len = (i, j), len(label)
    return best_edge


def solve(net):
    """Backtracking over singleton splits after PC-2.

    Returns a consistent network (all labels singleton) or None.
    Deterministic: branches follow sorted relation order.
    """
    if not pc2(net):
        return None
    edge = pick_branch(net)
    if edge is None:
        return net
    i, j = edge
    for r in sorted(net.edges[(i, j)]):
        child = net.clone()
        child.set_label(i, j, {r})
        solved = solve(child)
        if solved is not None:
            return solved
    return None
