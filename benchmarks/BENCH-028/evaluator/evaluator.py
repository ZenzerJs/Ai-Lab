"""Protected deterministic checks for BENCH-028."""
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from counters import GCounter, PNCounter
        from lww import LWWRegister
        from merge import merge
        from orset import ORSet
        from store import Store
        from vclock import VectorClock

        def vclock_checks():
            a = VectorClock().increment("n1")
            b = VectorClock().increment("n2")
            assert a.compare(b) == "concurrent"
            m = a.merge(b)
            assert m.entries == {"n1": 1, "n2": 1}
            assert m.compare(a) == "gt" and m.compare(b) == "gt"
            assert a.merge(b).entries == b.merge(a).entries
            a2 = a.increment("n1")
            assert a2.compare(a) == "gt" and a.compare(a2) == "lt"
            assert a.compare(a) == "eq"
            # merge keeps causal history (elementwise max)
            lost = a.merge(VectorClock({"n1": 5}))
            assert lost.entries["n1"] == 5

        def counter_checks():
            g1 = GCounter().increment("a", 3)
            g2 = GCounter().increment("b", 2)
            m = g1.merge(g2)
            assert m.value == 5
            assert m.merge(m).value == 5          # idempotent
            assert m.merge(g1).value == 5
            assert g1.merge(g2).value == g2.merge(g1).value
            p = PNCounter().increment("a", 4).decrement("a", 1)
            assert p.value == 3
            p2 = p.merge(PNCounter().increment("b", 2))
            assert p2.value == 5
            assert p2.merge(p).value == 5         # idempotent

        def orset_checks():
            s = ORSet().add("x", "t1")
            assert s.contains("x")
            assert not s.contains("y")
            dead = s.remove("x")
            assert not dead.contains("x")
            # Add-wins: a concurrent add whose tag was never observed
            # by remove() must survive the merge.
            readded = s.add("x", "t2")
            merged = dead.merge(readded)
            assert merged.contains("x")
            assert merged.elements() == ["x"]
            assert merged.merge(merged).elements() == ["x"]
            multi = ORSet().add("a", "ta").add("b", "tb")
            assert multi.elements() == ["a", "b"]
            dead2 = multi.remove("a")
            peer = ORSet().add("a", "ta2")
            assert dead2.merge(peer).elements() == ["a", "b"]

        def lww_checks():
            r = LWWRegister().set("v1", 10, "n1")
            assert r.value == "v1"
            # Stale and equal-stamp writes lose.
            assert r.set("old", 5, "n9").value == "v1"
            # Equal ts: the higher node id wins — deterministically.
            a = LWWRegister().set("A", 7, "node-a")
            b = LWWRegister().set("B", 7, "node-b")
            assert a.merge(b).value == "B"
            assert b.merge(a).value == "B"        # order-independent
            c = LWWRegister().set("C", 8, "node-a")
            assert a.merge(c).value == "C"        # later write same node

        def merge_checks():
            g = GCounter().increment("a")
            s = ORSet().add("e", "t")
            assert merge(g, g).value == 1
            assert merge(s, s).elements() == ["e"]
            rejected(TypeError, lambda: merge(g, s))
            rejected(TypeError, lambda: merge(g, 42))

        def store_checks():
            s1 = Store("n1").apply("k", PNCounter().increment("n1", 3))
            s2 = Store("n2").apply("k", PNCounter().increment("n2", 4))
            conv = s1.merge_peer(s2)
            assert conv.get("k").value == 7
            again = conv.merge_peer(s1).merge_peer(s2)
            assert again.get("k").value == 7      # idempotent
            assert again.clock.entries == {"n1": 1, "n2": 1}
            # Concurrent removes/adds converge regardless of order.
            a = Store("a").apply("set", ORSet().add("m", "t1"))
            b = Store("b").apply("set", ORSet().add("m", "t2"))
            dead = Store("a").apply("set",
                                    ORSet().add("m", "t1").remove("m"))
            merged1 = dead.merge_peer(a.merge_peer(b))
            merged2 = dead.merge_peer(b.merge_peer(a))
            assert merged1.get("set").elements() == ["m"]
            assert merged2.get("set").elements() == ["m"]

        for check in (vclock_checks, counter_checks, orset_checks,
                      lww_checks, merge_checks, store_checks):
            try:
                check()
            except Exception as exc:
                fail(f"{check.__name__}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        fail(f"import_error: {exc}")
    print("ALL CHECKS PASSED")


def fail(detail):
    print("REASON: convergence_invariant_violation", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
