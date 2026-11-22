"""BENCH-034 evaluator: Allen interval constraint solver."""
import sys


def fail(check, detail=""):
    print("REASON: consistency_violation")
    print(f"{check}: {type(detail).__name__ if isinstance(detail, Exception) else 'AssertionError'}: {detail}")
    sys.exit(1)


def check(fn):
    try:
        fn()
    except Exception as e:
        fail(fn.__name__, e)


def relation_checks():
    from relations import B, BI, D, DI, EQ, F, FI, M, MI, O, OI, relation_of, S, SI
    assert relation_of((0, 1), (2, 3)) == B
    assert relation_of((0, 1), (1, 2)) == M
    assert relation_of((0, 3), (1, 2)) == DI
    assert relation_of((0, 2), (0, 3)) == S
    assert relation_of((0, 2), (1, 2)) == FI
    assert relation_of((0, 3), (1, 3)) == FI
    assert relation_of((1, 3), (0, 2)) == OI
    assert relation_of((0, 2), (1, 3)) == O
    assert relation_of((1, 3), (0, 3)) == F
    assert relation_of((0, 2), (0, 2)) == EQ
    assert relation_of((1, 2), (0, 1)) == MI


def converse_checks():
    from algebra import converse_set, compose
    from relations import B, BI, M, O, S, D, F, FI
    assert converse_set({B}) == frozenset({BI})
    assert converse_set({S, F}) == frozenset({"si", "fi"})
    # b ∘ b = {b}; m ∘ b includes bi-side results
    assert compose(B, B) == frozenset({B})
    assert B in compose(B, M)


def compose_table_checks():
    """Composition must be complete — overlaps need 4 points."""
    from algebra import compose
    from relations import O, S, D, F, B, M
    c = compose(O, O)
    assert c == frozenset({B, M, O}), \
        f"o∘o must be exactly {{b,m,o}}, got {c}"
    c2 = compose(O, S)
    assert len(c2) > 0


def network_checks():
    from network import Network
    from relations import B
    n = Network(["a", "b"])
    n.set_label("a", "b", {B})
    assert n.label("a", "b") == frozenset({B})
    assert n.label("b", "a") == frozenset({"bi"}), \
        "reverse edge must hold the converse"


def pc2_checks():
    from network import Network
    from propagate import pc2
    from relations import B, M
    n = Network(["a", "b", "c"])
    n.set_label("a", "b", {B})
    n.set_label("b", "c", {B})
    assert pc2(n) is True
    # a < b < c forces a<c to be {b} exactly
    assert n.label("a", "c") == frozenset({B}), \
        f"pc2 must tighten a->c to {{b}}, got {n.label('a','c')}"


def inconsistent_checks():
    from network import Network
    from propagate import pc2
    from relations import B, BI
    n = Network(["a", "b", "c"])
    n.set_label("a", "b", {B})
    n.set_label("b", "c", {B})
    n.set_label("c", "a", {B})    # cycle: a<b<c<a is impossible
    assert pc2(n) is False, "empty label must fail"


def solver_checks():
    from relations import B, M, O
    from solver import Solver
    s = Solver(["x", "y", "z"])
    s.constrain("x", "y", {B, M})
    s.constrain("y", "z", {B, M})
    sol = s.solve()
    assert sol is not None
    assert sol[("x", "y")] in {"b", "m"}
    assert sol[("x", "z")] == "b", "x<y<z forces x<z = before"

    s2 = Solver(["p", "q", "r"])
    s2.constrain("p", "q", {B})
    s2.constrain("q", "r", {B})
    s2.constrain("r", "p", {B})
    assert s2.solve() is None, "cyclic before-chain is unsatisfiable"


for fn in (relation_checks, converse_checks, compose_table_checks,
           network_checks, pc2_checks, inconsistent_checks,
           solver_checks):
    check(fn)
print("ALL CHECKS PASSED")
