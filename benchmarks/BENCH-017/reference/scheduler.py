"""DST-aware next-run enumeration for cron schedules."""
from datetime import datetime, timedelta, timezone

from zoneinfo import ZoneInfo

from matcher import matches

_SEARCH_LIMIT = timedelta(days=366 * 5)


def _localize(tz, naive):
    """Attach tz to a naive wall-clock datetime.

    Returns None for nonexistent wall-clock times (spring-forward gap);
    ambiguous times (fall-back overlap) resolve to the first occurrence.
    """
    aware = naive.replace(tzinfo=tz)  # fold defaults to 0
    roundtrip = aware.astimezone(timezone.utc).astimezone(tz)
    if roundtrip.replace(tzinfo=None) != naive:
        return None
    return aware


def next_runs(schedule, after, tz, count):
    """Return the next `count` matching instants strictly after `after`.

    `tz` is a zoneinfo.ZoneInfo or an IANA timezone name. Skipped
    wall-clock times (DST gaps) never match; ambiguous times yield their
    first (fold=0) occurrence only. Raises ValueError when `count` < 1 or
    no further run exists within five years.
    """
    if isinstance(tz, str):
        tz = ZoneInfo(tz)
    if count < 1:
        raise ValueError("count must be positive")
    cursor = after.astimezone(tz).replace(second=0, microsecond=0) + timedelta(minutes=1)
    naive = cursor.replace(tzinfo=None)
    deadline = naive + _SEARCH_LIMIT
    results = []
    while len(results) < count:
        if naive > deadline:
            raise ValueError("no matching run within five years")
        if matches(schedule, naive):
            aware = _localize(tz, naive)
            if aware is not None:
                results.append(aware)
        naive += timedelta(minutes=1)
    return results


def next_run(schedule, after, tz):
    return next_runs(schedule, after, tz, 1)[0]
