"""
test_visible.py - Accessible tests for BENCH-002.
"""
from api_server import handle_health_check


def test_health_check_preserved():
    """Verify health check endpoint is functional."""
    res = handle_health_check()
    assert res["status"] == "healthy"
    assert res["version"] == "1.2.0"
