"""
date_range.py - Date range generator helper.
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
    """
    Generate ISO date strings from start_date up to end_date.
    """
    # BROKEN: Off-by-one boundary (<= includes end_date instead of exclusive)
    # BROKEN: start_date == end_date yields [start_date] instead of []
    # BROKEN: No validation for start_date > end_date (reversed) or step_days <= 0
    start = _parse_date(start_date)
    end = _parse_date(end_date)

    current = start
    step = timedelta(days=step_days)
    results = []

    # Boundary bug: current <= end incorrectly includes exclusive end date
    while current <= end:
        results.append(current.isoformat())
        current += step

    return results
