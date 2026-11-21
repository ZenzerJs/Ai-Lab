"""DST-aware next-run enumeration for cron schedules."""
from datetime import datetime, timedelta, timezone

from zoneinfo import ZoneInfo

from matcher import matches

_SEARCH_LIMIT = timedelta(days=366 * 5)
# Any zone's UTC offset stays within +/-14h, so a wall minute's instants
# can fall at most 14h away from the scan cursor.
_OFFSET_SPAN = timedelta(hours=14)


def _localize(tz, naive):
    """UTC instants a wall-clock minute maps to.

    Empty for nonexistent times (spring-forward gap); one instant for
    normal times; both occurrences for ambiguous times (fall-back).
    """
    instants = set()
    for fold in (0, 1):
        aware = naive.replace(tzinfo=tz, fold=fold)
        utc = aware.astimezone(timezone.utc)
        if utc.astimezone(tz).replace(tzinfo=None) == naive:
            instants.add(utc)
    return instants


def next_runs(schedule, after, tz, count):
    """Return the next `count` matching instants strictly after `after`.

    `tz` is a zoneinfo.ZoneInfo or an IANA timezone name. Skipped
    wall-clock times (DST gaps) never match; ambiguous times yield their
    first (fold=0) occurrence unless that instant is already past `after`,
    in which case the second occurrence applies. Raises ValueError when
    `count` < 1 or no further run exists within five years.
    """
    if isinstance(tz, str):
        tz = ZoneInfo(tz)
    if count < 1:
        raise ValueError("count must be positive")
    after_utc = after.astimezone(timezone.utc)
    # Start 14h early: second (fold=1) occurrences of earlier wall minutes
    # can still land after `after`.
    naive = after.astimezone(tz).replace(second=0, microsecond=0,
                                       tzinfo=None) - _OFFSET_SPAN
    deadline = naive + _SEARCH_LIMIT
    instants = sorted(set())
    while True:
        if naive > deadline:
            if len(instants) >= count:
                break
            raise ValueError("no matching run within five years")
        # A wall minute maps no earlier than naive - 14h; once the count-th
        # result precedes that bound no earlier instant can still appear.
        if len(instants) >= count \
                and naive - _OFFSET_SPAN > instants[count - 1].replace(tzinfo=None):
            break
        if matches(schedule, naive):
            future = sorted(u for u in _localize(tz, naive) if u > after_utc)
            if future:
                instants = sorted(instants + [future[0]])
        naive += timedelta(minutes=1)
    return [u.astimezone(tz) for u in instants[:count]]


def next_run(schedule, after, tz):
    return next_runs(schedule, after, tz, 1)[0]
