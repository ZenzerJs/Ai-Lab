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


def test_ui_01_demo_fixture_report_banner_and_metric_suppression(tmp_path: Path):
    """
    UI-01: When fixture/demo report is active, payload has is_demo_report=True,
    has_measured_data=False, and empirical headline metrics are None (suppressed).
    """
    db_file = tmp_path / "ui01_demo.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    # Record 2 fixture runs
    ledger.record_run(
        task_id="EXP-FIXTURE-DEMO",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=10_000,
        output_tokens=1_000,
        source_kind="fixture",
        evidence_status="unverified",
        exclusion_reasons=["fixture_replay"],
        conn=conn,
    )
    ledger.record_run(
        task_id="EXP-FIXTURE-DEMO",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:05:00Z",
        input_tokens=5_000,
        output_tokens=500,
        source_kind="fixture",
        evidence_status="unverified",
        exclusion_reasons=["fixture_replay"],
        conn=conn,
    )

    payload = build_data.build_data_payload(db_path=db_file)

    assert payload["is_demo_report"] is True
    assert payload["has_data"] is False
    assert payload["cumulative"]["has_measured_data"] is False
    assert payload["cumulative"]["is_demo_report"] is True
    assert payload["cumulative"]["cumulative_savings_usd"] is None
    assert payload["cumulative"]["cumulative_savings_percent"] is None
    assert payload["cumulative"]["total_baseline_cost_usd"] is None
    assert payload["cumulative"]["total_icm_cost_usd"] is None
    assert payload["cumulative"]["fixture_runs_count"] == 2

    # Task summary also marks is_demo_report
    task = payload["tasks"][0]
    assert task["is_demo_report"] is True
    assert task["savings"] is None

    conn.close()


def test_ui_02_per_arm_counts_and_provenance_tracking(tmp_path: Path):
    """
    UI-02 / EXP-02: Detailed per-arm counts (scheduled, completed, verified, failed, excluded)
    and provenance tags (source_kinds, evidence_statuses, exclusion_reasons).
    """
    db_file = tmp_path / "ui02_counts.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    ev_file = tmp_path / "ev.ndjson"
    ev_file.write_text('{"event": "start"}\n{"event": "complete"}\n', encoding="utf-8")
    ev_hash = hashlib.sha256(ev_file.read_bytes()).hexdigest()

    # 1. Baseline: 1 verified, 1 failed verification (excluded)
    ledger.record_run(
        task_id="TASK-MIXED",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=10_000,
        output_tokens=1_000,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        execution_status="completed",
        verification_status="passed",
        conn=conn,
    )
    ledger.record_run(
        task_id="TASK-MIXED",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=2,
        timestamp="2026-09-10T12:10:00Z",
        input_tokens=8_000,
        output_tokens=800,
        source_kind="live",
        evidence_status="invalid",
        execution_status="completed",
        verification_status="failed",
        exclusion_reasons=["failed_verification"],
        conn=conn,
    )

    # 2. ICM: 1 verified, 1 execution failure
    ledger.record_run(
        task_id="TASK-MIXED",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:05:00Z",
        input_tokens=5_000,
        output_tokens=500,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        execution_status="completed",
        verification_status="passed",
        conn=conn,
    )
    ledger.record_run(
        task_id="TASK-MIXED",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=2,
        timestamp="2026-09-10T12:15:00Z",
        input_tokens=2_000,
        output_tokens=200,
        source_kind="live",
        evidence_status="unverified",
        execution_status="failed",
        verification_status="not_run",
        exclusion_reasons=["execution_failure"],
        conn=conn,
    )

    ts = ledger.task_summary("TASK-MIXED", conn=conn)
    assert ts["scheduled_count"] == 4
    assert ts["cost_eligible_count"] == 2
    assert ts["failed_count"] == 2
    assert "failed_verification" in ts["exclusion_reasons"]
    assert "execution_failure" in ts["exclusion_reasons"]

    # Baseline arm stats
    b = ts["arms"]["baseline"]
    assert b["scheduled_count"] == 2
    assert b["verified_count"] == 1
    assert b["failed_count"] == 1
    assert b["excluded_count"] == 1
    assert b["cost_eligible_count"] == 1

    # ICM arm stats
    i = ts["arms"]["icm"]
    assert i["scheduled_count"] == 2
    assert i["verified_count"] == 1
    assert i["failed_count"] == 1
    assert i["excluded_count"] == 1
    assert i["cost_eligible_count"] == 1

    # Cumulative per-arm aggregation
    cum = ledger.cumulative_savings(conn=conn)
    assert "baseline" in cum["per_arm_counts"]
    assert "icm" in cum["per_arm_counts"]
    assert cum["per_arm_counts"]["baseline"]["verified"] == 1
    assert cum["per_arm_counts"]["baseline"]["excluded"] == 1
    assert cum["per_arm_counts"]["icm"]["verified"] == 1
    assert cum["per_arm_counts"]["icm"]["excluded"] == 1

    conn.close()


