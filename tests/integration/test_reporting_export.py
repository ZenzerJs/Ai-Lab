import hashlib
import json
import sqlite3
from pathlib import Path
import pytest

import ledger
import build_data


def test_exp_01_ledger_and_export_agreement(tmp_path: Path):
    """
    EXP-01: Compare shared ledger report with JSON export.
    Expected: Same counts, eligibility decisions, costs, and completeness labels.
    """
    db_file = tmp_path / "exp01.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    ev_file = tmp_path / "exp01_ev.ndjson"
    ev_file.write_text('{"event": "start"}\n{"event": "complete"}\n', encoding="utf-8")
    ev_hash = hashlib.sha256(ev_file.read_bytes()).hexdigest()

    # 1. Eligible measured baseline & icm pair
    ledger.record_run(
        task_id="EXP-MEASURED",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=100_000,
        output_tokens=10_000,
        cache_read_tokens=20_000,
        num_turns=3,
        duration_seconds=15.0,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        verification_status="passed",
        conn=conn,
    )
    ledger.record_run(
        task_id="EXP-MEASURED",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:05:00Z",
        input_tokens=50_000,
        output_tokens=8_000,
        cache_read_tokens=40_000,
        num_turns=2,
        duration_seconds=9.0,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        verification_status="passed",
        conn=conn,
    )

    # 2. Fixture run
    ledger.record_run(
        task_id="EXP-FIXTURE",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T13:00:00Z",
        input_tokens=80_000,
        output_tokens=5_000,
        source_kind="fixture",
        evidence_status="unverified",
        exclusion_reasons=["fixture_replay"],
        conn=conn,
    )

    # 3. Legacy unknown run
    ledger.record_run(
        task_id="EXP-LEGACY",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-01T10:00:00Z",
        input_tokens=90_000,
        output_tokens=7_000,
        source_kind="unknown",
        evidence_status="unverified",
        conn=conn,
    )

    # 4. Incomplete cost run
    ledger.record_run(
        task_id="EXP-INCOMPLETE",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T14:00:00Z",
        input_tokens=20_000,
        output_tokens=1_000,
        cost_status="incomplete",
        exclusion_reasons=["partial_telemetry"],
        conn=conn,
    )

    # Get ledger report
    cum_ledger = ledger.cumulative_savings(conn=conn)
    task_ledger = ledger.task_summary("EXP-MEASURED", conn=conn)

    # Get export payload
    payload = build_data.build_data_payload(db_path=db_file)

    # Verify counts agreement
    assert payload["cumulative"]["total_runs"] == cum_ledger["total_runs"] == 2
    assert payload["cumulative"]["fixture_runs_count"] == cum_ledger["fixture_runs_count"] == 1
    assert payload["cumulative"]["historical_runs_count"] == cum_ledger["historical_runs_count"] == 2  # legacy + incomplete
    assert len(payload["runs"]) == 5

    # Verify cumulative financial metrics agreement
    assert payload["cumulative"]["has_measured_data"] == cum_ledger["has_measured_data"] == True
    assert payload["cumulative"]["total_baseline_cost_usd"] == cum_ledger["total_baseline_cost_usd"]
    assert payload["cumulative"]["total_icm_cost_usd"] == cum_ledger["total_icm_cost_usd"]
    assert payload["cumulative"]["cumulative_savings_usd"] == cum_ledger["cumulative_savings_usd"]
    assert payload["cumulative"]["cumulative_savings_percent"] == cum_ledger["cumulative_savings_percent"]

    # Verify individual run eligibility & classification in export
    runs_by_task = {r["task_id"]: r for r in payload["runs"]}
    assert runs_by_task["EXP-MEASURED"]["is_eligible"] is True
    assert runs_by_task["EXP-MEASURED"]["reporting_category"] == "measured"
    assert runs_by_task["EXP-FIXTURE"]["is_eligible"] is False
    assert runs_by_task["EXP-FIXTURE"]["reporting_category"] == "fixture"
    assert runs_by_task["EXP-LEGACY"]["is_eligible"] is False
    assert runs_by_task["EXP-LEGACY"]["reporting_category"] == "historical"
    assert runs_by_task["EXP-INCOMPLETE"]["is_eligible"] is False
    assert runs_by_task["EXP-INCOMPLETE"]["cost_status"] == "incomplete"

    conn.close()


