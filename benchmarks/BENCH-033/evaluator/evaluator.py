"""BENCH-033 evaluator: windowed stream aggregation with watermarks."""
import sys


def fail(check, detail=""):
    print("REASON: stream_invariant_violation")
    print(f"{check}: {type(detail).__name__ if isinstance(detail, Exception) else 'AssertionError'}: {detail}")
    sys.exit(1)


def check(fn):
    try:
        fn()
    except Exception as e:
        fail(fn.__name__, e)


def watermark_checks():
    from watermark import Watermark
    w = Watermark(10)
    assert w.observe(100) == 90
    assert w.observe(50) == 90, "out-of-order event must not regress wm"
    assert w.is_late(89) and not w.is_late(90)
    assert not w.is_late(150)
    assert w.observe(200) == 190


def window_checks():
    from windows import window_of, window_bounds
    assert window_of(0, 100) == 0
    assert window_of(99, 100) == 0, "floor, not round"
    assert window_of(100, 100) == 1
    assert window_of(150, 100) == 1
    assert window_bounds(2, 100) == (200, 300)


def aggregator_checks():
    from aggregators import Count, Mean, Sum
    c = Count()
    for v in (5, 5, 5):
        c.add(v)
    assert c.result() == 3, "Count counts events, not values"
    s = Sum()
    for v in (5, 5):
        s.add(v)
    assert s.result() == 10
    m = Mean()
    assert m.result() is None, "empty Mean is None"
    m.add(10)
    m.add(20)
    assert m.result() == 15.0


def pipeline_checks():
    from aggregators import Count
    from event import Event
    from pipeline import Pipeline
    p = Pipeline(size=100, lateness=10, aggregator_factory=Count)
    p.push(Event(0, "k", 1))
    p.push(Event(50, "k", 1))
    p.push(Event(5, "k", 1))     # on-time still (wm=-10..40 -> late? check)
    # wm after ts=50 is 40; event ts=5 < 40 -> late, dropped
    p.push(Event(110, "k", 1))   # wm=100 -> fires window 0
    assert p.results == [("k", 0, 2)], f"results: {p.results}"


def late_drop_checks():
    from aggregators import Sum
    from event import Event
    from pipeline import Pipeline
    p = Pipeline(size=100, lateness=10, aggregator_factory=Sum)
    p.push(Event(200, "k", 100))
    out = p.push(Event(0, "k", 999))   # wm=190; ts=0 late -> drop
    assert out == [] and ("k", 0, 999) not in p.results


def once_only_checks():
    from aggregators import Count
    from event import Event
    from pipeline import Pipeline
    p = Pipeline(size=100, lateness=5, aggregator_factory=Count)
    p.push(Event(10, "a", 1))
    p.push(Event(105, "a", 1))  # wm=100 fires window 0
    p.push(Event(120, "a", 1))  # wm=115, window 1 pending
    assert p.results == [("a", 0, 1)], "window fires exactly once"
    p.push(Event(210, "a", 1))  # wm=205 fires window 1
    assert p.results == [("a", 0, 1), ("a", 1, 2)]


def per_key_checks():
    from aggregators import Sum
    from event import Event
    from pipeline import Pipeline
    p = Pipeline(size=10, lateness=0, aggregator_factory=Sum)
    p.push(Event(1, "a", 10))
    p.push(Event(1, "b", 20))
    p.push(Event(10, "x", 1))   # wm=10 fires window 0 for a,b,x
    results = sorted(p.results)
    assert ("a", 0, 10) in results and ("b", 0, 20) in results


for fn in (watermark_checks, window_checks, aggregator_checks,
           pipeline_checks, late_drop_checks, once_only_checks,
           per_key_checks):
    check(fn)
print("ALL CHECKS PASSED")
