import hashlib
import json
import math
import re
import socket
import sqlite3
from pathlib import Path
import pytest

import build_data
import ledger
import runner
import run_experiment


# ---------------------------------------------------------------------------
# Finding 1: Live paths assert verified evidence without references/hashes
# ---------------------------------------------------------------------------

def test_finding1_live_run_requires_evidence_under_approved_policy(tmp_path: Path):
    """Under approved capture policy, live runs must provide valid evidence references and hashes."""
    db_file = tmp_path / "f1.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    # 1. Live run without evidence_ref
    rid1 = ledger.record_run(
        task_id="EXP-F1",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=10000,
        output_tokens=1000,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=None,
        conn=conn,
    )

    # 2. Live run with evidence_ref but missing hash
    evidence_file = tmp_path / "live_evidence.ndjson"
    evidence_file.write_text('{"event": "start"}\n{"event": "complete"}\n', encoding="utf-8")
    actual_hash = hashlib.sha256(evidence_file.read_bytes()).hexdigest()

    rid2 = ledger.record_run(
        task_id="EXP-F1",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:01:00Z",
        input_tokens=5000,
        output_tokens=500,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(evidence_file),
        evidence_hash=None,
        conn=conn,
    )

    # 3. Live run with valid evidence_ref and correct hash
    rid3 = ledger.record_run(
        task_id="EXP-F1-VALID",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:02:00Z",
        input_tokens=10000,
        output_tokens=1000,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(evidence_file),
        evidence_hash=actual_hash,
        verification_status="passed",
        conn=conn,
    )
    rid4 = ledger.record_run(
        task_id="EXP-F1-VALID",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:03:00Z",
        input_tokens=5000,
        output_tokens=500,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(evidence_file),
        evidence_hash=actual_hash,
        verification_status="passed",
        conn=conn,
    )

    # Evaluate under default capture policy (which defaults to "approved")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE id = ?", (rid1,))
    row1 = dict(cursor.fetchone())
    elig1 = ledger.evaluate_run_eligibility(row1)
    assert elig1["is_eligible"] is False
    assert elig1["category"] == "historical"
    assert "evidence_missing" in elig1["exclusion_reasons"]

    cursor.execute("SELECT * FROM runs WHERE id = ?", (rid2,))
    row2 = dict(cursor.fetchone())
    elig2 = ledger.evaluate_run_eligibility(row2)
    assert elig2["is_eligible"] is False
    assert elig2["category"] == "historical"
    assert "evidence_hash_missing" in elig2["exclusion_reasons"]

    cursor.execute("SELECT * FROM runs WHERE id = ?", (rid3,))
    row3 = dict(cursor.fetchone())
    elig3 = ledger.evaluate_run_eligibility(row3)
    assert elig3["is_eligible"] is True
    assert elig3["category"] == "measured"

    # Under default approved policy, unverified runs do not enter measured totals in task summary
    sum1 = ledger.task_summary("EXP-F1", conn=conn)
    assert sum1["measured_runs_count"] == 0
    assert sum1["historical_runs_count"] == 2
    assert sum1["has_measured_data"] is False

    # Simulation mode does not bypass evidence validation
    sum1_sim = ledger.task_summary("EXP-F1", model_override="gemini-2.5-pro", conn=conn)
    assert sum1_sim["measured_runs_count"] == 0

    # EXP-F1-VALID has valid evidence and hashes -> measured
    sum_valid = ledger.task_summary("EXP-F1-VALID", conn=conn)
    assert sum_valid["measured_runs_count"] == 2
    assert sum_valid["has_measured_data"] is True

    # Under legacy permissive policy (if explicitly requested), row1 would be measured:
    elig1_permissive = ledger.evaluate_run_eligibility(row1, capture_policy="permissive")
    assert elig1_permissive["is_eligible"] is True
    assert elig1_permissive["category"] == "measured"

    conn.close()


# ---------------------------------------------------------------------------
# Finding 2: Workspace preparation deletes paths without ownership checks
# ---------------------------------------------------------------------------

