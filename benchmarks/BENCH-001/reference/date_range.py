"""
date_range.py - Reference solution for BENCH-001.
"""
from datetime import date, datetime, timedelta
from typing import Union


def _parse_date(d: Union[str, date]) -> date:
    if isinstance(d, date):
        return d
    if not isinstance(d, str):
        raise ValueError("Date must be str or datetime.date")
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid date format, expected YYYY-MM-DD: {exc}") from exc


def generate_date_range(
    start_date: Union[str, date],
    end_date: Union[str, date],
    step_days: int = 1,
) -> list[str]:
    """
    Generate ISO date strings starting at start_date (inclusive) up to end_date (exclusive).
    """
    if step_days <= 0:
        raise ValueError("step_days must be a positive integer")

    start = _parse_date(start_date)
    end = _parse_date(end_date)

    if start > end:
        raise ValueError("start_date must not be after end_date")

    if start == end:
        return []

    current = start
    step = timedelta(days=step_days)
    results = []

    while current < end:
        results.append(current.isoformat())
        current += step

    return results
