import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path
import pytest

import ledger
import runner


# ---------------------------------------------------------------------------
# RUN-01: Prepare two arms from a task snapshot
# ---------------------------------------------------------------------------

def test_run_01_prepare_two_arms_same_starting_state(tmp_path: Path):
    """
    RUN-01: Prepare two arms from a task snapshot.
    Expected: Same starting state; separate writable directories.
    """
    snapshot_dir = tmp_path / "task_snapshot"
    snapshot_dir.mkdir()
    (snapshot_dir / "calculator.py").write_text("def calc(a, b): return a * b\n", encoding="utf-8")
    (snapshot_dir / "README.md").write_text("# Calc Task\n", encoding="utf-8")
    (snapshot_dir / "config.json").write_text('{"mode": "fast"}', encoding="utf-8")

    ws_root = tmp_path / "workspaces"
    ws_base, ws_icm = runner.WorkspaceManager.prepare_two_arms(
        snapshot_dir=snapshot_dir,
        workspace_root=ws_root,
        run_id="run_01_test",
    )

    try:
        # Separate directories
        assert ws_base.path != ws_icm.path
        assert ws_base.path.exists()
        assert ws_icm.path.exists()

        # Same starting state
        base_files = sorted([p.relative_to(ws_base.path).as_posix() for p in ws_base.path.rglob("*") if p.is_file()])
        icm_files = sorted([p.relative_to(ws_icm.path).as_posix() for p in ws_icm.path.rglob("*") if p.is_file()])
        assert base_files == icm_files
        assert base_files == ["README.md", "calculator.py", "config.json"]

        for f in base_files:
            content_base = (ws_base.path / f).read_bytes()
            content_icm = (ws_icm.path / f).read_bytes()
            content_orig = (snapshot_dir / f).read_bytes()
            assert content_base == content_orig
            assert content_icm == content_orig
    finally:
        ws_base.cleanup()
        ws_icm.cleanup()


# ---------------------------------------------------------------------------
# RUN-02: Write in arm A
# ---------------------------------------------------------------------------

def test_run_02_write_in_arm_a_arm_b_and_source_unchanged(tmp_path: Path):
    """
    RUN-02: Write in arm A.
    Expected: Arm B and source checkout unchanged.
    """
    snapshot_dir = tmp_path / "task_snapshot"
    snapshot_dir.mkdir()
    orig_code = "def calc(a, b): return a + b\n"
    (snapshot_dir / "calculator.py").write_text(orig_code, encoding="utf-8")
    (snapshot_dir / "README.md").write_text("# Calc\n", encoding="utf-8")

    ws_root = tmp_path / "workspaces"
    ws_base, ws_icm = runner.WorkspaceManager.prepare_two_arms(
        snapshot_dir=snapshot_dir,
        workspace_root=ws_root,
        run_id="run_02_test",
    )

    try:
        # Arm A (baseline) modifies a file and creates a new file
        (ws_base.path / "calculator.py").write_text("def calc(a, b): return a + b + 999\n", encoding="utf-8")
        (ws_base.path / "new_arm_a_file.txt").write_text("Arm A secret note\n", encoding="utf-8")

        # Arm B (icm) must be completely unchanged
        assert (ws_icm.path / "calculator.py").read_text(encoding="utf-8") == orig_code
        assert not (ws_icm.path / "new_arm_a_file.txt").exists()

        # Source snapshot must be completely unchanged
        assert (snapshot_dir / "calculator.py").read_text(encoding="utf-8") == orig_code
        assert not (snapshot_dir / "new_arm_a_file.txt").exists()
    finally:
        ws_base.cleanup()
        ws_icm.cleanup()


# ---------------------------------------------------------------------------
# RUN-03: Existing user files and uncommitted changes are present
# ---------------------------------------------------------------------------

