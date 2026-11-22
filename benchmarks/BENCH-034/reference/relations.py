"""The 13 Allen interval relations.

x=[x1,x2), y=[y1,y2) with x1<x2, y1<y2:
  b  x2 <  y1          bi y2 <  x1
  m  x2 == y1          mi y2 == x1
  o  x1 < y1 < x2 < y2 oi y1 < x1 < y2 < x2
  s  x1==y1, x2 < y2   si x1==y1, x2 > y2
  d  x1 > y1, x2 < y2  di x1 < y1, x2 > y2
  f  x1 > y1, x2==y2   fi x1 < y1, x2==y2
  eq x1==y1, x2==y2
"""
B, M, O, S, D, F, BI, MI, OI, SI, DI, FI, EQ = (
    "b", "m", "o", "s", "d", "f",
    "bi", "mi", "oi", "si", "di", "fi", "eq")

ALL = frozenset([B, M, O, S, D, F, BI, MI, OI, SI, DI, FI, EQ])

CONVERSE = {
    B: BI, M: MI, O: OI, S: SI, D: DI, F: FI, EQ: EQ,
    BI: B, MI: M, OI: O, SI: S, DI: D, FI: F,
}


def relation_of(x, y):
    """Classify the Allen relation between intervals x=(x1,x2), y=(y1,y2)."""
    x1, x2 = x
    y1, y2 = y
    assert x1 < x2 and y1 < y2, "degenerate interval"
    if x2 < y1:
        return B
    if x2 == y1:
        return M
    if y2 < x1:
        return BI
    if y2 == x1:
        return MI
    if x1 == y1:
        if x2 < y2:
            return S
        if x2 > y2:
            return SI
        return EQ
    if x2 == y2:
        return F if x1 > y1 else FI
    if x1 < y1 and x2 < y2:
        return O
    if x1 > y1 and x2 > y2:
        return OI
    if x1 > y1:
        return D
    return DI
