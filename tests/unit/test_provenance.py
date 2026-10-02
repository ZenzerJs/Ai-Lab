import hashlib
import json
import sqlite3
from pathlib import Path
import pytest

import ledger


def test_prov_01_fixture_replay_exp008_absent_from_measured(tmp_path: Path):
    """
    PROV-01: Replay fixture telemetry with task ID EXP-008.
    Expected: Classified as fixture; absent from empirical measured totals.
    """
    db_file = tmp_path / "prov01.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    # Record a fixture run with task ID EXP-008 (mimicking dry-run replay)
    ledger.record_run(
        task_id="EXP-008",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=10000,
        output_tokens=1000,
        thinking_tokens=200,
        cache_read_tokens=2000,
        total_tokens=13200,
        num_turns=3,
        duration_seconds=15.0,
        source_kind="fixture",
        evidence_status="unverified",
        exclusion_reasons=["fixture_replay"],
        conn=conn,
    )
    ledger.record_run(
        task_id="EXP-008",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:01:00Z",
        input_tokens=4000,
        output_tokens=800,
        thinking_tokens=150,
        cache_read_tokens=6000,
        total_tokens=10950,
        num_turns=2,
        duration_seconds=8.0,
        source_kind="fixture",
        evidence_status="unverified",
        exclusion_reasons=["fixture_replay"],
        conn=conn,
    )

    # Check task summary
    summary = ledger.task_summary("EXP-008", conn=conn)
    assert summary["total_runs"] == 2
    assert summary["fixture_runs_count"] == 2
    assert summary["measured_runs_count"] == 0
    assert summary["has_measured_data"] is False
    assert summary["savings"] is None

    # Check cumulative savings
    cum = ledger.cumulative_savings(conn=conn)
    assert cum["has_measured_data"] is False
    assert cum["cumulative_savings_usd"] is None
    assert cum["fixture_runs_count"] == 2
    assert cum["total_runs"] == 0

    conn.close()


def test_prov_02_unknown_legacy_run_excluded_from_metrics(tmp_path: Path):
    """
    PROV-02: Insert an unknown legacy run.
    Expected: Visible in historical view; excluded from evidence-qualified metrics.
    """
    db_file = tmp_path / "prov02.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    # Insert a run with source_kind="unknown" (legacy row)
    ledger.record_run(
        task_id="EXP-001",
        arm="baseline",
        model="gemini-3.8-flash",
        run_index=1,
        timestamp="2026-09-01T12:00:00Z",
        input_tokens=40000,
        output_tokens=2000,
        thinking_tokens=0,
        cache_read_tokens=2000,
        total_tokens=44000,
        num_turns=5,
        duration_seconds=20.0,
        source_kind="unknown",
        evidence_status="unverified",
        exclusion_reasons=["legacy_record_unknown_provenance"],
        conn=conn,
    )

    summary = ledger.task_summary("EXP-001", conn=conn)
    assert summary["total_runs"] == 1
    assert summary["historical_runs_count"] == 1
    assert summary["measured_runs_count"] == 0
    assert summary["has_measured_data"] is False
    assert len(summary["excluded_runs"]) == 1
    assert "legacy_unknown_provenance" in summary["excluded_runs"][0]["exclusion_reasons"]

    # Verify cumulative metrics also exclude it
    cum = ledger.cumulative_savings(conn=conn)
    assert cum["has_measured_data"] is False
    assert cum["historical_runs_count"] == 1

    conn.close()