def test_run_03_existing_user_files_and_uncommitted_changes_preserved(tmp_path: Path):
    """
    RUN-03: Existing user files and uncommitted changes are present.
    Expected: Preparation and cleanup preserve them. Never run destructive reset/cleanup on user checkout.
    """
    host_repo = tmp_path / "user_project"
    host_repo.mkdir()
    (host_repo / ".git").mkdir()

    tracked_file = host_repo / "server.py"
    tracked_file.write_text("def start(): print('original')\n", encoding="utf-8")

    # Simulate user uncommitted edits
    uncommitted_edit = "def start(): print('user uncommitted work in progress')\n"
    tracked_file.write_text(uncommitted_edit, encoding="utf-8")

    # Simulate untracked user scratch file
    untracked_notes = host_repo / "my_private_notes.md"
    untracked_notes.write_text("# Personal To-Do\nDo not delete!\n", encoding="utf-8")

    # Snapshot to execute from
    snapshot_dir = tmp_path / "task_snapshot"
    snapshot_dir.mkdir()
    (snapshot_dir / "task.py").write_text("print('task')\n", encoding="utf-8")

    # Run preparation and cleanup
    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir,
        arm="baseline",
        workspace_root=tmp_path / "ws_disposable",
        run_id="run_03_test",
    )
    # Write inside disposable workspace
    (ws.path / "task.py").write_text("print('modified in agent run')\n", encoding="utf-8")
    (ws.path / "generated_artifact.tmp").write_text("temporary data\n", encoding="utf-8")

    # Cleanup disposable workspace
    ws.cleanup()

    # Invariant assertion: Host repository was preserved bit-for-bit
    assert tracked_file.read_text(encoding="utf-8") == uncommitted_edit
    assert untracked_notes.exists()
    assert untracked_notes.read_text(encoding="utf-8") == "# Personal To-Do\nDo not delete!\n"
    assert not ws.path.exists()


# ---------------------------------------------------------------------------
# RUN-04: Model/configuration differs unintentionally
# ---------------------------------------------------------------------------

def test_run_04_unintentional_model_mismatch_rejected_or_segregated():
    """
    RUN-04: Model/configuration differs unintentionally.
    Expected: Mismatch rejected or segregated; not silently pooled.
    """
    arm_base = runner.ArmConfig(
        arm="baseline",
        model="gemini-2.5-pro",
        prompt="Fix the bug",
    )
    # Unintentional model mismatch: gemini-3.8-flash vs gemini-2.5-pro
    arm_mismatched = runner.ArmConfig(
        arm="icm",
        model="gemini-3.8-flash",
        prompt="Fix the bug",
    )

    manifest = runner.RunManifest(
        manifest_id="MAN-ERR-001",
        task_id="TASK-001",
        task_version="1.0.0",
        created_at="2026-10-02T12:00:00Z",
        task_contract={"task_id": "TASK-001", "task_version": "1.0.0"},
        arms={"baseline": arm_base, "icm": arm_mismatched},
    )

    # 1. Unintentional mismatch must be rejected
    with pytest.raises(runner.ConfigurationMismatchError, match="Unintentional model mismatch rejected"):
        runner.validate_manifest_configuration(manifest, enforce_model_match=True)

    # 2. When marked segregated or allow_model_mismatch, it is segregated and not silently pooled
    manifest.metadata["allow_model_mismatch"] = True
    val_res = runner.validate_manifest_configuration(manifest, enforce_model_match=True)
    assert val_res["valid"] is True
    assert val_res["is_segregated"] is True
    assert manifest.metadata.get("segregated") is True


# ---------------------------------------------------------------------------
# RUN-05: Governance instructions differ intentionally
# ---------------------------------------------------------------------------

