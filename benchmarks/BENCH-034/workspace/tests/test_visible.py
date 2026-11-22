"""Visible smoke tests for BENCH-034."""
from relations import B, M, relation_of
from solver import Solver


def test_relation_classify():
    assert relation_of((0, 1), (2, 3)) == B
    assert relation_of((0, 1), (1, 2)) == M


def test_solver_satisfiable():
    s = Solver(["x", "y"])
    s.constrain("x", "y", {B})
    sol = s.solve()
    assert sol is not None
    assert sol[("x", "y")] == "b"