def test_ui_04_zero_baseline_cost_safe_handling(tmp_path: Path):
    """
    UI-04: When baseline mean cost is 0.0, savings percent must be None
    (avoiding ZeroDivisionError, fake 0.0% or NaN).
    """
    db_file = tmp_path / "ui04_zero.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    ev_file = tmp_path / "ev.ndjson"
    ev_file.write_text('{"event": "done"}\n', encoding="utf-8")
    ev_hash = hashlib.sha256(ev_file.read_bytes()).hexdigest()

    # Both baseline and icm have 0 tokens (cost is 0.0)
    ledger.record_run(
        task_id="TASK-FREE",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=0,
        output_tokens=0,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        verification_status="passed",
        conn=conn,
    )
    ledger.record_run(
        task_id="TASK-FREE",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:05:00Z",
        input_tokens=0,
        output_tokens=0,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        verification_status="passed",
        conn=conn,
    )

    ts = ledger.task_summary("TASK-FREE", conn=conn)
    assert ts["savings"] is not None
    assert ts["savings"]["mean_savings_usd"] == 0.0
    # Must be None, not 0.0 or NaN
    assert ts["savings"]["mean_savings_percent"] is None

    conn.close()


def test_exp_01_campaign_export_parity(tmp_path: Path):
    """
    EXP-01: Shared campaign report is present in export payload.
    """
    db_file = tmp_path / "exp01_campaign.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    payload = build_data.build_data_payload(db_path=db_file)
    assert "campaign" in payload
    assert payload["campaign"] is not None
    assert "campaign_id" in payload["campaign"]
    assert "status" in payload["campaign"]
    assert "total_scheduled" in payload["campaign"]

    conn.close()


def test_ui_03_filtering_by_task_arm_source_and_evidence(tmp_path: Path):
    """
    UI-03: Filter runs by task, arm, source kind, and evidence status.
    Expected: Counts and filtered lists match criteria without data leakage.
    """
    db_file = tmp_path / "ui03_filter.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    ev_file = tmp_path / "ui03_ev.ndjson"
    ev_file.write_text('{"event": "start"}\n{"event": "complete"}\n', encoding="utf-8")
    ev_hash = hashlib.sha256(ev_file.read_bytes()).hexdigest()

    # 1. TASK-A Baseline live verified
    ledger.record_run(
        task_id="TASK-A",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=10_000,
        output_tokens=1_000,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        verification_status="passed",
        conn=conn,
    )
    # 2. TASK-A ICM live verified
    ledger.record_run(
        task_id="TASK-A",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:05:00Z",
        input_tokens=5_000,
        output_tokens=500,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        verification_status="passed",
        conn=conn,
    )
    # 3. TASK-B ICM-Subagents fixture unverified
    ledger.record_run(
        task_id="TASK-B",
        arm="icm-subagents",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T13:00:00Z",
        input_tokens=8_000,
        output_tokens=800,
        source_kind="fixture",
        evidence_status="unverified",
        exclusion_reasons=["fixture_replay"],
        conn=conn,
    )
    # 4. TASK-B Baseline imported invalid
    ledger.record_run(
        task_id="TASK-B",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T13:05:00Z",
        input_tokens=9_000,
        output_tokens=900,
        source_kind="imported",
        evidence_status="invalid",
        exclusion_reasons=["evidence_hash_mismatch"],
        conn=conn,
    )

    payload = build_data.build_data_payload(db_path=db_file)
    runs = payload["runs"]
    assert len(runs) == 4

    # Filter by task TASK-A
    task_a_runs = [r for r in runs if r["task_id"] == "TASK-A"]
    assert len(task_a_runs) == 2
    assert all(r["task_id"] == "TASK-A" for r in task_a_runs)

    # Filter by arm icm-subagents
    subagent_runs = [r for r in runs if r["arm"].lower() == "icm-subagents"]
    assert len(subagent_runs) == 1
    assert subagent_runs[0]["task_id"] == "TASK-B"

    # Filter by source_kind fixture
    fixture_runs = [r for r in runs if r.get("source_kind") == "fixture"]
    assert len(fixture_runs) == 1
    assert fixture_runs[0]["arm"] == "icm-subagents"

    # Filter by evidence_status invalid
    invalid_runs = [r for r in runs if r.get("evidence_status") == "invalid"]
    assert len(invalid_runs) == 1
    assert "evidence_hash_mismatch" in invalid_runs[0]["exclusion_reasons"]

    conn.close()


