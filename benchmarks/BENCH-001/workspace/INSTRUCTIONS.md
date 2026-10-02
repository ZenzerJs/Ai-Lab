# BENCH-001: Date Range Helper Boundary Fix

## Assignment
Fix the date range generator in `date_range.py`. The current implementation contains boundary defects where the exclusive end date is incorrectly included or start date handling fails, and reversed or invalid inputs are not properly handled according to the contract.

## Public API Contract
Function: `generate_date_range(start_date: str | datetime.date, end_date: str | datetime.date, step_days: int = 1) -> list[str]`

- **Inclusive start, exclusive end**: Return a list of ISO date strings (`YYYY-MM-DD`) starting at `start_date` up to, but not including, `end_date`.
- **Equal boundary**: If `start_date == end_date`, return an empty list `[]`.
- **Single-day range**: For consecutive days (e.g. `2026-06-01` to `2026-06-02`), return `["2026-06-01"]`.
- **Reversed range**: If `start_date > end_date`, raise `ValueError("start_date must not be after end_date")`.
- **Invalid inputs**: If date strings cannot be parsed as `YYYY-MM-DD`, raise `ValueError("Invalid date format, expected YYYY-MM-DD")`.
- **Step days**: If `step_days <= 0`, raise `ValueError("step_days must be a positive integer")`.
- **Transitions**: Handle month and year boundaries correctly (e.g., 2025-12-30 to 2026-01-02, leap years).
- **Types**: Accept both `str` (`YYYY-MM-DD`) and `datetime.date` objects for `start_date` and `end_date`.

## Constraints
Preserve the existing module name `date_range.py` and function signature.
