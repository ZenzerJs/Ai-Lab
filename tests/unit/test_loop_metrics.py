import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

import ledger

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE_EXP006_NDJSON = (
    REPO_ROOT / "experiments" / "evidence" / "live_EXP-006_baseline_run1_1791066412.ndjson"
)
ICM_EXP006_NDJSON = (
    REPO_ROOT / "experiments" / "evidence" / "live_EXP-006_icm_run1_1791066551.ndjson"
)


def test_extract_ndjson_tool_metrics_synthetic_dedup_and_thresholds(tmp_path: Path):
    """Verify step_index deduplication, consecutive streaks, error thresholds, and Path/str/list inputs."""
    lines = [
        json.dumps({"event": "init", "init": {"model": "gemini-4-hydrogen-low"}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 0, "state": "DONE", "step_type": "user_input"}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 1, "state": "ACTIVE", "step_type": "tool", "tool_name": "view_file", "tool_info": {"parameters": {"AbsolutePath": "a.py"}}}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 1, "state": "DONE", "step_type": "tool", "tool_name": "view_file", "tool_info": {"parameters": {"AbsolutePath": "a.py"}}}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 2, "state": "ACTIVE", "step_type": "tool", "tool_name": "view_file", "tool_info": {"parameters": {"AbsolutePath": "b.py"}}}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 2, "state": "ERROR", "step_type": "tool", "tool_name": "view_file", "tool_info": {"parameters": {"AbsolutePath": "b.py"}}}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 3, "state": "DONE", "step_type": "tool", "tool_name": "view_file", "tool_info": {"parameters": {"AbsolutePath": "c.py"}}}}),
        json.dumps({"event": "step_update", "step_update": {"step_index": 4, "state": "DONE", "step_type": "tool", "tool_name": "write_to_file", "tool_info": {"parameters": {"TargetFile": "d.py"}}}}),
        json.dumps({"event": "result", "result": {"duration_seconds": 4.2, "num_turns": 1, "usage": {"input_tokens": 100, "output_tokens": 20, "thinking_tokens": 0, "cache_read_tokens": 0, "total_tokens": 120}}}),
    ]
    ndjson_file = tmp_path / "synthetic.ndjson"
    ndjson_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Test list, str, and Path inputs
    m_list = ledger.extract_ndjson_tool_metrics(lines)
    m_str = ledger.extract_ndjson_tool_metrics("\n".join(lines))
    m_path = ledger.extract_ndjson_tool_metrics(ndjson_file)
    assert m_list == m_str == m_path

    # Deduped: 4 unique tool steps (step_index 1..4), 1 ERROR, max streak 3 (view_file x3)
    assert m_list["tool_calls_count"] == 4
    assert m_list["tool_errors_count"] == 1
    assert m_list["max_consecutive_tool_streak"] == 3
    assert m_list["loop_detected"] is False  # Below default thresholds (6 streak, 3 errors)
    assert len(m_list["events"]) == 4
    assert m_list["events"][0] == {
        "seq": 1,
        "phase": "tool",
        "tool_name": "view_file",
        "target_path": "a.py",
        "status": "DONE",
    }
    assert m_list["events"][1]["status"] == "ERROR"
    assert m_list["events"][3]["target_path"] == "d.py"

    # Trigger loop via custom streak_threshold or error_threshold
    m_streak_loop = ledger.extract_ndjson_tool_metrics(lines, streak_threshold=3, error_threshold=5)
    assert m_streak_loop["loop_detected"] is True
    m_err_loop = ledger.extract_ndjson_tool_metrics(lines, streak_threshold=10, error_threshold=1)
    assert m_err_loop["loop_detected"] is True

    # validate_and_parse_telemetry exposes tool_metrics cleanly
    parsed = ledger.validate_and_parse_telemetry(lines)
    assert parsed["usage"]["input_tokens"] == 100
    assert parsed["model"] == "gemini-4-hydrogen-low"
    assert parsed["tool_metrics"] == m_list


def test_extract_ndjson_tool_metrics_real_exp006_streams():
    """Verify exact counts on real EXP-006 baseline and icm NDJSON evidence files."""
    assert BASELINE_EXP006_NDJSON.is_file()
    assert ICM_EXP006_NDJSON.is_file()

    base_metrics = ledger.extract_ndjson_tool_metrics(BASELINE_EXP006_NDJSON)
    assert base_metrics["tool_calls_count"] == 61
    assert base_metrics["tool_errors_count"] == 3
    assert base_metrics["max_consecutive_tool_streak"] == 7
    assert base_metrics["loop_detected"] is True
    assert len(base_metrics["events"]) == 61

    icm_metrics = ledger.extract_ndjson_tool_metrics(ICM_EXP006_NDJSON)
    assert icm_metrics["tool_calls_count"] == 25
    assert icm_metrics["tool_errors_count"] == 0
    assert len(icm_metrics["events"]) == 25


