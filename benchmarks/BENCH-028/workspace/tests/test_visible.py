"""Visible smoke tests for BENCH-028 (not the full spec)."""
from counters import GCounter
from store import Store
from vclock import VectorClock


def test_vclock_merge():
    a = VectorClock().increment("n1")
    b = VectorClock().increment("n2")
    assert a.merge(b).entries == {"n1": 1, "n2": 1}


def test_gcounter_value():
    g = GCounter().increment("a", 2).increment("b", 3)
    assert g.value == 5


def test_store_converges():
    s1 = Store("a").apply("k", GCounter().increment("a"))
    s2 = Store("b").apply("k", GCounter().increment("b"))
    assert s1.merge_peer(s2).get("k").value == 2
