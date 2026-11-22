"""Visible smoke tests for BENCH-032."""
from engine import Engine
from graph import Graph


def test_basic_recompute():
    g = Graph()
    g.add_source("a", 1)
    g.add("b", lambda a: a * 2, ["a"])
    e = Engine(g)
    e.propagate()
    assert g.cells["b"].value == 2
    e.set("a", 3)
    assert g.cells["b"].value == 6


def test_batch_flushes():
    g = Graph()
    g.add_source("x", 0)
    g.add("y", lambda x: x + 1, ["x"])
    e = Engine(g)
    e.propagate()
    b = e.batch()
    b.set(g.cells["x"], 5)
    b.flush(e)
    assert g.cells["y"].value == 6
