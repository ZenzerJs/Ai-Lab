"""Next-run enumeration for cron schedules."""
from datetime import datetime, timedelta, timezone

from zoneinfo import ZoneInfo

from matcher import matches


def next_runs(schedule, after, tz, count):
    """Return the next `count` matching instants at or after `after`."""
    if isinstance(tz, str):
        tz = ZoneInfo(tz)
    if count < 1:
        raise ValueError("count must be positive")
    naive = after.astimezone(tz).replace(second=0, microsecond=0).replace(tzinfo=None)
    results = []
    while len(results) < count:
        if matches(schedule, naive):
            results.append(naive.replace(tzinfo=tz))
        naive += timedelta(minutes=1)
    return results


def next_run(schedule, after, tz):
    return next_runs(schedule, after, tz, 1)[0]