def test_prov_03_import_without_source_evidence_cannot_qualify_as_live(tmp_path: Path):
    """
    PROV-03: Import telemetry without source evidence.
    Expected: Remains imported/unverified; cannot silently qualify as live.
    """
    db_file = tmp_path / "prov03.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    # Attempt to import telemetry claiming to be live without verified evidence
    import_payload = {
        "import_id": "IMP-001",
        "task_id": "TASK-EXT",
        "arm": "baseline",
        "model": "gemini-2.5-pro",
        "run_index": 1,
        "timestamp": "2026-09-10T15:00:00Z",
        "input_tokens": 15000,
        "output_tokens": 1200,
        "thinking_tokens": 300,
        "cache_read_tokens": 0,
        "num_turns": 4,
        "duration_seconds": 18.0,
        "source_kind": "live",  # Claims live, but lacks verified evidence!
        "evidence_ref": None,
        "evidence_status": "unverified",
    }

    run_id = ledger.import_run(conn, import_payload)
    assert run_id > 0

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
    row = dict(cursor.fetchone())

    # Must be demoted to imported with unverified status
    assert row["source_kind"] == "imported"
    assert row["evidence_status"] == "unverified"
    reasons = json.loads(row["exclusion_reasons"])
    assert "unverified_import" in reasons

    # Excluded from measured totals
    summary = ledger.task_summary("TASK-EXT", conn=conn)
    assert summary["measured_runs_count"] == 0
    assert summary["imported_runs_count"] == 1
    assert summary["has_measured_data"] is False

    # Also test an import explicitly attempting to spoof verified live origin without evidence
    spoof_payload = {
        "import_id": "IMP-SPOOF",
        "task_id": "TASK-EXT2",
        "arm": "baseline",
        "model": "gemini-2.5-pro",
        "run_index": 1,
        "input_tokens": 10000,
        "output_tokens": 500,
        "source_kind": "live",
        "evidence_status": "verified",  # Attempt to spoof verified live
        "evidence_ref": None,
    }
    spoof_id = ledger.import_run(conn, spoof_payload)
    cursor.execute("SELECT * FROM runs WHERE id = ?", (spoof_id,))
    spoof_row = dict(cursor.fetchone())
    assert spoof_row["source_kind"] == "imported"
    assert spoof_row["evidence_status"] == "unverified"
    assert "unverified_import" in json.loads(spoof_row["exclusion_reasons"])

    s2 = ledger.task_summary("TASK-EXT2", conn=conn)
    assert s2["has_measured_data"] is False
    assert s2["measured_runs_count"] == 0

    conn.close()


def test_prov_04_mismatching_hash_excludes_metrics_with_reason(tmp_path: Path):
    """
    PROV-04: Validate a referenced artifact with mismatching hash.
    Expected: Evidence invalid; affected metrics excluded with a reason.
    """
    db_file = tmp_path / "prov04.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    artifact_file = tmp_path / "tampered_stream.ndjson"
    artifact_file.write_text('{"event": "turn", "input_tokens": 100}\n', encoding="utf-8")
    actual_hash = hashlib.sha256(artifact_file.read_bytes()).hexdigest()

    fake_expected_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    # Validate directly
    val = ledger.validate_evidence_file(artifact_file, expected_hash=fake_expected_hash)
    assert val["is_valid"] is False
    assert val["status"] == "invalid"
    assert val["exclusion_reason"] == "evidence_hash_mismatch"
    assert val["actual_hash"] == actual_hash

    # Import with this mismatching artifact
    import_payload = {
        "import_id": "IMP-TAMPERED",
        "task_id": "TASK-HASH",
        "arm": "baseline",
        "model": "gemini-2.5-pro",
        "run_index": 1,
        "input_tokens": 5000,
        "output_tokens": 200,
        "evidence_ref": str(artifact_file),
        "evidence_hash": fake_expected_hash,
    }

    run_id = ledger.import_run(conn, import_payload)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
    row = dict(cursor.fetchone())

    assert row["evidence_status"] == "invalid"
    reasons = json.loads(row["exclusion_reasons"])
    assert "evidence_hash_mismatch" in reasons

    summary = ledger.task_summary("TASK-HASH", conn=conn)
    assert summary["measured_runs_count"] == 0
    assert summary["has_measured_data"] is False

    conn.close()


def test_prov_05_missing_or_unreadable_evidence(tmp_path: Path):
    """
    PROV-05: Validate missing or unreadable evidence.
    Expected: No fabricated metadata; explicit unavailable/missing status.
    """
    non_existent = tmp_path / "does_not_exist.ndjson"

    val = ledger.validate_evidence_file(non_existent, expected_hash="abc123")
    assert val["is_valid"] is False
    assert val["status"] == "missing"
    assert val["exclusion_reason"] == "evidence_file_missing"
    assert val["actual_hash"] is None


