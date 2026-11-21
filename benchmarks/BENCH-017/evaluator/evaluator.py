"""Protected deterministic checks for BENCH-017."""
from datetime import datetime, timedelta, timezone
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from zoneinfo import ZoneInfo
        from models import MINUTE, HOUR, DAY, MONTH, WEEKDAY, CronSchedule
        from parser import parse, parse_field
        from matcher import cron_weekday, matches
        from scheduler import next_run, next_runs

        def parse_checks():
            assert parse_field("*/15", MINUTE) == frozenset({0, 15, 30, 45})
            assert parse_field("9-17/2", HOUR) == frozenset({9, 11, 13, 15, 17})
            assert parse_field("1,15,31", DAY) == frozenset({1, 15, 31})
            assert parse_field("JAN-MAR", MONTH) == frozenset({1, 2, 3})
            assert parse_field("dec,jan", MONTH) == frozenset({12, 1})
            assert parse_field("fri", WEEKDAY) == frozenset({5})
            assert parse_field("7", WEEKDAY) == frozenset({0})
            assert parse_field("SUN,mon-SAT", WEEKDAY) == frozenset(range(7))
            assert parse_field("10/10", MINUTE) == frozenset(range(10, 60, 10))
            assert parse_field("*", DAY) == frozenset(range(1, 32))
            for bad in ("*/0", "*/-2", "60", "-1", "5-3", "", "  ", "JANUARY",
                        "1,,2", "1/2/3", "x-y", "5-", "*/abc"):
                rejected(ValueError, lambda: parse_field(bad, MINUTE))
            rejected(ValueError, lambda: parse_field("24", HOUR))
            rejected(ValueError, lambda: parse_field("0", MONTH))
            rejected(ValueError, lambda: parse_field("8", WEEKDAY))
            rejected(ValueError, lambda: parse("1 2 3 4"))
            rejected(ValueError, lambda: parse("1 2 3 4 5 6"))
            rejected(ValueError, lambda: parse("* * * * x"))
            rejected(ValueError, lambda: parse(None))
            schedule = parse("  0  9 *  JAN-MAR   MON-FRI ")
            assert schedule.hour == frozenset({9})
            assert schedule.month == frozenset({1, 2, 3})
            assert schedule.weekday == frozenset({1, 2, 3, 4, 5})
            assert isinstance(schedule, CronSchedule) and schedule.raw

        def matcher_checks():
            assert cron_weekday(datetime(2026, 11, 1)) == 0  # Sunday
            assert cron_weekday(datetime(2026, 11, 2)) == 1  # Monday
            daily = parse("0 0 * * *")
            assert matches(daily, datetime(2026, 3, 8, 0, 0))
            assert not matches(daily, datetime(2026, 3, 8, 0, 1))
            both = parse("0 0 15 * FRI")
            assert matches(both, datetime(2026, 5, 15))      # 15th, Friday
            assert matches(both, datetime(2026, 5, 8))       # Friday, not 15th
            assert matches(both, datetime(2026, 4, 15))      # 15th, not Friday
            assert not matches(both, datetime(2026, 5, 9))    # neither 15th nor Friday
            only_dom = parse("0 0 13 * *")
            assert matches(only_dom, datetime(2026, 11, 13))   # Friday the 13th
            assert not matches(only_dom, datetime(2026, 11, 12))
            only_dow = parse("0 0 * * SAT")
            assert matches(only_dow, datetime(2026, 11, 7))
            assert not matches(only_dow, datetime(2026, 11, 8))

        def scheduler_checks():
            utc = timezone.utc
            ny = ZoneInfo("America/New_York")
            every = parse("* * * * *")
            assert next_run(every, datetime(2026, 1, 1, 0, 0, 0, tzinfo=utc), utc) == \
                datetime(2026, 1, 1, 0, 1, tzinfo=utc)
            assert next_run(every, datetime(2026, 1, 1, 0, 0, 30, tzinfo=utc), utc) == \
                datetime(2026, 1, 1, 0, 1, tzinfo=utc)
            runs = next_runs(parse("0 9-17 * * MON-FRI"),
                             datetime(2026, 11, 20, 16, 0, tzinfo=utc), utc, 3)
            assert runs == [datetime(2026, 11, 20, 17, 0, tzinfo=utc),
                            datetime(2026, 11, 23, 9, 0, tzinfo=utc),
                            datetime(2026, 11, 23, 10, 0, tzinfo=utc)]
            rejected(ValueError, lambda: next_runs(every, datetime(2026, 1, 1, tzinfo=utc), utc, 0))
            rejected(ValueError, lambda: next_run(parse("0 0 31 2 *"),
                                                datetime(2026, 1, 1, tzinfo=utc), utc))

        def dst_checks():
            ny = "America/New_York"
            # Spring forward 2026-03-08: 02:00-02:59 never occurs.
            after = datetime(2026, 3, 7, 12, 0, tzinfo=ZoneInfo(ny))
            first = next_run(parse("30 2 * * *"), after, ny)
            assert first.replace(tzinfo=None) == datetime(2026, 3, 9, 2, 30)
            assert first.utcoffset() == timedelta(hours=-4)
            skipped = next_runs(parse("* 2 * * *"), after, ny, 3)
            assert [r.replace(tzinfo=None) for r in skipped] == [
                datetime(2026, 3, 9, 2, 0), datetime(2026, 3, 9, 2, 1),
                datetime(2026, 3, 9, 2, 2)]
            # Fall back 2026-11-01: 01:30 occurs once; fold=0 (EDT) wins.
            after2 = datetime(2026, 10, 31, 12, 0, tzinfo=ZoneInfo(ny))
            pair = next_runs(parse("30 1 * * *"), after2, ny, 2)
            assert pair[0].replace(tzinfo=None) == datetime(2026, 11, 1, 1, 30)
            assert pair[0].utcoffset() == timedelta(hours=-4)
            assert pair[0].fold == 0
            assert pair[1].replace(tzinfo=None) == datetime(2026, 11, 2, 1, 30)
            assert pair[1].utcoffset() == timedelta(hours=-5)
            assert pair[0].astimezone(timezone.utc) == datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc)
            # Inside the repeated hour (1:30 EST), strictly-after holds by instant.
            after3 = datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc)
            nxt = next_run(parse("45 1 * * *"), after3, ny)
            assert nxt.astimezone(timezone.utc) > after3
            assert nxt.replace(tzinfo=None) == datetime(2026, 11, 1, 1, 45)
            assert nxt.fold == 1
            assert nxt.utcoffset() == timedelta(hours=-5)
            # Hourly schedule across the fall-back night sees each wall hour once.
            hourly = next_runs(parse("15 * * * *"), after2, ny, 4)
            assert [r.replace(tzinfo=None) for r in hourly] == [
                datetime(2026, 10, 31, 12, 15), datetime(2026, 10, 31, 13, 15),
                datetime(2026, 10, 31, 14, 15), datetime(2026, 10, 31, 15, 15)]
            runs = next_runs(parse("* * * * *"),
                             datetime(2026, 10, 31, 23, 59, tzinfo=ZoneInfo(ny)), ny, 150)
            nov1 = [r for r in runs if r.date() == datetime(2026, 11, 1).date()]
            wall = [r.replace(tzinfo=None) for r in nov1]
            assert len(wall) == len(set(wall))
            assert datetime(2026, 11, 1, 1, 30) in wall

        for check in (parse_checks, matcher_checks, scheduler_checks, dst_checks):
            try:
                check()
            except Exception as exc:
                fail(f"{check.__name__}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        fail(f"import_error: {exc}")
    print("ALL CHECKS PASSED")


def fail(detail):
    print("REASON: cron_schedule_invariant_violation", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
