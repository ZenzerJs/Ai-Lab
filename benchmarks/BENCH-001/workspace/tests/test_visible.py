"""
test_visible.py - Accessible tests for BENCH-001.
"""
from date_range import generate_date_range


def test_basic_progression():
    """Verify basic date progression starts at start_date."""
    res = generate_date_range("2026-05-01", "2026-05-05")
    assert len(res) >= 4
    assert res[0] == "2026-05-01"