def test_finding2_workspace_manager_and_reset_enforce_ownership(tmp_path: Path):
    """WorkspaceManager and run_experiment.reset_workspace_state must enforce ownership markers."""
    repo_src = tmp_path / "repo_source"
    repo_src.mkdir()
    (repo_src / "code.py").write_text("print('hello')", encoding="utf-8")
    ws_root = tmp_path / "workspaces"

    # 1. Reject invalid characters / traversal in run_id or arm
    with pytest.raises(ValueError, match="Invalid (run_id|arm)"):
        runner.WorkspaceManager.prepare_arm_workspace(
            snapshot_dir=repo_src,
            arm="baseline",
            workspace_root=ws_root,
            run_id="../malicious",
        )

    with pytest.raises(ValueError, match="Invalid (run_id|arm)"):
        runner.WorkspaceManager.prepare_arm_workspace(
            snapshot_dir=repo_src,
            arm="../../arm",
            workspace_root=ws_root,
            run_id="run1",
        )

    # 2. Refuse to delete an existing directory without ownership marker
    run_id = "run_safe"
    arm = "baseline"
    target_dir = ws_root / f"{run_id}_{arm}"
    target_dir.mkdir(parents=True, exist_ok=True)
    unowned_file = target_dir / "user_data.txt"
    unowned_file.write_text("DO NOT DELETE", encoding="utf-8")

    with pytest.raises(RuntimeError, match="missing ownership marker"):
        runner.WorkspaceManager.prepare_arm_workspace(
            snapshot_dir=repo_src,
            arm=arm,
            workspace_root=ws_root,
            run_id=run_id,
        )

    assert unowned_file.exists()

    # 3. Clean up unowned dir, then verify successful creation with marker
    unowned_file.unlink()
    target_dir.rmdir()
    ws_created = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=repo_src,
        arm=arm,
        workspace_root=ws_root,
        run_id=run_id,
    )
    marker = ws_root / f".ai_lab_marker_{ws_created.path.name}.json"
    assert marker.exists()
    marker_data = json.loads(marker.read_text(encoding="utf-8"))
    assert marker_data["run_id"] == run_id
    assert marker_data["arm"] == arm

    # 4. Now preparing again should succeed because the marker exists
    ws_reprepared = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=repo_src,
        arm=arm,
        workspace_root=ws_root,
        run_id=run_id,
    )
    assert ws_reprepared.path.exists()
    assert (ws_root / f".ai_lab_marker_{ws_reprepared.path.name}.json").exists()

    # 5. Test run_experiment.reset_workspace_state ownership guard
    external_repo = tmp_path / "external_git_repo"
    external_repo.mkdir()
    git_dir = external_repo / ".git"
    git_dir.mkdir()
    secret_file = external_repo / "uncommitted.txt"
    secret_file.write_text("preserve me", encoding="utf-8")

    # Call reset_workspace_state on external directory lacking marker -> must NOT execute git reset
    run_experiment.reset_workspace_state(external_repo)
    assert secret_file.exists()


# ---------------------------------------------------------------------------
# Finding 3: Nested cumulative/task run exports bypass top-level sanitization
# ---------------------------------------------------------------------------

