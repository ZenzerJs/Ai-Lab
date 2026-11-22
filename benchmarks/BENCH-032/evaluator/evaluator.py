"""BENCH-032 evaluator: glitch-free reactive dataflow."""
import sys


def fail(check, detail=""):
    print("REASON: propagation_glitch")
    print(f"{check}: {type(detail).__name__ if isinstance(detail, Exception) else 'AssertionError'}: {detail}")
    sys.exit(1)


def check(fn):
    try:
        fn()
    except Exception as e:
        fail(fn.__name__, e)


def basic_checks():
    from cell import Computed
    from engine import Engine
    from graph import Graph
    g = Graph()
    g.add_source("a", 1)
    g.add_source("b", 2)
    g.add("sum", lambda a, b: a + b, ["a", "b"])
    e = Engine(g)
    e.propagate()
    assert g.cells["sum"].value == 3
    e.set("a", 10)
    assert g.cells["sum"].value == 12, "dependents must recompute"


def diamond_checks():
    """Diamond: a -> m1, a -> m2, m1+m2 -> out. One wave, no glitch."""
    from engine import Engine
    from graph import Graph
    g = Graph()
    g.add_source("a", 1)
    seen = []
    g.add("m1", lambda a: a * 2, ["a"])
    g.add("m2", lambda a: a + 1, ["a"])
    g.add("out", lambda m1, m2: seen.append((m1, m2)) or m1 + m2,
          ["m1", "m2"])
    e = Engine(g)
    e.propagate()
    assert g.cells["out"].value == 4
    e.set("a", 5)
    assert g.cells["out"].value == 16
    # 'out' fn ran exactly twice total: initial + one per wave
    assert seen == [(2, 2), (10, 6)], f"glitch states observed: {seen}"
    assert e.recompute_count == 6, "each dirty cell recomputes once"


def chain_checks():
    """Chain a -> b -> c -> d: transitive dirty marking."""
    from engine import Engine
    from graph import Graph
    g = Graph()
    g.add_source("a", 1)
    g.add("b", lambda a: a + 1, ["a"])
    g.add("c", lambda b: b * 10, ["b"])
    g.add("d", lambda c: c - 1, ["c"])
    e = Engine(g)
    e.propagate()
    assert g.cells["d"].value == 19
    e.set("a", 2)
    assert g.cells["d"].value == 29, \
        "deep dependents must be marked dirty transitively"


def batch_checks():
    """Batch: two writes -> ONE wave; no intermediate states."""
    from engine import Engine
    from graph import Graph
    g = Graph()
    g.add_source("x", 0)
    g.add_source("y", 0)
    states = []
    g.add("both", lambda x, y: states.append((x, y)) or (x, y),
          ["x", "y"])
    e = Engine(g)
    e.propagate()
    b = e.batch()
    b.set(g.cells["x"], 1)
    b.set(g.cells["y"], 2)
    b.flush(e)
    assert states == [(0, 0), (1, 2)], \
        f"intermediate glitch states observed: {states}"


def topo_checks():
    from cell import Computed
    from topo import topo_order
    from engine import Engine
    from graph import Graph
    g = Graph()
    g.add_source("a", 1)
    g.add("b", lambda a: a + 1, ["a"])
    g.add("c", lambda b, a: b + a, ["b", "a"])
    e = Engine(g)
    e.propagate()
    e.set("a", 5)
    dirty = [c for c in g.cells.values()
             if isinstance(c, Computed)]
    order = topo_order(dirty)
    names = [c.name for c in order]
    assert names.index("b") < names.index("c"), \
        "b must recompute before its dependent c"


for fn in (basic_checks, diamond_checks, chain_checks, batch_checks,
           topo_checks):
    check(fn)
print("ALL CHECKS PASSED")
