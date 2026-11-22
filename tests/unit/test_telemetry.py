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


def test_extract_ndjson_cache_diagnostics_multistep_and_dedup():
    """
    Verify extract_ndjson_cache_diagnostics deduplicates step_update by step_index,
    orders by ascending step_index, excludes Turn-1 from avg_fresh_input_per_call,
    and computes tools_per_llm_call both automatically and when passed explicitly.
    """
    lines = [
        json.dumps({"event": "init", "init": {"model": "gemini-4-argon-low"}}),
        # Step 1 ACTIVE then DONE (out of order with step 4, should dedup and sort)
        json.dumps({"event": "step_update", "step_update": {"step_index": 1, "step_type": "agent_response", "state": "ACTIVE", "usage": None}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 4, "step_type": "agent_response", "state": "DONE", "usage": {"input_tokens": 2000, "output_tokens": 80, "cache_read_tokens": 22000}}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 1, "step_type": "agent_response", "state": "DONE", "usage": {"input_tokens": 24000, "output_tokens": 100, "cache_read_tokens": 0}}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 2, "step_type": "tool", "state": "DONE", "tool_name": "read_file"}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 3, "step_type": "tool", "state": "DONE", "tool_name": "edit_file"}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 5, "step_type": "tool", "state": "DONE", "tool_name": "run_command"}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 6, "step_type": "agent_response", "state": "DONE", "usage": {"input_tokens": 3000, "output_tokens": 120, "cache_read_tokens": 25000}}}),
    ]

    diag = ledger.extract_ndjson_cache_diagnostics(lines)
    assert diag["llm_calls_count"] == 3
    # Peak context: max(24000+0, 2000+22000, 3000+25000) = 28000
    assert diag["peak_context_tokens"] == 28000
    # Turn 2+ fresh input: mean(2000, 3000) = 2500.0 (Turn 1's 24000 excluded)
    assert diag["avg_fresh_input_per_call"] == pytest.approx(2500.0)
    # Cache monotonically increased: 0 -> 22000 -> 25000
    assert diag["cache_bust_count"] == 0
    # 3 tool steps / 3 llm calls = 1.0
    assert diag["tools_per_llm_call"] == pytest.approx(1.0)

    # Explicit tool_calls_count override
    diag_override = ledger.extract_ndjson_cache_diagnostics("\n".join(lines), tool_calls_count=6)
    assert diag_override["tools_per_llm_call"] == pytest.approx(2.0)


def test_extract_ndjson_cache_diagnostics_mid_run_cache_drop():
    """Verify simulated mid-run cache drop yields cache_bust_count == 1."""
    lines = [
        {"event": "step_update", "step_update": {"step_index": 1, "step_type": "agent_response", "state": "DONE", "usage": {"input_tokens": 20000, "cache_read_tokens": 0}}},
        {"event": "step_update", "step_update": {"step_index": 3, "step_type": "agent_response", "state": "DONE", "usage": {"input_tokens": 2000, "cache_read_tokens": 22000}}},
        {"event": "step_update", "step_update": {"step_index": 5, "step_type": "agent_response", "state": "DONE", "usage": {"input_tokens": 18000, "cache_read_tokens": 5000}}},
        {"event": "step_update", "step_update": {"step_index": 7, "step_type": "agent_response", "state": "DONE", "usage": {"input_tokens": 1500, "cache_read_tokens": 23000}}},
    ]

    diag = ledger.extract_ndjson_cache_diagnostics(lines)
    assert diag["llm_calls_count"] == 4
    assert diag["cache_bust_count"] == 1
    assert diag["peak_context_tokens"] == 24500
    assert diag["avg_fresh_input_per_call"] == pytest.approx((2000 + 18000 + 1500) / 3.0)