def test_exp_02_export_redacts_private_paths_and_secrets(tmp_path: Path):
    """
    EXP-02: Put sentinel secrets and private paths in raw evidence and notes.
    Expected: Public export omits them.
    """
    db_file = tmp_path / "exp02.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    secret_key = "sk-live_99887766554433221100998877665544"
    github_token = "ghp_1234567890abcdef1234567890abcdef12345678"
    google_key = "AIzaSyDa94_SampleValidGeminiKeySecret12345"
    anthropic_key = "sk-ant-api03-abcdef1234567890abcdef12345678"
    win_path = r"C:\Users\AliceSmith\Confidential\evidence.ndjson"
    win_fwd_path = "C:/Users/CarolDanvers/evidence2.ndjson"
    unix_path = "/home/bobjones/sensitive/run_trace.ndjson"

    ledger.record_run(
        task_id="EXP-SEC-01",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=10_000,
        output_tokens=1_000,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=win_path,
        notes=f"Authorized with token: {github_token} and secret: {secret_key} and google: {google_key} and anthropic: {anthropic_key} on {unix_path} and {win_fwd_path}",
        conn=conn,
    )

    payload = build_data.build_data_payload(db_path=db_file)

    # Convert entire export payload to string to scan for leaked strings across all nested structures (Finding 3)
    dumped = json.dumps(payload)

    # 1. Private username paths must NOT be present
    assert "AliceSmith" not in dumped
    assert "bobjones" not in dumped
    assert "CarolDanvers" not in dumped
    assert r"C:\Users\AliceSmith" not in dumped
    assert "C:/Users/CarolDanvers" not in dumped
    assert "/home/bobjones" not in dumped

    # 2. Secrets must be redacted
    assert secret_key not in dumped
    assert github_token not in dumped
    assert google_key not in dumped
    assert anthropic_key not in dumped
    assert "[REDACTED_SECRET]" in dumped

    conn.close()


def test_rep_04_honest_empty_state_when_zero_measured_runs(tmp_path: Path):
    """
    REP-04 / UI-04: No eligible measured runs exist.
    Expected: Honest empty state; no synthetic substitute, no fake savings.
    """
    db_file = tmp_path / "rep04.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    # Only fixture runs exist in DB
    ledger.record_run(
        task_id="EXP-008",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=50_000,
        output_tokens=2_000,
        source_kind="fixture",
        evidence_status="unverified",
        exclusion_reasons=["fixture_replay"],
        conn=conn,
    )

    # 1. Ledger cumulative savings must be an honest empty state
    cum = ledger.cumulative_savings(conn=conn)
    assert cum["has_measured_data"] is False
    assert cum["cumulative_savings_usd"] is None
    assert cum["cumulative_savings_percent"] is None
    assert cum["total_baseline_cost_usd"] is None
    assert cum["total_icm_cost_usd"] is None
    assert cum["total_runs"] == 0
    assert cum["fixture_runs_count"] == 1

    # 2. Export payload must also be an honest empty state
    payload = build_data.build_data_payload(db_path=db_file)
    assert payload["has_data"] is False
    assert payload["cumulative"]["has_measured_data"] is False
    assert payload["timeline"] == []

    conn.close()


def test_exp_icm_subagents_governed_arm_in_timeline_and_cumulative(tmp_path: Path):
    """
    EXP-01 / EXP-03: Governed arm named icm-subagents (as in EXP-006, EXP-007, EXP-008).
    Expected: Correctly paired against baseline in cumulative savings and export timeline.
    """
    db_file = tmp_path / "exp_subagents.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)
    ev_file = tmp_path / "sub_ev.ndjson"
    ev_file.write_text('{"event": "start"}\n{"event": "complete"}\n', encoding="utf-8")
    ev_hash = hashlib.sha256(ev_file.read_bytes()).hexdigest()

    ledger.record_run(
        task_id="EXP-006",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=100_000,
        output_tokens=10_000,
        cache_read_tokens=20_000,
        num_turns=3,
        duration_seconds=15.0,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        verification_status="passed",
        conn=conn,
    )
    ledger.record_run(
        task_id="EXP-006",
        arm="icm-subagents",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:05:00Z",
        input_tokens=40_000,
        output_tokens=5_000,
        cache_read_tokens=10_000,
        num_turns=2,
        duration_seconds=8.0,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        verification_status="passed",
        conn=conn,
    )

    cum = ledger.cumulative_savings(conn=conn)
    assert cum["has_measured_data"] is True
    assert cum["total_runs"] == 2
    assert cum["cumulative_savings_usd"] is not None and cum["cumulative_savings_usd"] > 0

    payload = build_data.build_data_payload(db_path=db_file)
    assert payload["has_data"] is True
    assert len(payload["timeline"]) == 1
    assert payload["timeline"][0]["governed_arm"] == "icm-subagents"
    assert payload["timeline"][0]["delta_saved_usd"] > 0
    assert payload["timeline"][0]["delta_saved_usd"] == cum["cumulative_savings_usd"]

    conn.close()

