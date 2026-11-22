"""Deterministic NFA simulation: closure, step, run."""
from nfa import NFA


def closure(states) -> list:
    """Transitive epsilon closure of `states`, order-stable."""
    seen = set()
    out = []
    stack = list(states)
    while stack:
        st = stack.pop()
        if id(st) in seen:
            continue
        seen.add(id(st))
        out.append(st)
        stack.extend(st.eps)
    return out


def step(states, ch: str) -> list:
    """All states reachable from `states` by consuming `ch`."""
    nxt = []
    for st in states:
        for pred, target in st.edges:
            if pred(ch):
                nxt.append(target)
    return closure(nxt)


def run(nfa: NFA, text: str, pos: int = 0) -> list:
    """End positions where the accept state is reachable.

    Returns the sorted list of end offsets e > pos-1 such that matching
    text[pos:e] drives the NFA to its accept state.
    """
    cur = closure([nfa.start])
    ends = [pos] if nfa.accept in cur else []
    for i in range(pos, len(text)):
        cur = step(cur, text[i])
        if not cur:
            break
        if nfa.accept in cur:
            ends.append(i + 1)
    return ends
