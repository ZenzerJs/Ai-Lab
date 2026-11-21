"""Cron schedule matching against datetimes."""
from models import ALL_DAYS, ALL_WEEKDAYS


def cron_weekday(dt):
    """cron weekday for a datetime: Sunday=0 ... Saturday=6."""
    return (dt.weekday() + 1) % 7


def matches(schedule, dt):
    """True when dt's wall-clock fields satisfy the schedule.

    When both day-of-month and weekday are restricted (not the full range),
    a match on either suffices (classic cron OR semantics); otherwise both
    apply conjunctively.
    """
    if dt.minute not in schedule.minute:
        return False
    if dt.hour not in schedule.hour:
        return False
    if dt.month not in schedule.month:
        return False
    day_ok = dt.day in schedule.day
    weekday_ok = cron_weekday(dt) in schedule.weekday
    if schedule.day != ALL_DAYS and schedule.weekday != ALL_WEEKDAYS:
        return day_ok or weekday_ok
    return day_ok and weekday_ok
