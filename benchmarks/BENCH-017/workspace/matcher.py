"""Cron schedule matching against datetimes."""


def cron_weekday(dt):
    """cron weekday for a datetime."""
    return dt.weekday()


def matches(schedule, dt):
    """True when dt's wall-clock fields satisfy the schedule."""
    return (
        dt.minute in schedule.minute
        and dt.hour in schedule.hour
        and dt.month in schedule.month
        and dt.day in schedule.day
        and cron_weekday(dt) in schedule.weekday
    )
