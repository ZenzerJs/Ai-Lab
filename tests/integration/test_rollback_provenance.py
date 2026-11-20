import json
import subprocess
from pathlib import Path
import pytest

import ledger
import runner


BENCH_002_DIR = runner.WORKSPACE_ROOT / "benchmarks" / "BENCH-002"
BASELINE_EXP006_NDJSON = (
    runner.WORKSPACE_ROOT / "experiments" / "evidence" / "live_EXP-006_baseline_run1_1791066412.ndjson"
)


class _MutatingFailureAdapter(runner.OfflineExecutionAdapter):
    """Adapter that injects a multi-file breaking edit and stray rogue.py during execution."""

    def __init__(self, workspace_path: Path):
        super().__init__()
        self.workspace_path = workspace_path

    def execute_mock(
        self,
        task_id: str,
        arm: str,
        run_index: int = 1,
        simulate_timeout: bool = False,
        simulate_interruption: bool = False,
        simulate_failure: bool = False,
        timeout_seconds: float = 600.0,
    ) -> runner.ExecutionResult:
        # Multi-file breaking edit + stray rogue.py
        (self.workspace_path / "api_server.py").write_text(
            "def handle_get_items(params=None):\n    return {'broken': True}\n\ndef handle_health_check():\n    return {'status': 'healthy', 'version': '1.2.0'}\n",
            encoding="utf-8",
        )
        (self.workspace_path / "api_client.py").write_text(
            "class ApiClient:\n    def __init__(self, server): pass\n    def fetch_items_page(self, page=1, page_size=10): raise RuntimeError('broken')\n",
            encoding="utf-8",
        )
        (self.workspace_path / "rogue.py").write_text("# stray file left by failing agent\n", encoding="utf-8")

        events = [
            json.dumps({
                "event": "step_update",
                "step_update": {
                    "step_index": 1,
                    "state": "DONE",
                    "step_type": "tool",
                    "tool_name": "write_to_file",
                    "tool_info": {"parameters": {"TargetFile": "rogue.py"}},
                },
            }),
            json.dumps({
                "event": "run_complete",
                "num_turns": 2,
                "duration_seconds": 3.5,
                "usage": {
                    "input_tokens": 1200,
                    "output_tokens": 250,
                    "thinking_tokens": 0,
                    "cache_read_tokens": 0,
                    "total_tokens": 1450,
                },
            }),
        ]
        return runner.ExecutionResult(
            execution_status="completed",
            duration_seconds=3.5,
            num_turns=2,
            usage={
                "input_tokens": 1200,
                "output_tokens": 250,
                "thinking_tokens": 0,
                "cache_read_tokens": 0,
                "total_tokens": 1450,
            },
            partial_events=events,
            evidence_ref="synthetic_mutating_fixture",
        )


