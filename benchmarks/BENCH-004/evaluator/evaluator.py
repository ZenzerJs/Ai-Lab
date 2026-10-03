"""
evaluator.py - Protected evaluator for BENCH-004.
Verifies stateful filter controller: count synchronization, reset handling,
keyboard Escape behavior, and race condition prevention.
"""
import sys


def run_checks():
    try:
        from filter_table import TableFilterController
    except Exception as exc:
        print(f"REASON: import_error\nFailed to import TableFilterController: {exc}", file=sys.stderr)
        sys.exit(1)

    controller = TableFilterController()

    # Check 1: Filter updates both displayed rows and matching_count
    controller.set_search("widget")
    s1 = controller.get_view_state()
    row_count = len(s1["displayed_rows"])

    if s1["matching_count"] != row_count:
        print("REASON: stale_filter_state_or_count", file=sys.stderr)
        print(f"Filter matching_count ({s1['matching_count']}) is desynchronized from displayed rows ({row_count}).", file=sys.stderr)
        sys.exit(1)

    if row_count == 0 or row_count >= 50:
        print("REASON: filter_logic_error", file=sys.stderr)
        print(f"Unexpected row count for query 'widget': {row_count}", file=sys.stderr)
        sys.exit(1)

    # Check 2: Clear filters restores complete dataset and resets filters
    controller.set_category("sensors")
    controller.clear_filters()
    s2 = controller.get_view_state()

    if s2["matching_count"] != 50 or len(s2["displayed_rows"]) != 50:
        print("REASON: stale_filter_state_or_count", file=sys.stderr)
        print(f"clear_filters() did not restore complete dataset. Rows: {len(s2['displayed_rows'])}, matching_count: {s2['matching_count']}", file=sys.stderr)
        sys.exit(1)

    if s2["active_filters"].get("query") != "" or s2["active_filters"].get("category") is not None:
        print("REASON: stale_filter_state_or_count", file=sys.stderr)
        print(f"clear_filters() failed to reset active filter fields: {s2['active_filters']}", file=sys.stderr)
        sys.exit(1)

    # Check 3: Keyboard Escape resets active filters and restores full count
    controller.set_category("sensors")
    controller.set_search("acoustic")
    s3_pre = controller.get_view_state()
    if s3_pre["matching_count"] >= 50:
        print("REASON: filter_logic_error", file=sys.stderr)
        print(f"Category + search filtering did not narrow results: {s3_pre['matching_count']}", file=sys.stderr)
        sys.exit(1)

    controller.handle_key_event("Escape")
    s3_post = controller.get_view_state()
    if s3_post["matching_count"] != 50 or len(s3_post["displayed_rows"]) != 50:
        print("REASON: keyboard_reset_unhandled", file=sys.stderr)
        print(f"handle_key_event('Escape') did not reset filters. Rows: {len(s3_post['displayed_rows'])}", file=sys.stderr)
        sys.exit(1)

    # Check 4: Rapid async sequence updates prevent race conditions
    controller.apply_async_query("gadget", sequence_id=1)
    controller.apply_async_query("tool", sequence_id=3)
    controller.apply_async_query("gadget", sequence_id=2)  # Stale out-of-order sequence arriving late!

    s4 = controller.get_view_state()
    active_q = s4["active_filters"].get("query")
    if active_q != "tool":
        print("REASON: stale_filter_state_or_count", file=sys.stderr)
        print(f"Async race condition: stale sequence 2 overwrote newer sequence 3! Active query: '{active_q}'", file=sys.stderr)
        sys.exit(1)

    # Check 5: Empty results state
    controller.set_search("xyz_completely_nonexistent_token_12345")
    s5 = controller.get_view_state()
    if not s5["is_empty"] or s5["matching_count"] != 0:
        print("REASON: empty_state_mismatch", file=sys.stderr)
        print(f"Empty results state failed: is_empty={s5['is_empty']}, count={s5['matching_count']}", file=sys.stderr)
        sys.exit(1)

    if s5["empty_message"] != "No records match the active filters":
        print("REASON: empty_state_mismatch", file=sys.stderr)
        print(f"Incorrect empty state message: {s5['empty_message']!r}", file=sys.stderr)
        sys.exit(1)

    print("ALL CHECKS PASSED")
    sys.exit(0)


if __name__ == "__main__":
    run_checks()
