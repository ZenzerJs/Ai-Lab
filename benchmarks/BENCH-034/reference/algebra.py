"""Relation algebra: converse + composition over the 13 relations.

The composition table is computed by exhaustive enumeration over all
intervals on a 4-point chain — sufficient to express every Allen
relation (the relations are complete for a dense linear order).
"""
from relations import ALL, CONVERSE, relation_of

_POINTS = range(7)
_INTERVALS = [(a, b) for a in _POINTS for b in _POINTS if a < b]


def converse_set(label):
    return frozenset(CONVERSE[r] for r in label)


def _compose_pair(r, s):
    out = set()
    for x in _INTERVALS:
        for y in _INTERVALS:
            if relation_of(x, y) != r:
                continue
            for z in _INTERVALS:
                if relation_of(y, z) == s:
                    out.add(relation_of(x, z))
    return frozenset(out)


_COMP = {(r, s): _compose_pair(r, s) for r in ALL for s in ALL}


def compose(r, s):
    """Table entry for r ∘ s."""
    return _COMP[(r, s)]


def compose_set(A, B):
    """A ∘ B = union of compose(r, s) for r in A, s in B."""
    out = set()
    for r in A:
        for s in B:
            out |= _COMP[(r, s)]
    return frozenset(out)