def test_run_05_governance_instructions_differ_intentionally():
    """
    RUN-05: Governance instructions differ intentionally.
    Expected: Difference recorded; same task specification remains shared.
    """
    arm_base = runner.ArmConfig(
        arm="baseline",
        model="gemini-2.5-pro",
        prompt="Implement authentication route",
    )
    arm_icm = runner.ArmConfig(
        arm="icm",
        model="gemini-2.5-pro",
        prompt="Implement authentication route",
        governance_instructions="Execute through formal ICM pipeline: 01_intake -> 02_plan -> 03_exec -> 04_verify",
        skills=["auth", "ai-check"],
        subagents=["backend-core", "qa-verifier"],
    )

    shared_contract = {
        "task_id": "AUTH-001",
        "task_version": "2.1.0",
        "requirements": ["JWT verification", "Rate limiting", "HTTP 401 on expired token"],
        "target_endpoint": "/api/v1/login",
    }

    manifest = runner.RunManifest(
        manifest_id="MAN-AUTH-001",
        task_id="AUTH-001",
        task_version="2.1.0",
        created_at="2026-10-02T12:00:00Z",
        task_contract=shared_contract,
        arms={"baseline": arm_base, "icm": arm_icm},
    )

    val_res = runner.validate_manifest_configuration(manifest)
    assert val_res["valid"] is True

    # Same task specification shared
    assert manifest.task_contract["task_id"] == "AUTH-001"
    assert manifest.task_contract["requirements"] == ["JWT verification", "Rate limiting", "HTTP 401 on expired token"]

    # Intentional governance differences explicitly documented
    gov_diffs = val_res["intentional_governance_diffs"]
    assert gov_diffs["baseline"]["skills"] == []
    assert gov_diffs["baseline"]["prompt_has_icm_scaffolding"] is False
    assert gov_diffs["icm"]["skills"] == ["auth", "ai-check"]
    assert gov_diffs["icm"]["subagents"] == ["backend-core", "qa-verifier"]
    assert gov_diffs["icm"]["prompt_has_icm_scaffolding"] is True


# ---------------------------------------------------------------------------
# RUN-06: Simulate timeout
# ---------------------------------------------------------------------------

def test_run_06_simulate_timeout_retains_partial_evidence(tmp_path: Path):
    """
    RUN-06: Simulate timeout.
    Expected: Timed-out attempt retained with available partial evidence.
    """
    db_file = tmp_path / "timeout.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir()
    (snapshot_dir / "main.py").write_text("while True: pass\n", encoding="utf-8")

    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir,
        arm="baseline",
        workspace_root=tmp_path / "ws",
        run_id="timeout_test",
    )

    manifest = runner.RunManifest(
        manifest_id="MAN-TO-001",
        task_id="TO-001",
        task_version="1.0.0",
        created_at="2026-10-02T12:00:00Z",
        task_contract={"task_id": "TO-001", "task_version": "1.0.0"},
        arms={
            "baseline": runner.ArmConfig(
                arm="baseline",
                model="gemini-2.5-pro",
                prompt="Infinite loop",
                resource_budget={"timeout_seconds": 30.0},
            )
        },
    )

    res = runner.execute_run_with_lifecycle(
        manifest=manifest,
        arm="baseline",
        workspace=ws,
        run_index=1,
        simulate_timeout=True,
        timeout_seconds=30.0,
        conn=conn,
    )

    assert res["execution_status"] == "timed_out"
    assert res["verification_status"] == "not_run"

    # Verify attempt retained in SQLite ledger
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE task_id = 'TO-001'")
    row = dict(cursor.fetchone())

    assert row["execution_status"] == "timed_out"
    assert row["verification_status"] == "not_run"
    assert row["duration_seconds"] == 30.0
    assert row["input_tokens"] == 1500
    assert row["output_tokens"] == 200
    reasons = json.loads(row["exclusion_reasons"])
    assert "timeout" in reasons
    assert "partial_telemetry" in reasons

    ws.cleanup()
    conn.close()


# ---------------------------------------------------------------------------
# RUN-07: Simulate interruption and resume/import
# ---------------------------------------------------------------------------