def test_imp_01_idempotent_duplicate_import(tmp_path: Path):
    """
    IMP-01: Import the same run twice.
    Expected: Idempotent ingestion, returns existing ID without inflating usage.
    """
    db_file = tmp_path / "imp01.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    payload = {
        "import_id": "RUN-UNIQUE-123",
        "task_id": "IDEM-TASK",
        "arm": "baseline",
        "model": "gemini-2.5-pro",
        "run_index": 1,
        "timestamp": "2026-09-10T10:00:00Z",
        "input_tokens": 12000,
        "output_tokens": 800,
        "num_turns": 3,
        "duration_seconds": 14.5,
    }

    id1 = ledger.import_run(conn, payload)
    id2 = ledger.import_run(conn, payload)

    assert id1 == id2

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM runs WHERE import_id = ?", ("RUN-UNIQUE-123",))
    assert cursor.fetchone()[0] == 1

    conn.close()


def test_imp_02_conflicting_import_rejected_with_error(tmp_path: Path):
    """
    IMP-02: Same ID arrives with conflicting content.
    Expected: Explicit conflict error; no silent overwrite.
    """
    db_file = tmp_path / "imp02.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    initial_payload = {
        "import_id": "RUN-CONFLICT-1",
        "task_id": "CONF-TASK",
        "arm": "baseline",
        "model": "gemini-2.5-pro",
        "run_index": 1,
        "input_tokens": 10000,
        "output_tokens": 500,
    }
    id1 = ledger.import_run(conn, initial_payload)

    # Conflicting payload with different input_tokens
    conflicting_payload = {
        "import_id": "RUN-CONFLICT-1",
        "task_id": "CONF-TASK",
        "arm": "baseline",
        "model": "gemini-2.5-pro",
        "run_index": 1,
        "input_tokens": 99999,  # Conflicting!
        "output_tokens": 500,
    }

    with pytest.raises(ledger.DuplicateConflictError, match="Conflicting import"):
        ledger.import_run(conn, conflicting_payload)

    # Ensure original data unchanged
    cursor = conn.cursor()
    cursor.execute("SELECT input_tokens FROM runs WHERE id = ?", (id1,))
    assert cursor.fetchone()[0] == 10000

    conn.close()


def test_imp_01_idempotent_without_import_id_or_timestamp(tmp_path: Path):
    """
    IMP-01 Edge Case: Import the same run twice without explicit import_id or timestamp.
    Expected: Idempotent ingestion uses stable natural key; returns existing run ID without duplicating.
    """
    db_file = tmp_path / "imp_stable.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    payload = {
        "task_id": "STABLE-TASK",
        "arm": "baseline",
        "model": "gemini-2.5-pro",
        "run_index": 1,
        "input_tokens": 15000,
        "output_tokens": 800,
    }

    id1 = ledger.import_run(conn, payload)
    id2 = ledger.import_run(conn, payload)

    assert id1 == id2
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM runs WHERE task_id = 'STABLE-TASK'")
    assert cursor.fetchone()[0] == 1

    conn.close()


def test_imp_02_conflict_on_turns_or_duration(tmp_path: Path):
    """
    IMP-02 Edge Case: Same import ID arrives with conflicting num_turns or duration_seconds.
    Expected: DuplicateConflictError raised; original data intact.
    """
    db_file = tmp_path / "imp_conflict_turns.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    payload1 = {
        "import_id": "IMP-TURN-1",
        "task_id": "TURN-TASK",
        "arm": "baseline",
        "model": "gemini-2.5-pro",
        "run_index": 1,
        "input_tokens": 5000,
        "output_tokens": 200,
        "num_turns": 2,
        "duration_seconds": 10.0,
    }
    id1 = ledger.import_run(conn, payload1)

    payload2 = dict(payload1)
    payload2["num_turns"] = 5  # Conflicting turns

    with pytest.raises(ledger.DuplicateConflictError, match="num_turns"):
        ledger.import_run(conn, payload2)

    payload3 = dict(payload1)
    payload3["duration_seconds"] = 99.5  # Conflicting duration

    with pytest.raises(ledger.DuplicateConflictError, match="duration_seconds"):
        ledger.import_run(conn, payload3)

    conn.close()