def test_rollback_and_provenance_on_failed_bench002(tmp_path: Path):
    """
    Prepare DisposableWorkspace from benchmarks/BENCH-002, inject multi-file breaking edit +
    stray rogue.py, run execute_run_with_lifecycle with ProtectedEvaluator, assert:
    - verification_status == 'failed'
    - workspace auto-rolled back (rogue.py removed, hash == pre-run hash)
    - SQLite run_events has start, verify(failed), rollback(rolled_back) in order
    """
    db_file = tmp_path / "rollback_prov.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    snapshot_dir = BENCH_002_DIR / "workspace"
    evaluator = runner.ProtectedEvaluator(BENCH_002_DIR / "evaluator")

    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir,
        arm="baseline",
        workspace_root=tmp_path / "workspaces",
        run_id="rollback_bench002",
    )

    try:
        pre_hash = ws.snapshot_tree_hash()
        orig_server = (ws.path / "api_server.py").read_text(encoding="utf-8")
        orig_client = (ws.path / "api_client.py").read_text(encoding="utf-8")

        manifest = runner.RunManifest(
            manifest_id="MAN-RB-002",
            task_id="BENCH-002",
            task_version="1.0.0",
            created_at="2026-11-20T00:00:00Z",
            task_contract={"task_id": "BENCH-002", "task_version": "1.0.0"},
            arms={
                "baseline": runner.ArmConfig(
                    arm="baseline",
                    model="gemini-2.5-pro",
                    prompt="Implement paginated endpoint",
                )
            },
        )

        adapter = _MutatingFailureAdapter(ws.path)
        res = runner.execute_run_with_lifecycle(
            manifest=manifest,
            arm="baseline",
            workspace=ws,
            evaluator=evaluator,
            adapter=adapter,
            run_index=1,
            conn=conn,
            rollback_on_failure=True,
        )

        assert res["verification_status"] == "failed"
        assert res["rolled_back"] is True
        assert res["pre_hash"] == pre_hash
        assert res["post_hash"] != pre_hash
        assert res["restored_hash"] == pre_hash

        # Workspace must be restored bit-for-bit and rogue.py removed
        assert not (ws.path / "rogue.py").exists()
        assert (ws.path / "api_server.py").read_text(encoding="utf-8") == orig_server
        assert (ws.path / "api_client.py").read_text(encoding="utf-8") == orig_client
        assert ws.snapshot_tree_hash() == pre_hash

        # Verify SQLite run_events order and hashes
        events = ledger.get_run_events(res["run_id"], conn=conn)
        phases_statuses = [(e["phase"], e["status"]) for e in events]
        assert phases_statuses == [
            ("start", "started"),
            ("tool", "DONE"),
            ("verify", "failed"),
            ("rollback", "rolled_back"),
        ]
        assert [e["seq"] for e in events] == sorted(e["seq"] for e in events)
        assert events[0]["diff_hash"] == pre_hash
        assert events[1]["tool_name"] == "write_to_file"
        assert events[1]["target_path"] == "rogue.py"
        assert events[2]["diff_hash"] == res["post_hash"]
        assert events[3]["diff_hash"] == pre_hash
        assert events[3]["rollback_ref"] == pre_hash
    finally:
        ws.cleanup()
        assert not ws.backup_dir.exists()
        conn.close()


def test_rollback_disabled_preserves_modified_workspace_and_omits_rollback_event(tmp_path: Path):
    """Verify rollback_on_failure=False retains broken edits and omits rollback event."""
    db_file = tmp_path / "no_rollback.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    evaluator = runner.ProtectedEvaluator(BENCH_002_DIR / "evaluator")
    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=BENCH_002_DIR / "workspace",
        arm="baseline",
        workspace_root=tmp_path / "workspaces",
        run_id="no_rb_bench002",
    )

    try:
        ws.capture_backup()
        pre_hash = ws.snapshot_tree_hash()

        # Pre-inject breaking edits after capturing backup
        (ws.path / "rogue.py").write_text("x = 1\n", encoding="utf-8")
        (ws.path / "api_server.py").write_text("broken = True\n", encoding="utf-8")

        manifest = runner.RunManifest(
            manifest_id="MAN-NORB-002",
            task_id="BENCH-002",
            task_version="1.0.0",
            created_at="2026-11-20T00:00:00Z",
            task_contract={"task_id": "BENCH-002"},
            arms={"baseline": runner.ArmConfig("baseline", "gemini-2.5-pro", "test")},
        )

        res = runner.execute_run_with_lifecycle(
            manifest=manifest,
            arm="baseline",
            workspace=ws,
            evaluator=evaluator,
            run_index=1,
            conn=conn,
            rollback_on_failure=False,
        )

        assert res["verification_status"] == "failed"
        assert res["rolled_back"] is False
        assert (ws.path / "rogue.py").exists()
        assert ws.snapshot_tree_hash() != pre_hash

        events = ledger.get_run_events(res["run_id"], conn=conn)
        assert [(e["phase"], e["status"]) for e in events] == [
            ("start", "started"),
            ("verify", "failed"),
        ]
    finally:
        ws.cleanup()
        conn.close()