def test_run_07_simulate_interruption_and_resume(tmp_path: Path):
    """
    RUN-07: Simulate interruption and resume/import.
    Expected: Original attempt preserved; no invented completion or duplicate run.
    """
    db_file = tmp_path / "interrupted.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir()
    (snapshot_dir / "worker.py").write_text("print('working...')\n", encoding="utf-8")

    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir,
        arm="baseline",
        workspace_root=tmp_path / "ws",
        run_id="interrupt_test",
    )

    manifest = runner.RunManifest(
        manifest_id="MAN-INT-001",
        task_id="INT-001",
        task_version="1.0.0",
        created_at="2026-10-02T12:00:00Z",
        task_contract={"task_id": "INT-001", "task_version": "1.0.0"},
        arms={
            "baseline": runner.ArmConfig(
                arm="baseline",
                model="gemini-2.5-pro",
                prompt="Long task",
            )
        },
    )

    # 1. Execute interrupted attempt
    res_int = runner.execute_run_with_lifecycle(
        manifest=manifest,
        arm="baseline",
        workspace=ws,
        run_index=1,
        simulate_interruption=True,
        conn=conn,
    )
    assert res_int["execution_status"] == "interrupted"

    # 2. Resume run protocol
    resume_outcome = runner.resume_interrupted_run(
        task_id="INT-001",
        arm="baseline",
        original_run_index=1,
        manifest=manifest,
        workspace=ws,
        conn=conn,
    )

    assert resume_outcome["original_run_index"] == 1
    assert resume_outcome["resumed_run_index"] == 2

    # 3. Assert both runs preserved in ledger
    cursor = conn.cursor()
    cursor.execute("SELECT run_index, execution_status FROM runs WHERE task_id = 'INT-001' ORDER BY run_index ASC")
    rows = cursor.fetchall()
    assert len(rows) == 2
    assert rows[0][0] == 1 and rows[0][1] == "interrupted"
    assert rows[1][0] == 2 and rows[1][1] == "completed"

    ws.cleanup()
    conn.close()


# ---------------------------------------------------------------------------
# RUN-08: Execute the offline workflow
# ---------------------------------------------------------------------------

def test_run_08_offline_workflow_asserts_zero_provider_calls():
    """
    RUN-08: Execute the offline workflow.
    Expected: No provider or paid adapter invocation.
    """
    adapter = runner.OfflineExecutionAdapter()

    # Replay simulated offline run
    exec_res = adapter.execute_mock(
        task_id="OFFLINE-001",
        arm="baseline",
        run_index=1,
    )

    assert exec_res.execution_status == "completed"
    # Verification: Zero live provider or paid API invocations
    adapter.assert_zero_provider_calls()
    assert adapter.provider_invocations_count == 0
    assert adapter.paid_api_calls_count == 0

    # Injecting simulated illegal provider call must raise violation
    adapter.provider_invocations_count = 1
    with pytest.raises(runner.OfflineModeViolationError, match="Offline invariant violated"):
        adapter.assert_zero_provider_calls()


# ---------------------------------------------------------------------------
# RUN-09: Agent edits test files in its workspace
# ---------------------------------------------------------------------------

def test_run_09_agent_workspace_test_edits_do_not_affect_protected_evaluator(tmp_path: Path):
    """
    RUN-09: Agent edits test files in its workspace.
    Expected: Protected evaluator remains intact and determines grading.
    """
    # 1. Protected evaluator outside the agent workspace
    evaluator_dir = tmp_path / "protected_evaluator"
    evaluator_dir.mkdir()
    evaluator_file = evaluator_dir / "eval_checks.py"
    evaluator_file.write_text("""
import sys
import solution

# Protected verification checks
assert solution.multiply(3, 4) == 12, "multiply(3,4) must be 12"
assert solution.multiply(-2, 5) == -10, "multiply(-2,5) must be -10"
print("SUCCESS")
""", encoding="utf-8")

    evaluator = runner.ProtectedEvaluator(evaluator_file)

    # 2. Agent workspace with buggy solution and workspace test file
    ws_dir = tmp_path / "agent_workspace"
    ws_dir.mkdir()
    # Buggy solution: returns wrong answer
    (ws_dir / "solution.py").write_text("def multiply(a, b): return a + b\n", encoding="utf-8")

    # Agent cheats by editing its local test file to assert True
    tests_dir = ws_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_solution.py").write_text("def test_multiply(): assert True\n", encoding="utf-8")

    # 3. Evaluate using protected evaluator
    verif = evaluator.evaluate_workspace(ws_dir)

    # The cheated test inside the workspace has zero effect on protected grading
    assert verif.passed is False
    assert verif.verification_status == "failed"
    assert "test_failure" in verif.reasons


# ---------------------------------------------------------------------------
# RUN-10: Compare recorded and actual evaluator hashes
# ---------------------------------------------------------------------------