def test_finding3_nested_exports_sanitized(tmp_path: Path):
    """Task summaries, cumulative metrics, and exported payloads must sanitize all nested strings."""
    db_file = tmp_path / "f3.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    sensitive_note = "User C:\\Users\\DavidHasselhoff\\secret_token.txt has token: ghp_111122223333444455556666777788889999"
    win_ev_path = "C:\\Users\\DavidHasselhoff\\evidence\\run1.ndjson"

    # Create dummy evidence file for valid measured run
    ev_file = tmp_path / "run1.ndjson"
    ev_file.write_text('{"event": "start"}\n', encoding="utf-8")
    actual_hash = hashlib.sha256(ev_file.read_bytes()).hexdigest()

    # 1. Eligible run with valid evidence file
    ledger.record_run(
        task_id="EXP-SAN",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=10000,
        output_tokens=1000,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=actual_hash,
        verification_status="passed",
        notes=sensitive_note,
        conn=conn,
    )
    # 2. Excluded run with sensitive path in evidence_ref and notes
    ledger.record_run(
        task_id="EXP-SAN",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:01:00Z",
        input_tokens=5000,
        output_tokens=500,
        source_kind="live",
        evidence_status="unverified",
        evidence_ref=win_ev_path,
        notes=sensitive_note,
        conn=conn,
    )

    # 1. Check ledger.task_summary nested runs in arms and excluded_runs
    summary = ledger.task_summary("EXP-SAN", conn=conn)
    nested_runs = summary["arms"]["baseline"]["runs"]
    assert len(nested_runs) == 1
    run_obj = nested_runs[0]
    assert "DavidHasselhoff" not in str(run_obj.get("notes"))
    assert "ghp_" not in str(run_obj.get("notes"))
    assert "[REDACTED_SECRET]" in str(run_obj.get("notes"))

    excluded_runs = summary["excluded_runs"]
    assert len(excluded_runs) == 1
    ex_obj = excluded_runs[0]
    assert "DavidHasselhoff" not in str(ex_obj.get("evidence_ref"))
    assert "DavidHasselhoff" not in str(ex_obj.get("notes"))
    assert "ghp_" not in str(ex_obj.get("notes"))
    assert "[REDACTED_SECRET]" in str(ex_obj.get("notes"))

    summary_dump = json.dumps(summary)
    assert "DavidHasselhoff" not in summary_dump
    assert "ghp_111122223333444455556666777788889999" not in summary_dump

    # 2. Check build_data.build_data_payload nested payload
    payload = build_data.build_data_payload(db_path=db_file)
    payload_dump = json.dumps(payload)
    assert "DavidHasselhoff" not in payload_dump
    assert "ghp_111122223333444455556666777788889999" not in payload_dump
    assert "[REDACTED_SECRET]" in payload_dump

    # 3. Check build_data.export_data written file
    out_json = tmp_path / "exported_data.json"
    build_data.export_data(output_file=out_json, db_path=db_file)
    file_content = out_json.read_text(encoding="utf-8")
    assert "DavidHasselhoff" not in file_content
    assert "ghp_111122223333444455556666777788889999" not in file_content
    assert "[REDACTED_SECRET]" in file_content

    conn.close()


# ---------------------------------------------------------------------------
# Finding 4: Missing/partial telemetry becomes zero or complete-looking totals
# ---------------------------------------------------------------------------

def test_finding4_telemetry_partial_preservation_and_non_finite_rejection():
    """validate_and_parse_telemetry must reject non-finite numbers, preserve missing fields, and enforce explicit schemas."""
    # 1. Reject NaN / Inf
    nan_event = json.dumps({
        "event": "turn",
        "usage": {"input_tokens": float("nan"), "output_tokens": 100},
    })
    with pytest.raises(ValueError, match="cannot be non-finite float"):
        ledger.validate_and_parse_telemetry([nan_event])

    inf_event = json.dumps({
        "event": "turn",
        "usage": {"input_tokens": 100, "output_tokens": float("inf")},
    })
    with pytest.raises(ValueError, match="cannot be non-finite float"):
        ledger.validate_and_parse_telemetry([inf_event])

    # 2. Missing fields remain None, not coerced to 0; adapter_name retained; field_completeness tracked
    simple_event = json.dumps({
        "event": "turn",
        "usage": {"input_tokens": 500, "output_tokens": 50},
    })
    parsed = ledger.validate_and_parse_telemetry([simple_event], adapter_name="custom_adapter")
    assert parsed["adapter_name"] == "custom_adapter"
    assert parsed["usage"]["input_tokens"] == 500
    assert parsed["usage"]["output_tokens"] == 50
    assert parsed["usage"]["thinking_tokens"] is None
    assert parsed["usage"]["cache_read_tokens"] is None
    assert parsed["usage"]["total_tokens"] == 550
    assert parsed["field_completeness"]["input_tokens"] is True
    assert parsed["field_completeness"]["output_tokens"] is True
    assert parsed["field_completeness"]["thinking_tokens"] is False
    assert parsed["field_completeness"]["cache_read_tokens"] is False

    # 3. Adapter reporting subset does not double count
    subset_event = json.dumps({
        "event": "turn",
        "adapter_name": "subset_adapter",
        "usage": {
            "input_tokens": 1000,  # includes cache read
            "cache_read_tokens": 300,
            "output_tokens": 100,
            "cache_accounting": "subset",
        },
    })
    parsed_subset = ledger.validate_and_parse_telemetry([subset_event])
    assert parsed_subset["usage"]["total_tokens"] == 1100  # 1000 + 100, not 1000 + 300 + 100

    # 4. Extra counters without explicit schema return None for total tokens
    extra_event = json.dumps({
        "event": "turn",
        "usage": {
            "input_tokens": 1000,
            "output_tokens": 100,
            "cache_read_tokens": 300,
        },
    })
    parsed_no_schema = ledger.validate_and_parse_telemetry([extra_event])
    assert parsed_no_schema["usage"]["total_tokens"] is None

    # 5. Extra counters with explicit separate schema are summed properly
    parsed_separate = ledger.validate_and_parse_telemetry([extra_event], adapter_name="gemini_separate")
    assert parsed_separate["usage"]["total_tokens"] == 1400  # 1000 + 100 + 300