def test_extract_ndjson_cache_diagnostics_partial_missing_usage_returns_none():
    """Verify missing or partial step usage remains None and never fakes 0."""
    # 1. Empty / no agent_response usage
    empty_diag = ledger.extract_ndjson_cache_diagnostics([
        {"event": "step_update", "step_update": {"step_index": 1, "step_type": "agent_response", "state": "ACTIVE", "usage": None}},
        {"event": "step_update", "step_update": {"step_index": 2, "step_type": "tool", "state": "DONE", "tool_name": "read_file"}},
    ])
    assert empty_diag == {
        "llm_calls_count": None,
        "peak_context_tokens": None,
        "avg_fresh_input_per_call": None,
        "cache_bust_count": None,
        "tools_per_llm_call": None,
    }

    # 2. Single call: avg_fresh_input_per_call and cache_bust_count must be None
    single_diag = ledger.extract_ndjson_cache_diagnostics([
        {"event": "step_update", "step_update": {"step_index": 1, "step_type": "agent_response", "state": "DONE", "usage": {"input_tokens": 5000, "cache_read_tokens": 0}}},
    ])
    assert single_diag["llm_calls_count"] == 1
    assert single_diag["peak_context_tokens"] == 5000
    assert single_diag["avg_fresh_input_per_call"] is None
    assert single_diag["cache_bust_count"] is None
    assert single_diag["tools_per_llm_call"] == pytest.approx(0.0)

    # 3. Multiple calls with missing input_tokens / cache_read_tokens (only output_tokens)
    partial_diag = ledger.extract_ndjson_cache_diagnostics([
        {"event": "step_update", "step_update": {"step_index": 1, "step_type": "agent_response", "state": "DONE", "usage": {"output_tokens": 40}}},
        {"event": "step_update", "step_update": {"step_index": 2, "step_type": "agent_response", "state": "DONE", "usage": {"input_tokens": 1200, "cache_read_tokens": None, "output_tokens": 50}}},
    ])
    assert partial_diag["llm_calls_count"] == 2
    assert partial_diag["peak_context_tokens"] == 1200
    assert partial_diag["avg_fresh_input_per_call"] is None
    assert partial_diag["cache_bust_count"] is None

    # 4. Calls with neither input_tokens nor cache_read_tokens -> peak_context_tokens is None
    no_context_diag = ledger.extract_ndjson_cache_diagnostics([
        {"event": "step_update", "step_update": {"step_index": 1, "step_type": "agent_response", "state": "DONE", "usage": {"output_tokens": 40}}},
    ])
    assert no_context_diag["llm_calls_count"] == 1
    assert no_context_diag["peak_context_tokens"] is None


def test_record_run_to_public_run_and_backfill_cache_diagnostics(tmp_path: Path):
    """
    Verify record_run persists all 7 new columns, to_public_run exposes them,
    and backfill_cache_diagnostics_from_evidence populates NULL rows idempotently.
    """
    db_file = tmp_path / "diag_backfill.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    ev_rel = Path("ev.ndjson")
    ev_path = tmp_path / ev_rel
    ev_path.write_text(
        "\n".join([
            json.dumps({"event": "step_update", "step_update": {"step_index": 1, "step_type": "agent_response", "state": "DONE", "usage": {"input_tokens": 10000, "cache_read_tokens": 0}}}),
            json.dumps({"event": "step_update", "step_update": {"step_index": 2, "step_type": "tool", "state": "DONE", "tool_name": "read_file"}}),
            json.dumps({"event": "step_update", "step_update": {"step_index": 3, "step_type": "agent_response", "state": "DONE", "usage": {"input_tokens": 1500, "cache_read_tokens": 9000}}}),
        ]) + "\n",
        encoding="utf-8",
    )

    rid_explicit = ledger.record_run(
        task_id="T-DIAG",
        arm="icm",
        model="gemini-4-argon-low",
        run_index=1,
        timestamp="2026-11-22T00:00:00Z",
        input_tokens=11500,
        output_tokens=200,
        cache_read_tokens=9000,
        llm_calls_count=2,
        peak_context_tokens=10500,
        avg_fresh_input_per_call=1500.0,
        cache_bust_count=0,
        tools_per_llm_call=0.5,
        contract_version="v2.1",
        contract_hash="abc123",
        conn=conn,
    )
    row = dict(conn.execute("SELECT * FROM runs WHERE id = ?", (rid_explicit,)).fetchone())
    pub = ledger.to_public_run(row)
    assert pub["llm_calls_count"] == 2
    assert pub["peak_context_tokens"] == 10500
    assert pub["avg_fresh_input_per_call"] == pytest.approx(1500.0)
    assert pub["cache_bust_count"] == 0
    assert pub["tools_per_llm_call"] == pytest.approx(0.5)
    assert pub["contract_version"] == "v2.1"
    assert pub["contract_hash"] == "abc123"

    rid_backfill = ledger.record_run(
        task_id="T-DIAG",
        arm="baseline",
        model="gemini-4-argon-low",
        run_index=1,
        timestamp="2026-11-22T00:01:00Z",
        input_tokens=11500,
        output_tokens=200,
        cache_read_tokens=9000,
        evidence_ref=str(ev_rel),
        conn=conn,
    )
    assert ledger.backfill_cache_diagnostics_from_evidence(conn, workspace_root=tmp_path) == 1
    assert ledger.backfill_cache_diagnostics_from_evidence(conn, workspace_root=tmp_path) == 0

    bf_row = dict(conn.execute("SELECT * FROM runs WHERE id = ?", (rid_backfill,)).fetchone())
    assert bf_row["llm_calls_count"] == 2
    assert bf_row["peak_context_tokens"] == 10500
    assert bf_row["avg_fresh_input_per_call"] == pytest.approx(1500.0)
    assert bf_row["cache_bust_count"] == 0
    assert bf_row["tools_per_llm_call"] == pytest.approx(0.5)
    conn.close()