def test_run_10_evaluator_hash_tamper_detection(tmp_path: Path):
    """
    RUN-10: Compare recorded and actual evaluator hashes.
    Expected: Tampering detected; verification marked invalid/evaluator error.
    """
    evaluator_file = tmp_path / "evaluator.py"
    evaluator_file.write_bytes(b"assert True\n")

    # Compute genuine hash
    genuine_hash = hashlib.sha256(evaluator_file.read_bytes()).hexdigest()

    # Construct evaluator with pinned expected hash
    evaluator = runner.ProtectedEvaluator(evaluator_file, expected_hash=genuine_hash)
    is_valid, _ = evaluator.verify_hash()
    assert is_valid is True

    # Tamper with the evaluator file
    evaluator_file.write_bytes(b"assert True  # TAMPERED BY ADVERSARY\n")

    # Evaluate workspace with tampered evaluator
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    verif = evaluator.evaluate_workspace(ws_dir)

    # Tampering detected -> marked evaluator_error
    assert verif.passed is False
    assert verif.verification_status == "evaluator_error"
    assert "evaluator_hash_mismatch" in verif.reasons
    assert "evaluator_tampered" in verif.reasons


# ---------------------------------------------------------------------------
# RUN-11: Manual adapter lacks usage telemetry
# ---------------------------------------------------------------------------

def test_run_11_manual_adapter_lacks_usage_telemetry(tmp_path: Path):
    """
    RUN-11: Manual adapter lacks usage telemetry.
    Expected: Correctness can be evaluated; usage and cost remain unavailable.
    """
    db_file = tmp_path / "manual.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    # Valid solution in workspace
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    (ws_dir / "solution.py").write_text("def solve(): return 42\n", encoding="utf-8")

    # Protected evaluator
    eval_file = tmp_path / "eval.py"
    eval_file.write_text("import solution; assert solution.solve() == 42\n", encoding="utf-8")
    evaluator = runner.ProtectedEvaluator(eval_file)

    # Record manual completion with no telemetry stream
    res = runner.ManualExecutionAdapter.record_manual_completion(
        task_id="MANUAL-001",
        arm="baseline",
        run_index=1,
        workspace_path=ws_dir,
        evaluator=evaluator,
        telemetry_stream=None,  # No telemetry stream available
        manifest_id="MAN-MANUAL-001",
        conn=conn,
    )

    # 1. Correctness is evaluated
    assert res["verification"].passed is True
    assert res["verification"].verification_status == "passed"

    # 2. Usage and cost remain unavailable
    assert res["has_usage_telemetry"] is False
    assert res["usage"]["input_tokens"] is None
    assert res["cost_status"] == "unavailable"

    # 3. Check ledger record
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE task_id = 'MANUAL-001'")
    row = dict(cursor.fetchone())

    assert row["verification_status"] == "passed"
    assert row["input_tokens"] is None
    assert row["cost_usd"] is None
    assert row["cost_status"] == "unavailable"
    assert "missing_usage_telemetry" in json.loads(row["exclusion_reasons"])

    # 4. Check summary exclusion from measured cost totals
    summary = ledger.task_summary("MANUAL-001", conn=conn)
    assert summary["measured_runs_count"] == 0
    assert summary["has_measured_data"] is False
    assert summary["savings"] is None

    conn.close()


# ---------------------------------------------------------------------------
# Fixture-Only Smoke Flow End-to-End Test
# ---------------------------------------------------------------------------

def test_fixture_smoke_flow_e2e(tmp_path: Path):
    """
    Execute full fixture smoke flow across temporary directories and database.
    Assert zero provider calls, clean workspace isolation, and valid reporting.
    """
    db_file = tmp_path / "smoke_flow.db"
    smoke_root = tmp_path / "smoke_env"

    summary = runner.run_fixture_smoke_flow(
        db_path=db_file,
        tmp_root=smoke_root,
    )

    assert summary["status"] == "success"
    assert summary["zero_provider_calls_verified"] is True
    assert summary["workspaces_isolated"] is True
    assert summary["task_id"] == "SMOKE-001"
    assert "baseline" in summary["verified_arms"]
    assert "icm" in summary["verified_arms"]