# ---------------------------------------------------------------------------
# Finding 5: Measurement and correctness are coupled in evaluate_run_eligibility
# ---------------------------------------------------------------------------

def test_finding5_decoupled_measurement_and_correctness(tmp_path: Path):
    """Failed runs must remain measurable while tracking correctness status independently."""
    db_file = tmp_path / "f5.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    evidence_file = tmp_path / "ev.ndjson"
    evidence_file.write_text('{"event": "start"}\n', encoding="utf-8")
    actual_hash = hashlib.sha256(evidence_file.read_bytes()).hexdigest()

    # Record a live measured run that failed its evaluator tests
    rid = ledger.record_run(
        task_id="EXP-DEC",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=20000,
        output_tokens=1500,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(evidence_file),
        evidence_hash=actual_hash,
        execution_status="completed",
        verification_status="failed",
        conn=conn,
    )

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE id = ?", (rid,))
    row = dict(cursor.fetchone())

    elig = ledger.evaluate_run_eligibility(row, capture_policy="approved")
    # Must be valid provenance and measured category
    assert elig["provenance_valid"] is True
    assert elig["category"] == "measured"
    assert elig["is_cost_complete"] is True
    # Correctness and comparison eligibility are distinct
    assert elig["is_correct"] is False
    assert elig["verification_status"] == "failed"
    assert elig["is_comparison_eligible"] is False
    assert "verification_failed" in elig["correctness_reasons"]

    # Check task summary tracks counts separately
    summary = ledger.task_summary("EXP-DEC", conn=conn)
    assert summary["measured_runs_count"] == 1
    assert summary["failed_runs_count"] == 1
    assert summary["passed_runs_count"] == 0
    assert summary["comparison_eligible_runs_count"] == 0

    conn.close()


# ---------------------------------------------------------------------------
# Finding 6: Offline-call counters do not independently enforce no-network invariant
# ---------------------------------------------------------------------------

def test_finding6_network_blocking_in_offline_execution(monkeypatch):
    """Offline execution must actively block network/socket connect calls."""
    adapter = runner.OfflineExecutionAdapter()

    # Verify NetworkAccessBlockedError is a subclass of OfflineModeViolationError
    assert issubclass(runner.NetworkAccessBlockedError, runner.OfflineModeViolationError)

    # 1. Direct block_network test
    with pytest.raises(runner.NetworkAccessBlockedError, match="Network access is blocked in offline mode"):
        with runner.block_network():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("8.8.8.8", 53))

    # Verify socket restored after context manager exits
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    assert s.connect != runner.block_network

    # 2. adapter.execute_mock() actively blocks outbound socket connections
    def connect_during_execution(*args, **kwargs):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("8.8.8.8", 53))

    monkeypatch.setattr(adapter, "assert_zero_provider_calls", connect_during_execution)
    with pytest.raises(runner.NetworkAccessBlockedError, match="Network access is blocked in offline mode"):
        adapter.execute_mock("EXP-001", "baseline")


# ---------------------------------------------------------------------------
# Finding 7: Default pytest discovery excludes tests/exp007 and tests/exp008
# ---------------------------------------------------------------------------

def test_finding7_pytest_ini_and_readme_documentation():
    """pytest.ini and tests/README.md must document the two-tier test suite architecture."""
    workspace_root = Path(__file__).resolve().parent.parent.parent
    pytest_ini = workspace_root / "pytest.ini"
    readme_md = workspace_root / "tests" / "README.md"

    assert pytest_ini.exists()
    assert readme_md.exists()

    ini_content = pytest_ini.read_text(encoding="utf-8")
    assert "tests/unit tests/integration" in ini_content
    assert "tests/exp007" in ini_content
    assert "tests/exp008" in ini_content

    readme_content = readme_md.read_text(encoding="utf-8")
    assert "Tier 1: Hermetic Unit & Integration Tests" in readme_content
    assert "Tier 2: End-to-End Playwright Browser Suites" in readme_content
    assert "EXP-007" in readme_content
    assert "EXP-008" in readme_content