def test_run_benchmark_live_with_mocked_agy_cli_and_unpriced_model(tmp_path: Path, monkeypatch):
    """
    Verify run_benchmark_live invokes agy CLI with expected flags, writes LF NDJSON evidence,
    parses tokens + tool_metrics, rolls back failing workspace, marks unpriced model as
    cost_status='unavailable', records run_events, and cleans up workspace.
    """
    db_file = tmp_path / "live_bench.db"
    evidence_dir = tmp_path / "evidence"
    ws_root = tmp_path / "workspaces"
    monkeypatch.setattr(runner, "DEFAULT_EVIDENCE_DIR", evidence_dir)

    raw_ndjson = BASELINE_EXP006_NDJSON.read_bytes()
    captured_calls = []
    orig_subprocess_run = subprocess.run

    def fake_subprocess_run(cmd, **kwargs):
        if cmd and cmd[0] == "agy":
            captured_calls.append({"cmd": cmd, "kwargs": kwargs})
            # Simulate agent creating a stray file inside workspace cwd before failing benchmark
            cwd_path = Path(kwargs["cwd"])
            (cwd_path / "rogue.py").write_text("# stray artifact\n", encoding="utf-8")
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=raw_ndjson,
                stderr=b"",
            )
        return orig_subprocess_run(cmd, **kwargs)

    monkeypatch.setattr(runner.subprocess, "run", fake_subprocess_run)

    res = runner.run_benchmark_live(
        task_id="BENCH-002",
        arm="icm",
        run_index=1,
        model="gemini-4-hydrogen-low",
        cli_cmd="agy",
        timeout_seconds=180,
        db_path=db_file,
        workspace_root=ws_root,
    )

    assert len(captured_calls) == 1
    cmd = captured_calls[0]["cmd"]
    assert cmd[0] == "agy"
    assert "--output-format" in cmd and "stream-json" in cmd
    assert "--model" in cmd and "gemini-4-hydrogen-low" in cmd
    assert "--dangerously-skip-permissions" in cmd
    assert "--print-timeout" in cmd and "180s" in cmd
    assert captured_calls[0]["kwargs"]["stdin"] == subprocess.DEVNULL
    assert "4-stage ICM contract" in cmd[cmd.index("-p") + 1]
    assert "BENCH-002: Cross-File API Contract" in cmd[cmd.index("-p") + 1]

    # BENCH-002 baseline workspace is broken -> verification failed -> auto-rolled back
    assert res["execution_status"] == "completed"
    assert res["verification_status"] == "failed"
    assert res["rolled_back"] is True
    assert res["restored_hash"] == res["pre_hash"]
    assert res["post_hash"] != res["pre_hash"]
    assert res["cost_status"] == "unavailable"
    assert res["cost_usd"] is None
    assert res["tool_metrics"]["tool_calls_count"] == 61
    assert res["tool_metrics"]["tool_errors_count"] == 3
    assert res["tool_metrics"]["max_consecutive_tool_streak"] == 7
    assert res["tool_metrics"]["loop_detected"] is True

    # Evidence file saved with pure LF endings
    ev_files = list(evidence_dir.glob("live_BENCH-002_gemini-4-hydrogen-low_icm_run1_*.ndjson"))
    assert len(ev_files) == 1
    assert b"\r\n" not in ev_files[0].read_bytes()

    # Disposable workspace and backup cleaned up
    assert list(ws_root.iterdir()) == []

    # Verify DB run and run_events
    conn = ledger.get_connection(db_file)
    row = dict(conn.execute("SELECT * FROM runs WHERE id = ?", (res["run_id"],)).fetchone())
    assert row["tool_calls_count"] == 61
    assert row["tool_errors_count"] == 3
    assert row["max_consecutive_tool_streak"] == 7
    assert row["loop_detected"] == 1
    assert row["cost_status"] == "unavailable"

    events = ledger.get_run_events(res["run_id"], conn=conn)
    assert events[0]["phase"] == "start"
    assert events[-2]["phase"] == "verify"
    assert events[-2]["status"] == "failed"
    assert events[-1]["phase"] == "rollback"
    assert events[-1]["status"] == "rolled_back"
    assert len(events) == 1 + 61 + 2
    conn.close()