def test_cost_and_tokens_per_passing_patch_with_failed_and_zero_passing(tmp_path: Path):
    """Verify cost_per_passing_patch_usd & tokens_per_passing_patch include failed runs and return None on 0 passes."""
    db_file = tmp_path / "loop_cost.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    ev_file = tmp_path / "ev.ndjson"
    ev_file.write_text('{"event": "start"}\n', encoding="utf-8")
    ev_hash = hashlib.sha256(ev_file.read_bytes()).hexdigest()

    # Baseline on TASK-PATCH: 1 failed run ($0.40, 100k tokens) + 1 passing run ($0.60, 200k tokens)
    # Explicit cost_usd used so assertions are exact and deterministic.
    ledger.record_run(
        task_id="TASK-PATCH",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-11-20T00:00:00Z",
        input_tokens=80_000,
        output_tokens=20_000,
        total_tokens=100_000,
        cost_usd=0.40,
        cost_status="usage_estimate",
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        verification_status="failed",
        tool_calls_count=40,
        tool_errors_count=3,
        max_consecutive_tool_streak=7,
        loop_detected=True,
        conn=conn,
    )
    ledger.record_run(
        task_id="TASK-PATCH",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=2,
        timestamp="2026-11-20T00:01:00Z",
        input_tokens=160_000,
        output_tokens=40_000,
        total_tokens=200_000,
        cost_usd=0.60,
        cost_status="usage_estimate",
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        verification_status="passed",
        tool_calls_count=20,
        tool_errors_count=0,
        max_consecutive_tool_streak=3,
        loop_detected=False,
        conn=conn,
    )

    # ICM on TASK-PATCH: 2 failed runs (0 passing runs -> None for cost/tokens per passing patch)
    ledger.record_run(
        task_id="TASK-PATCH",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-11-20T00:02:00Z",
        input_tokens=40_000,
        output_tokens=10_000,
        total_tokens=50_000,
        cost_usd=0.20,
        cost_status="usage_estimate",
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        verification_status="failed",
        tool_calls_count=15,
        tool_errors_count=1,
        max_consecutive_tool_streak=2,
        loop_detected=False,
        conn=conn,
    )

    summary = ledger.task_summary("TASK-PATCH", conn=conn)
    b = summary["arms"]["baseline"]
    assert b["passed_count"] == 1
    assert b["pass_rate"] == pytest.approx(0.5)
    assert b["cost_per_passing_patch_usd"] == pytest.approx(1.00)  # (0.40 + 0.60) / 1
    assert b["tokens_per_passing_patch"] == pytest.approx(300_000.0)  # (100k + 200k) / 1
    assert b["total_tool_calls"] == 60
    assert b["total_tool_errors"] == 3
    assert b["loop_runs_count"] == 1

    i = summary["arms"]["icm"]
    assert i["passed_count"] == 0
    assert i["pass_rate"] == pytest.approx(0.0)
    assert i["cost_per_passing_patch_usd"] is None
    assert i["tokens_per_passing_patch"] is None
    assert i["total_tool_calls"] == 15
    assert i["total_tool_errors"] == 1
    assert i["loop_runs_count"] == 0

    cum = ledger.cumulative_savings(conn=conn)
    assert cum["arms"]["baseline"]["cost_per_passing_patch_usd"] == pytest.approx(1.00)
    assert cum["arms"]["baseline"]["tokens_per_passing_patch"] == pytest.approx(300_000.0)
    assert cum["arms"]["baseline"]["total_tool_errors"] == 3
    assert cum["arms"]["baseline"]["loop_runs_count"] == 1
    assert cum["arms"]["icm"]["cost_per_passing_patch_usd"] is None
    assert cum["arms"]["icm"]["tokens_per_passing_patch"] is None
    assert cum["arms"]["icm"]["total_tool_errors"] == 1
    assert cum["arms"]["icm"]["loop_runs_count"] == 0

    # Failed averages across the 2 failed runs: (80k + 40k)/2, (20k + 10k)/2, (0.40 + 0.20)/2
    assert cum["failed_avg_input_tokens"] == pytest.approx(60_000.0)
    assert cum["failed_avg_output_tokens"] == pytest.approx(15_000.0)
    assert cum["failed_avg_cost_usd"] == pytest.approx(0.30)

    conn.close()


