"""
evaluator.py - Protected evaluator for BENCH-001.
Evaluates date range generator contract against workspace implementation.
"""
import sys
from datetime import date


def run_checks():
    try:
        from date_range import generate_date_range
    except Exception as exc:
        print(f"REASON: import_error\nFailed to import generate_date_range: {exc}", file=sys.stderr)
        sys.exit(1)

    # Check 1: Inclusive start, exclusive end
    res = generate_date_range("2026-06-01", "2026-06-04")
    if "2026-06-04" in res:
        print("REASON: boundary_exclusive_end_included", file=sys.stderr)
        print("Exclusive end date '2026-06-04' was included in generated range.", file=sys.stderr)
        sys.exit(1)

    expected = ["2026-06-01", "2026-06-02", "2026-06-03"]
    if res != expected:
        print(f"REASON: boundary_exclusive_end_included\nExpected {expected}, got {res}", file=sys.stderr)
        sys.exit(1)

    # Check 2: Equal start and end returns empty list
    res_empty = generate_date_range("2026-06-01", "2026-06-01")
    if res_empty != []:
        print("REASON: boundary_equal_not_empty", file=sys.stderr)
        print(f"Equal start/end range returned non-empty list: {res_empty}", file=sys.stderr)
        sys.exit(1)

    # Check 3: Single day range
    res_single = generate_date_range("2026-06-01", "2026-06-02")
    if res_single != ["2026-06-01"]:
        print(f"REASON: boundary_single_day\nExpected ['2026-06-01'], got {res_single}", file=sys.stderr)
        sys.exit(1)

    # Check 4: Month and year transitions
    res_year = generate_date_range("2025-12-30", "2026-01-02")
    if res_year != ["2025-12-30", "2025-12-31", "2026-01-01"]:
        print(f"REASON: boundary_transition\nYear boundary failed: {res_year}", file=sys.stderr)
        sys.exit(1)

    res_leap = generate_date_range("2024-02-28", "2024-03-01")
    if res_leap != ["2024-02-28", "2024-02-29"]:
        print(f"REASON: boundary_transition\nLeap year transition failed: {res_leap}", file=sys.stderr)
        sys.exit(1)

    # Check 5: Step days
    res_step = generate_date_range("2026-06-01", "2026-06-05", step_days=2)
    if res_step != ["2026-06-01", "2026-06-03"]:
        print(f"REASON: boundary_step_days\nStep days failed: {res_step}", file=sys.stderr)
        sys.exit(1)

    # Check 6: datetime.date objects
    res_obj = generate_date_range(date(2026, 6, 1), date(2026, 6, 3))
    if res_obj != ["2026-06-01", "2026-06-02"]:
        print(f"REASON: date_object_support\nDate object handling failed: {res_obj}", file=sys.stderr)
        sys.exit(1)

    # Check 7: Reversed range validation
    try:
        generate_date_range("2026-06-05", "2026-06-01")
        print("REASON: missing_reversed_range_validation", file=sys.stderr)
        print("Reversed date range did not raise ValueError.", file=sys.stderr)
        sys.exit(1)
    except ValueError:
        pass
    except Exception as exc:
        print(f"REASON: missing_reversed_range_validation\nExpected ValueError, got {type(exc)}: {exc}", file=sys.stderr)
        sys.exit(1)

    # Check 8: Invalid date format validation
    try:
        generate_date_range("invalid-date-string", "2026-06-01")
        print("REASON: missing_invalid_date_validation", file=sys.stderr)
        print("Invalid date string did not raise ValueError.", file=sys.stderr)
        sys.exit(1)
    except ValueError:
        pass
    except Exception as exc:
        print(f"REASON: missing_invalid_date_validation\nExpected ValueError, got {type(exc)}: {exc}", file=sys.stderr)
        sys.exit(1)

    # Check 9: Non-positive step_days validation
    for bad_step in (0, -1, -5):
        try:
            generate_date_range("2026-06-01", "2026-06-05", step_days=bad_step)
            print("REASON: missing_invalid_step_validation", file=sys.stderr)
            print(f"step_days={bad_step} did not raise ValueError.", file=sys.stderr)
            sys.exit(1)
        except ValueError:
            pass
        except Exception as exc:
            print(f"REASON: missing_invalid_step_validation\nExpected ValueError for step_days={bad_step}, got {exc}", file=sys.stderr)
            sys.exit(1)

    print("ALL CHECKS PASSED")
    sys.exit(0)


if __name__ == "__main__":
    run_checks()
