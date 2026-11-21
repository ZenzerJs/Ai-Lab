from datetime import datetime, timezone

from parser import parse
from scheduler import next_run


def test_parse_smoke():
    schedule = parse("*/15 9 * * MON-FRI")
    assert schedule.minute == frozenset({0, 15, 30, 45})
    assert schedule.hour == frozenset({9})


def test_next_run_smoke():
    schedule = parse("0 9 * * *")
    nxt = next_run(schedule, datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc), "UTC")
    assert nxt == datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
