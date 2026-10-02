"""
test_visible.py - Accessible tests for BENCH-004.
"""
from filter_table import TableFilterController


def test_initial_state_loads():
    controller = TableFilterController()
    state = controller.get_view_state()
    assert state["total_count"] == 50
    assert len(state["displayed_rows"]) == 50
