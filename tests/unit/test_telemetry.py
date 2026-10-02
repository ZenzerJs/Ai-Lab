import json
import sqlite3
from pathlib import Path
import pytest

import ledger


def test_tel_01_malformed_syntax_and_invalid_event():
    """
    TEL-01: Parse malformed NDJSON and invalid event fields.
    Expected: Useful validation error with event location; no accidental valid-run record.
    """
    stream_malformed_json = """{"event": "start", "task_id": "T1", "arm": "baseline", "model": "m1"}
{"event": "turn", "turn": 1, "usage": {INVALID JSON HERE}}
{"event": "run_complete"}"""

    with pytest.raises(ledger.TelemetryValidationError) as exc_info:
        ledger.validate_and_parse_telemetry(stream_malformed_json)

    assert exc_info.value.line_number == 2
    assert "Line 2" in str(exc_info.value)
    assert "Malformed NDJSON syntax" in str(exc_info.value)

    # Event that is not a JSON object (e.g. array)
    stream_non_object = """{"event": "start", "task_id": "T1"}
[1, 2, 3]
{"event": "run_complete"}"""

    with pytest.raises(ledger.TelemetryValidationError) as exc_info2:
        ledger.validate_and_parse_telemetry(stream_non_object)

    assert exc_info2.value.line_number == 2
    assert "Line 2" in str(exc_info2.value)
    assert "Event must be a JSON object" in str(exc_info2.value)


def test_tel_02_omitted_usage_unknown_not_zero(tmp_path: Path):
    """
    TEL-02: Omit usage counters from a completed run.
    Expected: Usage remains unknown (None); not zero.
    """
    stream_no_usage = """{"event": "start", "task_id": "T-NO-USAGE", "arm": "icm", "model": "gemini-2.5-pro"}
{"event": "turn", "turn": 1}
{"event": "run_complete", "duration_seconds": 12.0}"""

    parsed = ledger.validate_and_parse_telemetry(stream_no_usage)
    assert parsed["has_usage"] is False
    assert parsed["usage"]["input_tokens"] is None
    assert parsed["usage"]["output_tokens"] is None
    assert parsed["usage"]["total_tokens"] is None

    # Test database recording with omitted usage
    db_file = tmp_path / "tel02.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    run_id = ledger.record_run(
        task_id="T-NO-USAGE",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=None,
        output_tokens=None,
        num_turns=1,
        duration_seconds=12.0,
        source_kind="live",
        evidence_status="verified",
        conn=conn,
    )

    cursor = conn.cursor()
    cursor.execute("SELECT input_tokens, output_tokens, total_tokens, cost_status, exclusion_reasons FROM runs WHERE id = ?", (run_id,))
    row = dict(cursor.fetchone())
    assert row["input_tokens"] is None
    assert row["output_tokens"] is None
    assert row["cost_status"] == "unavailable"

    reasons = json.loads(row["exclusion_reasons"])
    assert "missing_usage_telemetry" in reasons

    # Summary excludes it from measured runs
    summary = ledger.task_summary("T-NO-USAGE", conn=conn)
    assert summary["measured_runs_count"] == 0
    assert summary["has_measured_data"] is False

    conn.close()


def test_tel_03_negative_counts_or_invalid_numeric():
    """
    TEL-03: Supply negative counts or invalid numeric values.
    Expected: Input rejected according to documented validation policy.
    """
    # Negative counter in turn event
    stream_neg = """{"event": "turn", "turn": 1, "usage": {"input_tokens": -50, "output_tokens": 10}}"""
    with pytest.raises(ledger.TelemetryValidationError) as exc1:
        ledger.validate_and_parse_telemetry(stream_neg)
    assert exc1.value.line_number == 1
    assert "cannot be negative" in str(exc1.value)

    # Float in integer token counter
    stream_float = """{"event": "turn", "turn": 1, "usage": {"input_tokens": 120.75, "output_tokens": 10}}"""
    with pytest.raises(ledger.TelemetryValidationError) as exc2:
        ledger.validate_and_parse_telemetry(stream_float)
    assert exc2.value.line_number == 1
    assert "cannot be a non-integer float" in str(exc2.value)

    # Boolean in integer token counter
    stream_bool = """{"event": "turn", "turn": 1, "usage": {"input_tokens": True, "output_tokens": 10}}"""
    # Note: in json valid boolean is true
    stream_bool_json = """{"event": "turn", "turn": 1, "usage": {"input_tokens": true, "output_tokens": 10}}"""
    with pytest.raises(ledger.TelemetryValidationError) as exc3:
        ledger.validate_and_parse_telemetry(stream_bool_json)
    assert exc3.value.line_number == 1
    assert "got boolean" in str(exc3.value)

    # Non-numeric string
    stream_str = """{"event": "turn", "turn": 1, "usage": {"input_tokens": "one_hundred"}}"""
    with pytest.raises(ledger.TelemetryValidationError) as exc4:
        ledger.validate_and_parse_telemetry(stream_str)
    assert exc4.value.line_number == 1
    assert "must be an integer" in str(exc4.value)

    # Negative duration
    stream_neg_dur = """{"event": "run_complete", "duration_seconds": -3.5}"""
    with pytest.raises(ledger.TelemetryValidationError) as exc5:
        ledger.validate_and_parse_telemetry(stream_neg_dur)
    assert exc5.value.line_number == 1
    assert "cannot be negative" in str(exc5.value)