def test_runner_live_wires_cache_diagnostics_offline(tmp_path: Path, monkeypatch):
    """Verify runner.run_benchmark_live extracts and persists cache diagnostics offline."""
    import subprocess
    import runner

    task_dir = tmp_path / "benchmarks" / "BENCH-T"
    ws_src = task_dir / "workspace"
    eval_dir = task_dir / "evaluator"
    ws_src.mkdir(parents=True)
    eval_dir.mkdir(parents=True)
    (ws_src / "INSTRUCTIONS.md").write_text("# Task\nDo work.\n", encoding="utf-8")
    (eval_dir / "test_ok.py").write_text("def test_ok(): assert True\n", encoding="utf-8")

    db_file = tmp_path / "runner_diag.db"
    ev_dir = tmp_path / "evidence"
    ws_root = tmp_path / "tmp" / "workspaces"
    monkeypatch.setattr(runner, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(runner, "DEFAULT_EVIDENCE_DIR", ev_dir)

    ndjson_stdout = "\n".join([
        json.dumps({"event": "init", "init": {"model": "gemini-4-argon-low"}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 1, "step_type": "agent_response", "state": "DONE", "usage": {"input_tokens": 12000, "output_tokens": 50, "cache_read_tokens": 0}}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 2, "step_type": "tool", "state": "DONE", "tool_name": "read_file"}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 3, "step_type": "agent_response", "state": "DONE", "usage": {"input_tokens": 1000, "output_tokens": 60, "cache_read_tokens": 12000}}}),
        json.dumps({"event": "result", "num_turns": 2, "duration_seconds": 4.0, "usage": {"input_tokens": 13000, "output_tokens": 110, "cache_read_tokens": 12000}}),
    ]).encode("utf-8")

    orig_run = subprocess.run

    def fake_run(cmd, **kwargs):
        if cmd and cmd[0] == "agy":
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=ndjson_stdout, stderr=b"")
        return orig_run(cmd, **kwargs)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    res = runner.run_benchmark_live(
        task_id="BENCH-T",
        arm="baseline",
        run_index=1,
        model="gemini-4-argon-low",
        cli_cmd="agy",
        db_path=db_file,
        workspace_root=ws_root,
    )
    assert res["cache_diagnostics"]["llm_calls_count"] == 2
    assert res["cache_diagnostics"]["peak_context_tokens"] == 13000
    assert res["cache_diagnostics"]["avg_fresh_input_per_call"] == pytest.approx(1000.0)
    assert res["cache_diagnostics"]["cache_bust_count"] == 0
    assert res["cache_diagnostics"]["tools_per_llm_call"] == pytest.approx(0.5)

    conn = ledger.get_connection(db_file)
    row = dict(conn.execute("SELECT * FROM runs WHERE id = ?", (res["run_id"],)).fetchone())
    assert row["llm_calls_count"] == 2
    assert row["peak_context_tokens"] == 13000
    assert row["avg_fresh_input_per_call"] == pytest.approx(1000.0)
    assert row["cache_bust_count"] == 0
    assert row["tools_per_llm_call"] == pytest.approx(0.5)
    conn.close()

