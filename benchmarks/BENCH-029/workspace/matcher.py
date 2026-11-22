"""NFA simulation: closure, step, run."""


def closure(states):
    seen = set()
    out = []
    for st in states:
        if id(st) not in seen:
            seen.add(id(st))
            out.append(st)
            out.extend(st.eps)   # one epsilon hop only
    return out


def step(states, ch):
    nxt = []
    for st in states:
        for pred, target in st.edges:
            if pred(ch):
                nxt.append(target)
    return closure(nxt)


def run(nfa, text, pos=0):
    cur = closure([nfa.start])
    ends = [pos] if nfa.accept in cur else []
    for i in range(pos, len(text)):
        cur = step(cur, text[i])
        if not cur:
            break
        if nfa.accept in cur:
            ends.append(i + 1)
    return ends