def test_cumulative_savings_zero_failed_runs_averages_none(tmp_path: Path):
    """Verify failed_avg_* fields are None when there are zero failed runs."""
    db_file = tmp_path / "no_fails.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    ev_file = tmp_path / "ev.ndjson"
    ev_file.write_text('{"event": "start"}\n', encoding="utf-8")
    ev_hash = hashlib.sha256(ev_file.read_bytes()).hexdigest()

    ledger.record_run(
        task_id="TASK-PASS",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-11-20T00:00:00Z",
        input_tokens=10_000,
        output_tokens=1_000,
        total_tokens=11_000,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ev_file),
        evidence_hash=ev_hash,
        verification_status="passed",
        conn=conn,
    )

    cum = ledger.cumulative_savings(conn=conn)
    assert cum["failed_avg_input_tokens"] is None
    assert cum["failed_avg_output_tokens"] is None
    assert cum["failed_avg_cost_usd"] is None
    conn.close()


def test_backfill_tool_metrics_from_evidence_idempotent(tmp_path: Path):
    """Verify backfill_tool_metrics_from_evidence populates NULL rows once and is idempotent."""
    db_file = tmp_path / "backfill.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    # 1. Baseline EXP-006 row with NULL tool metrics and existing evidence_ref
    rid1 = ledger.record_run(
        task_id="EXP-006",
        arm="baseline",
        model="gemini-3.8-flash-low",
        run_index=1,
        timestamp="2026-11-20T00:00:00Z",
        input_tokens=297398,
        output_tokens=7408,
        source_kind="live",
        evidence_status="verified",
        evidence_ref="experiments/evidence/live_EXP-006_baseline_run1_1791066412.ndjson",
        evidence_hash=hashlib.sha256(BASELINE_EXP006_NDJSON.read_bytes()).hexdigest(),
        verification_status="passed",
        conn=conn,
    )
    # 2. ICM EXP-006 row with NULL tool metrics
    rid2 = ledger.record_run(
        task_id="EXP-006",
        arm="icm",
        model="gemini-3.8-flash-low",
        run_index=1,
        timestamp="2026-11-20T00:01:00Z",
        input_tokens=159977,
        output_tokens=3686,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(ICM_EXP006_NDJSON),
        evidence_hash=hashlib.sha256(ICM_EXP006_NDJSON.read_bytes()).hexdigest(),
        verification_status="passed",
        conn=conn,
    )
    # 3. Row with missing evidence file (should be skipped)
    rid3 = ledger.record_run(
        task_id="EXP-MISSING",
        arm="baseline",
        model="gemini-3.8-flash-low",
        run_index=1,
        timestamp="2026-11-20T00:02:00Z",
        input_tokens=100,
        output_tokens=10,
        source_kind="live",
        evidence_status="missing",
        evidence_ref=str(tmp_path / "does_not_exist.ndjson"),
        conn=conn,
    )

    first_updated = ledger.backfill_tool_metrics_from_evidence(conn=conn)
    assert first_updated == 2

    row1 = dict(conn.execute("SELECT * FROM runs WHERE id = ?", (rid1,)).fetchone())
    assert row1["tool_calls_count"] == 61
    assert row1["tool_errors_count"] == 3
    assert row1["max_consecutive_tool_streak"] == 7
    assert row1["loop_detected"] == 1

    row2 = dict(conn.execute("SELECT * FROM runs WHERE id = ?", (rid2,)).fetchone())
    assert row2["tool_calls_count"] == 25
    assert row2["tool_errors_count"] == 0

    row3 = dict(conn.execute("SELECT * FROM runs WHERE id = ?", (rid3,)).fetchone())
    assert row3["tool_calls_count"] is None

    # Second call must be a no-op (0 rows updated)
    second_updated = ledger.backfill_tool_metrics_from_evidence(conn=conn)
    assert second_updated == 0
    conn.close()


def test_migrate_db_phase2_upgrade_idempotency(tmp_path: Path):
    """Verify migrate_db returns True when adding new columns/run_events to Phase 2 DB and False on re-run."""
    db_file = tmp_path / "phase2_upgrade.db"
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
                notes TEXT,
                execution_status TEXT NOT NULL DEFAULT 'completed',
                verification_status TEXT NOT NULL DEFAULT 'not_run',
                manifest_id TEXT,
                evaluator_hash TEXT
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

    assert ledger.migrate_db(conn) is True
    assert ledger.migrate_db(conn) is False

    cols = {r[1] for r in conn.execute("PRAGMA table_info(runs)").fetchall()}
    assert {"tool_calls_count", "tool_errors_count", "max_consecutive_tool_streak", "loop_detected"}.issubset(cols)
    assert conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='run_events'").fetchone() is not None
    conn.close()
