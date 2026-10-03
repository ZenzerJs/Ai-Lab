"""
date_range.py - Deliberately flawed solution for BENCH-001.
Merely changes <= to < without input validation for reversed or invalid ranges.
"""
from datetime import date, datetime, timedelta
from typing import Union


def _parse_date(d: Union[str, date]) -> date:
    if isinstance(d, date):
        return d
    return datetime.strptime(d, "%Y-%m-%d").date()


def generate_date_range(
    start_date: Union[str, date],
    end_date: Union[str, date],
    step_days: int = 1,
) -> list[str]:
    # Flawed: changed loop condition to < but omitted reversed range validation,
    # invalid step_days validation, and invalid date string handling.
    start = _parse_date(start_date)
    end = _parse_date(end_date)

    current = start
    step = timedelta(days=step_days)
    results = []

    # Flawed: If start > end, this returns [] instead of raising ValueError as contract requires!
    while current < end:
        results.append(current.isoformat())
        current += step

    return results