def test_ui_05_pricing_simulator_separation_and_accuracy(tmp_path: Path):
    """
    UI-05 / ACC-06: Pricing simulator reprices token workload against target rate card.
    Expected: Simulation is clearly distinguished from empirical actuals, empirical totals
    remain untouched, and cascade projects accurately.
    """
    db_file = tmp_path / "ui05_sim.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    ev_file = tmp_path / "ui05_ev.ndjson"
    ev_file.write_text('{"event": "start"}\n{"event": "complete"}\n', encoding="utf-8")
    ev_hash = hashlib.sha256(ev_file.read_bytes()).hexdigest()

    # Empirical baseline & icm on gemini-2.5-pro
    ledger.record_run(
        task_id="EXP-SIM-01",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=1_000_000,
        output_tokens=100_000,
        cache_read_tokens=200_000,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        verification_status="passed",
        conn=conn,
    )
    ledger.record_run(
        task_id="EXP-SIM-01",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:05:00Z",
        input_tokens=200_000,
        output_tokens=20_000,
        cache_read_tokens=600_000,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        verification_status="passed",
        conn=conn,
    )

    # 1. Baseline empirical totals
    cum_actual = ledger.cumulative_savings(conn=conn)
    assert cum_actual["is_simulation"] is False
    assert cum_actual["has_measured_data"] is True
    emp_baseline_cost = cum_actual["total_baseline_cost_usd"]
    emp_icm_cost = cum_actual["total_icm_cost_usd"]
    emp_savings = cum_actual["cumulative_savings_usd"]

    # 2. Simulated re-pricing on claude-sonnet-4-6
    cum_sim = ledger.cumulative_savings(conn=conn, model_override="claude-sonnet-4-6")
    assert cum_sim["is_simulation"] is True
    assert cum_sim["total_baseline_cost_usd"] != emp_baseline_cost
    assert cum_sim["total_icm_cost_usd"] != emp_icm_cost
    assert cum_sim["cumulative_savings_usd"] != emp_savings

    # Verify rates applied correctly from pricing config (claude-sonnet-4-6 uses subset cache accounting)
    rates = ledger.get_pricing("claude-sonnet-4-6", conn=conn)
    uncached_b_in = max(0, 1_000_000 - 200_000)
    expected_b_cost = (
        uncached_b_in * rates["input_usd_per_mtok"]
        + 200_000 * rates["cache_read_usd_per_mtok"]
        + 100_000 * rates["output_usd_per_mtok"]
    ) / 1_000_000.0
    uncached_i_in = max(0, 200_000 - 600_000)
    expected_i_cost = (
        uncached_i_in * rates["input_usd_per_mtok"]
        + 600_000 * rates["cache_read_usd_per_mtok"]
        + 20_000 * rates["output_usd_per_mtok"]
    ) / 1_000_000.0
    assert abs(cum_sim["total_baseline_cost_usd"] - expected_b_cost) < 1e-4
    assert abs(cum_sim["total_icm_cost_usd"] - expected_i_cost) < 1e-4

    # 3. Export payload cascade
    payload = build_data.build_data_payload(db_path=db_file)
    assert "cascade" in payload
    cascade_models = [c["model"] for c in payload["cascade"]]
    assert "claude-sonnet-4-6" in cascade_models
    assert "gemini-2.5-pro" in cascade_models

    claude_cascade = next(c for c in payload["cascade"] if c["model"] == "claude-sonnet-4-6")
    assert abs(claude_cascade["total_baseline_cost_usd"] - expected_b_cost) < 1e-4

    conn.close()


def test_unmigrated_legacy_database_export_safe_handling(tmp_path: Path):
    """
    Test that an unmigrated legacy database lacking source_kind and evidence_status
    columns is read without crashing, safely treated as unknown/unverified,
    and suppressed from empirical headlines.
    """
    legacy_db = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(legacy_db))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            arm TEXT NOT NULL,
            model TEXT NOT NULL,
            run_index INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            input_tokens INTEGER,
            output_tokens INTEGER,
            thinking_tokens INTEGER,
            cache_read_tokens INTEGER,
            total_tokens INTEGER,
            num_turns INTEGER NOT NULL,
            duration_seconds REAL NOT NULL,
            cost_usd REAL
        );
        CREATE TABLE pricing (
            model TEXT PRIMARY KEY,
            input_usd_per_mtok REAL NOT NULL,
            cache_read_usd_per_mtok REAL NOT NULL,
            output_usd_per_mtok REAL NOT NULL,
            source_url TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        );
    """)
    conn.execute(
        "INSERT INTO pricing VALUES ('gemini-2.5-pro', 1.25, 0.3125, 5.0, 'https://example.com', '2026-09-01')"
    )
    conn.execute(
        "INSERT INTO runs (task_id, arm, model, run_index, timestamp, input_tokens, output_tokens, num_turns, duration_seconds) "
        "VALUES ('LEGACY-01', 'baseline', 'gemini-2.5-pro', 1, '2026-08-01T10:00:00Z', 50000, 5000, 3, 10.0)"
    )
    conn.commit()
    conn.close()

    # Must build payload without crashing
    payload = build_data.build_data_payload(db_path=legacy_db)
    assert payload["has_data"] is False
    assert payload["is_demo_report"] is True
    assert payload["cumulative"]["has_measured_data"] is False
    assert len(payload["runs"]) == 1
    assert payload["runs"][0]["source_kind"] == "unknown"
    assert payload["runs"][0]["evidence_status"] == "unverified"
    assert payload["runs"][0]["is_eligible"] is False