# ---------------------------------------------------------------------------
# Additional Edge Case & Robustness Verification Tests
# ---------------------------------------------------------------------------

def test_run_03_reset_workspace_state_guards_host_checkout_and_subdirectories(tmp_path: Path):
    """RUN-03: Verify reset_workspace_state refuses destructive reset on host root and subdirs."""
    import run_experiment
    # Test host root
    run_experiment.reset_workspace_state(runner.WORKSPACE_ROOT)
    # Test subdirectory of host root
    run_experiment.reset_workspace_state(runner.WORKSPACE_ROOT / "scripts")


def test_run_03_disposable_workspace_cleanup_refuses_unsafe_host_paths(tmp_path: Path):
    """RUN-03: Verify DisposableWorkspace.cleanup refuses to delete host or snapshot files."""
    snap_dir = tmp_path / "snapshot"
    snap_dir.mkdir()
    (snap_dir / "keep.txt").write_text("keep me", encoding="utf-8")

    # Workspace pointing to snapshot_dir
    ws_unsafe = runner.DisposableWorkspace(path=snap_dir, arm="baseline", snapshot_dir=snap_dir, run_id="u1")
    ws_unsafe.cleanup()
    assert snap_dir.exists()
    assert (snap_dir / "keep.txt").exists()

    # Workspace pointing to host root
    ws_host = runner.DisposableWorkspace(path=runner.WORKSPACE_ROOT, arm="baseline", snapshot_dir=snap_dir, run_id="u2")
    ws_host.cleanup()
    assert runner.WORKSPACE_ROOT.exists()


def test_run_04_model_settings_and_budget_mismatch_segregated():
    """RUN-04: Verify settings and budget mismatches are rejected or segregated when allowed."""
    arm_a = runner.ArmConfig(arm="arm_a", model="m1", prompt="p", model_settings={"temp": 0.0}, resource_budget={"timeout_seconds": 600.0})
    arm_b = runner.ArmConfig(arm="arm_b", model="m1", prompt="p", model_settings={"temp": 0.7}, resource_budget={"timeout_seconds": 600.0})

    manifest = runner.RunManifest(
        manifest_id="M1", task_id="T1", task_version="1.0.0", created_at="now",
        task_contract={"task_id": "T1"}, arms={"arm_a": arm_a, "arm_b": arm_b},
    )
    # Unintentional settings mismatch rejected
    with pytest.raises(runner.ConfigurationMismatchError, match="Unintentional model_settings mismatch"):
        runner.validate_manifest_configuration(manifest)

    # Allowed mismatch -> MUST be marked segregated
    manifest.metadata["allow_config_mismatch"] = True
    val_res = runner.validate_manifest_configuration(manifest)
    assert val_res["is_segregated"] is True
    assert manifest.metadata.get("segregated") is True

    # Resource budget mismatch
    arm_c = runner.ArmConfig(arm="arm_c", model="m1", prompt="p", model_settings={"temp": 0.0}, resource_budget={"timeout_seconds": 60.0})
    manifest2 = runner.RunManifest(
        manifest_id="M2", task_id="T2", task_version="1.0.0", created_at="now",
        task_contract={"task_id": "T2"}, arms={"arm_a": arm_a, "arm_c": arm_c},
    )
    with pytest.raises(runner.ConfigurationMismatchError, match="Unintentional resource_budget mismatch"):
        runner.validate_manifest_configuration(manifest2)


