#!/usr/bin/env python3
"""Unit tests for infra_error classification, 1x bounded retry, and --start-repetition."""

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = WORKSPACE_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import campaign
import ledger
import runner


def _ok_result_ndjson() -> bytes:
    events = [
        {
            "event": "step_update",
            "step_update": {
                "step_index": 1,
                "step_type": "agent_response",
                "usage": {
                    "input_tokens": 1200,
                    "cache_read_tokens": 0,
                    "output_tokens": 150,
                    "thinking_tokens": 0,
                },
            },
        },
        {
            "event": "result",
            "result": {
                "status": "SUCCESS",
                "response": "done",
                "duration_seconds": 1.2,
                "num_turns": 1,
                "usage": {
                    "input_tokens": 1200,
                    "cache_read_tokens": 0,
                    "output_tokens": 150,
                    "thinking_tokens": 0,
                    "total_tokens": 1350,
                },
            },
        },
    ]
    return ("\n".join(json.dumps(e) for e in events) + "\n").encode("utf-8")


def _infra_fail_ndjson() -> bytes:
    return (
        json.dumps(
            {
                "event": "result",
                "result": {
                    "status": "ERROR",
                    "error": "failed to start conversation: backend returned an empty conversation id",
                    "duration_seconds": 0,
                    "num_turns": 0,
                    "usage": {
                        "input_tokens": 0,
                        "cache_read_tokens": 0,
                        "output_tokens": 0,
                        "thinking_tokens": 0,
                        "total_tokens": 0,
                    },
                },
            }
        )
        + "\n"
    ).encode("utf-8")


def test_infra_error_retries_once_and_preserves_attempt_metadata(tmp_path, monkeypatch):
    ev_dir = tmp_path / "evidence"
    monkeypatch.setattr(runner, "DEFAULT_EVIDENCE_DIR", ev_dir)

    db_path = tmp_path / "usage.db"
    conn = ledger.get_connection(db_path)
    ledger.init_db(conn)
    ledger.seed_pricing(WORKSPACE_ROOT / "config" / "PRICING.json", conn=conn)
    conn.close()

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if len(calls) == 1:
            return subprocess.CompletedProcess(cmd, 1, stdout=_infra_fail_ndjson(), stderr=b"")
        return subprocess.CompletedProcess(cmd, 0, stdout=_ok_result_ndjson(), stderr=b"")

    with (
        mock.patch.object(runner.subprocess, "run", side_effect=fake_run),
        mock.patch.object(runner.ProtectedEvaluator, "evaluate_workspace") as mock_eval,
    ):
        ev_inst = runner.ProtectedEvaluator(WORKSPACE_ROOT / "benchmarks" / "BENCH-005" / "evaluator")
        _, ev_hash = ev_inst.verify_hash()
        mock_eval.return_value = runner.VerificationResult(
            verification_status="passed",
            passed=True,
            reasons=[],
            evaluator_hash=ev_hash,
            output="ok",
        )
        res = runner.run_benchmark_live(
            task_id="BENCH-005",
            arm="icm_v3",
            run_index=2,
            model="gemini-3.8-flash-low",
            db_path=db_path,
            mode="icm-v3",
            max_infra_retries=1,
            infra_retry_backoff_seconds=0.0,
        )

    assert len(calls) == 2
    assert res["execution_status"] == "completed"
    assert res["verification_status"] == "passed"
    assert len(res["infra_retry_attempts"]) == 1
    assert res["infra_retry_attempts"][0]["attempt"] == 1
    assert "infra_error" in res["infra_retry_attempts"][0]["exclusion_reasons"]

    check_conn = ledger.get_connection(db_path)
    row = check_conn.execute("SELECT notes FROM runs WHERE id = ?", (res["run_id"],)).fetchone()
    check_conn.close()
    parsed_notes = json.loads(row["notes"])
    assert len(parsed_notes["infra_retry_attempts"]) == 1


def test_verification_failure_never_retries(tmp_path, monkeypatch):
    ev_dir = tmp_path / "evidence"
    monkeypatch.setattr(runner, "DEFAULT_EVIDENCE_DIR", ev_dir)

    db_path = tmp_path / "usage.db"
    conn = ledger.get_connection(db_path)
    ledger.init_db(conn)
    ledger.seed_pricing(WORKSPACE_ROOT / "config" / "PRICING.json", conn=conn)
    conn.close()

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=_ok_result_ndjson(), stderr=b"")

    with (
        mock.patch.object(runner.subprocess, "run", side_effect=fake_run),
        mock.patch.object(runner.ProtectedEvaluator, "evaluate_workspace") as mock_eval,
    ):
        ev_inst = runner.ProtectedEvaluator(WORKSPACE_ROOT / "benchmarks" / "BENCH-005" / "evaluator")
        _, ev_hash = ev_inst.verify_hash()
        mock_eval.return_value = runner.VerificationResult(
            verification_status="failed",
            passed=False,
            reasons=["verification_failed"],
            evaluator_hash=ev_hash,
            output="assertion failed",
        )
        res = runner.run_benchmark_live(
            task_id="BENCH-005",
            arm="icm_v3",
            run_index=2,
            model="gemini-3.8-flash-low",
            db_path=db_path,
            mode="icm-v3",
            max_infra_retries=1,
            infra_retry_backoff_seconds=0.0,
        )

    assert len(calls) == 1
    assert res["execution_status"] == "completed"
    assert res["verification_status"] == "failed"
    assert res["infra_retry_attempts"] == []


def test_double_infra_failure_records_infra_error(tmp_path, monkeypatch):
    ev_dir = tmp_path / "evidence"
    monkeypatch.setattr(runner, "DEFAULT_EVIDENCE_DIR", ev_dir)

    db_path = tmp_path / "usage.db"
    conn = ledger.get_connection(db_path)
    ledger.init_db(conn)
    ledger.seed_pricing(WORKSPACE_ROOT / "config" / "PRICING.json", conn=conn)
    conn.close()

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, stdout=_infra_fail_ndjson(), stderr=b"")

    with mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
        res = runner.run_benchmark_live(
            task_id="BENCH-005",
            arm="icm_v3",
            run_index=2,
            model="gemini-3.8-flash-low",
            db_path=db_path,
            mode="icm-v3",
            max_infra_retries=1,
            infra_retry_backoff_seconds=0.0,
        )

    assert len(calls) == 2
    assert res["execution_status"] == "failed"
    assert "infra_error" in res["exclusion_reasons"]
    assert "execution_failed" in res["exclusion_reasons"]
    assert len(res["infra_retry_attempts"]) == 1


def test_plan_campaign_start_repetition():
    manifest = campaign.plan_campaign(
        tasks=["BENCH-005", "BENCH-006"],
        arms=["icm_v3"],
        repetitions=1,
        random_seed=43,
        model="gemini-3.8-flash-low",
        start_repetition=2,
    )
    assert manifest.verify_integrity() is True
    assert [s.repetition_index for s in manifest.slots] == [2, 2]