def test_tel_04_replayed_turn_events_deduplicated():
    """
    TEL-04: Replay duplicated events.
    Expected: No double counting; documented duplicate handling.
    """
    stream_with_dupes = """{"event": "start", "task_id": "T-DEDUP", "arm": "baseline", "model": "gemini-2.5-pro"}
{"event": "turn", "turn": 1, "usage": {"input_tokens": 1000, "output_tokens": 200}}
{"event": "turn", "turn": 1, "usage": {"input_tokens": 1000, "output_tokens": 200}}
{"event": "turn", "turn": 2, "usage": {"input_tokens": 1500, "output_tokens": 300}}"""

    parsed = ledger.validate_and_parse_telemetry(stream_with_dupes)
    # Turn 1 should only be counted once: 1000 + 1500 = 2500, 200 + 300 = 500
    assert parsed["usage"]["input_tokens"] == 2500
    assert parsed["usage"]["output_tokens"] == 500

    # Conflicting turn usage with same turn number must raise error
    stream_conflicting_turn = """{"event": "turn", "turn": 1, "usage": {"input_tokens": 1000, "output_tokens": 200}}
{"event": "turn", "turn": 1, "usage": {"input_tokens": 9999, "output_tokens": 200}}"""
    with pytest.raises(ledger.TelemetryValidationError) as exc:
        ledger.validate_and_parse_telemetry(stream_conflicting_turn)
    assert "Conflicting turn usage" in str(exc.value)


def test_tel_05_cumulative_plus_per_turn_counters():
    """
    TEL-05: Supply cumulative counters plus per-turn counters.
    Expected: Correct total under the declared adapter schema; no double summation.
    """
    stream_hybrid = """{"event": "start", "task_id": "T-HYBRID", "arm": "baseline", "model": "gemini-2.5-pro"}
{"event": "turn", "turn": 1, "usage": {"input_tokens": 1000, "output_tokens": 100}}
{"event": "turn", "turn": 2, "usage": {"input_tokens": 2000, "output_tokens": 200}}
{"event": "turn", "turn": 3, "usage": {"input_tokens": 3000, "output_tokens": 300}}
{"event": "run_complete", "num_turns": 3, "duration_seconds": 15.0, "usage": {"input_tokens": 6000, "output_tokens": 600, "total_tokens": 6600}}"""

    parsed = ledger.validate_and_parse_telemetry(stream_hybrid)
    # Must use cumulative run_complete usage (6000, 600), NOT sum of turns + run_complete (12000, 1200)
    assert parsed["usage"]["input_tokens"] == 6000
    assert parsed["usage"]["output_tokens"] == 600
    assert parsed["usage"]["total_tokens"] == 6600
    assert parsed["num_turns"] == 3
    assert parsed["duration_seconds"] == 15.0


def test_tel_02_multiple_turns_omitted_usage():
    """
    TEL-02: Completed run with multiple turns where usage is omitted.
    Expected: Usage fields remain None (not coerced to 0); has_usage is False.
    """
    stream = """{"event": "start", "task_id": "T-MULTI-NO-USAGE", "arm": "icm", "model": "gemini-2.5-pro"}
{"event": "turn", "turn": 1}
{"event": "turn", "turn": 2}
{"event": "run_complete", "duration_seconds": 5.0}"""
    parsed = ledger.validate_and_parse_telemetry(stream)
    assert parsed["has_usage"] is False
    assert parsed["usage"]["input_tokens"] is None
    assert parsed["usage"]["output_tokens"] is None
    assert parsed["usage"]["thinking_tokens"] is None
    assert parsed["usage"]["cache_read_tokens"] is None
    assert parsed["usage"]["total_tokens"] is None
    assert parsed["num_turns"] == 2


def test_tel_05_conflicting_run_complete_events():
    """
    TEL-05: Stream contains multiple conflicting run_complete events.
    Expected: TelemetryValidationError raised on conflicting summary events.
    """
    stream_conflict = """{"event": "start", "task_id": "T-CONFLICT-COMPLETE", "arm": "baseline", "model": "gemini-2.5-pro"}
{"event": "run_complete", "num_turns": 1, "duration_seconds": 10.0, "usage": {"input_tokens": 1000, "output_tokens": 100}}
{"event": "run_complete", "num_turns": 2, "duration_seconds": 15.0, "usage": {"input_tokens": 2000, "output_tokens": 200}}"""
    with pytest.raises(ledger.TelemetryValidationError, match="conflicting run_complete"):
        ledger.validate_and_parse_telemetry(stream_conflict)