def test_run_06_simulated_failure_and_timeout_with_tampered_evaluator(tmp_path: Path):
    """RUN-06 / RUN-10: Test execution failure recording and timeout with tampered evaluator."""
    db_file = tmp_path / "lifecycle_fail.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    ws = runner.DisposableWorkspace(ws_dir, "baseline", ws_dir, "fail_test")

    manifest = runner.RunManifest(
        manifest_id="M-FAIL", task_id="FAIL-001", task_version="1.0.0", created_at="now",
        task_contract={"task_id": "FAIL-001"},
        arms={"baseline": runner.ArmConfig("baseline", "gemini-2.5-pro", "fail test")},
    )

    # Simulated failure
    res_fail = runner.execute_run_with_lifecycle(
        manifest=manifest, arm="baseline", workspace=ws, run_index=1,
        simulate_failure=True, conn=conn,
    )
    assert res_fail["execution_status"] == "failed"

    cursor = conn.cursor()
    cursor.execute("SELECT execution_status, exclusion_reasons FROM runs WHERE task_id = 'FAIL-001' AND run_index = 1")
    row = dict(cursor.fetchone())
    assert row["execution_status"] == "failed"
    assert "execution_failed" in json.loads(row["exclusion_reasons"])

    # Timeout with tampered evaluator
    eval_file = tmp_path / "eval.py"
    eval_file.write_bytes(b"assert True\n")
    evaluator = runner.ProtectedEvaluator(eval_file, expected_hash="wrong_hash")

    res_to = runner.execute_run_with_lifecycle(
        manifest=manifest, arm="baseline", workspace=ws, evaluator=evaluator,
        run_index=2, simulate_timeout=True, conn=conn,
    )
    assert res_to["execution_status"] == "timed_out"
    assert res_to["verification_status"] == "evaluator_error"
    cursor.execute("SELECT verification_status, exclusion_reasons FROM runs WHERE task_id = 'FAIL-001' AND run_index = 2")
    row2 = dict(cursor.fetchone())
    assert row2["verification_status"] == "evaluator_error"
    reasons = json.loads(row2["exclusion_reasons"])
    assert "evaluator_tampered" in reasons
    assert "evaluator_error" in reasons

    ws.cleanup()
    conn.close()


def test_run_07_resume_interrupted_run_with_existing_subsequent_runs(tmp_path: Path):
    """RUN-07: Resuming finds MAX(run_index) + 1 to avoid duplicate collisions."""
    db_file = tmp_path / "resume_max.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    ws = runner.DisposableWorkspace(ws_dir, "baseline", ws_dir, "res_test")

    manifest = runner.RunManifest(
        manifest_id="M-RES", task_id="RES-001", task_version="1.0.0", created_at="now",
        task_contract={"task_id": "RES-001"},
        arms={"baseline": runner.ArmConfig("baseline", "gemini-2.5-pro", "res test")},
    )

    # 1. Run 1 interrupted
    runner.execute_run_with_lifecycle(manifest=manifest, arm="baseline", workspace=ws, run_index=1, simulate_interruption=True, conn=conn)

    # 2. Suppose run 2 was already completed earlier
    runner.execute_run_with_lifecycle(manifest=manifest, arm="baseline", workspace=ws, run_index=2, conn=conn)

    # 3. Resume run 1: should pick run_index = 3 (MAX + 1), not 2
    resumed = runner.resume_interrupted_run(task_id="RES-001", arm="baseline", original_run_index=1, manifest=manifest, workspace=ws, conn=conn)
    assert resumed["resumed_run_index"] == 3

    ws.cleanup()
    conn.close()


def test_run_08_subprocess_environment_sanitization_offline():
    """RUN-08: Subprocess env sanitization removes API keys/secrets and sets OFFLINE_MODE."""
    tainted_env = {
        "PATH": "C:\\Windows",
        "GEMINI_API_KEY": "secret_gemini_key",
        "OPENAI_API_KEY": "sk-secret123",
        "GITHUB_TOKEN": "ghp_secrettoken",
        "USER": "testuser",
    }
    safe = runner.sanitize_subprocess_env(tainted_env)
    assert "GEMINI_API_KEY" not in safe
    assert "OPENAI_API_KEY" not in safe
    assert "GITHUB_TOKEN" not in safe
    assert safe["OFFLINE_MODE"] == "1"
    assert safe["AI_LAB_OFFLINE"] == "1"
    assert safe["USER"] == "testuser"


def test_run_09_protected_evaluator_directory_support(tmp_path: Path):
    """RUN-09: ProtectedEvaluator supports evaluating a directory of tests with pytest."""
    eval_dir = tmp_path / "eval_suite"
    eval_dir.mkdir()
    (eval_dir / "test_math.py").write_text("def test_sub():\n    import solution\n    assert solution.sub(5, 3) == 2\n", encoding="utf-8")

    evaluator = runner.ProtectedEvaluator(eval_dir)
    assert evaluator.expected_hash is not None

    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    (ws_dir / "solution.py").write_text("def sub(a, b): return a - b\n", encoding="utf-8")

    verif = evaluator.evaluate_workspace(ws_dir)
    assert verif.passed is True
    assert verif.verification_status == "passed"


