"""Visible smoke tests for BENCH-033."""
from aggregators import Count
from event import Event
from pipeline import Pipeline
from watermark import Watermark


def test_watermark_max():
    w = Watermark(5)
    assert w.observe(20) == 15
    assert w.observe(10) == 15


def test_pipeline_counts():
    p = Pipeline(size=10, lateness=0, aggregator_factory=Count)
    p.push(Event(1, "a", 1))
    p.push(Event(3, "a", 1))
    p.push(Event(10, "a", 1))
    assert ("a", 0, 2) in p.results