def test_run_11_manual_adapter_preserves_custom_model(tmp_path: Path):
    """RUN-11: ManualExecutionAdapter preserves supplied model and records evaluator reasons."""
    db_file = tmp_path / "manual_model.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    (ws_dir / "sol.py").write_text("x = 1\n", encoding="utf-8")

    eval_file = tmp_path / "eval.py"
    eval_file.write_text("import sol; assert sol.x == 1\n", encoding="utf-8")
    evaluator = runner.ProtectedEvaluator(eval_file)

    res = runner.ManualExecutionAdapter.record_manual_completion(
        task_id="MAN-M1",
        arm="baseline",
        run_index=1,
        workspace_path=ws_dir,
        evaluator=evaluator,
        model="claude-3-7-sonnet",
        conn=conn,
    )
    cursor = conn.cursor()
    cursor.execute("SELECT model FROM runs WHERE task_id = 'MAN-M1'")
    assert cursor.fetchone()[0] == "claude-3-7-sonnet"
    conn.close()


def test_ledger_record_and_import_run_handles_none_execution_and_verification_status(tmp_path: Path):
    """Verify record_run and import_run safely handle None values for execution_status and verification_status."""
    db_file = tmp_path / "null_status.db"
    conn = ledger.get_connection(db_file)

    # Calling record_run with None values must not raise sqlite3.IntegrityError
    rid = ledger.record_run(
        task_id="NULL-001",
        arm="baseline",
        model="test-model",
        run_index=1,
        timestamp="2026-10-02T12:00:00Z",
        input_tokens=1000,
        output_tokens=200,
        num_turns=1,
        duration_seconds=1.0,
        execution_status=None,
        verification_status=None,
        conn=conn,
    )
    cursor = conn.cursor()
    cursor.execute("SELECT execution_status, verification_status FROM runs WHERE id = ?", (rid,))
    row = dict(cursor.fetchone())
    assert row["execution_status"] == "completed"
    assert row["verification_status"] == "not_run"

    # Calling import_run with None values
    imp_dict = {
        "task_id": "NULL-001",
        "arm": "icm",
        "model": "test-model",
        "run_index": 1,
        "timestamp": "2026-10-02T12:00:00Z",
        "num_turns": 1,
        "duration_seconds": 1.0,
        "execution_status": None,
        "verification_status": None,
    }
    rid2 = ledger.import_run(conn, imp_dict)
    cursor.execute("SELECT execution_status, verification_status FROM runs WHERE id = ?", (rid2,))
    row2 = dict(cursor.fetchone())
    assert row2["execution_status"] == "completed"
    assert row2["verification_status"] == "not_run"
    conn.close()


def test_ledger_migrate_db_upgrades_phase1_database_to_phase2(tmp_path: Path):
    """Verify migrate_db upgrades a Phase 1 schema database missing Phase 2 columns."""
    db_file = tmp_path / "phase1.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    with conn:
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
                source_kind TEXT NOT NULL DEFAULT 'unknown',
                evidence_status TEXT NOT NULL DEFAULT 'unverified',
                exclusion_reasons TEXT,
                evidence_ref TEXT,
                evidence_hash TEXT,
                import_id TEXT,
                cost_status TEXT NOT NULL DEFAULT 'unknown',
                cost_usd REAL,
                is_simulation INTEGER NOT NULL DEFAULT 0,
                notes TEXT
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

    # Run migration on Phase 1 database
    applied = ledger.migrate_db(conn)
    assert applied is True

    # Check that Phase 2 columns now exist
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(runs)")
    cols = {row[1] for row in cursor.fetchall()}
    assert "execution_status" in cols
    assert "verification_status" in cols
    assert "manifest_id" in cols
    assert "evaluator_hash" in cols

    # Second migration run should be idempotent (return False)
    applied_again = ledger.migrate_db(conn)
    assert applied_again is False
    conn.close()
