import json
import sqlite3
from pathlib import Path
import pytest

import ledger


def create_legacy_db(db_path: Path) -> sqlite3.Connection:
    """Create a database with the exact legacy schema (Phase 0)."""
    conn = sqlite3.connect(str(db_path))
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
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                thinking_tokens INTEGER NOT NULL,
                cache_read_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                num_turns INTEGER NOT NULL,
                duration_seconds REAL NOT NULL
            );

            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                prompt_path TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
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
    return conn


def test_mig_01_legacy_migration_preserves_values_and_sets_unknown(tmp_path: Path):
    """
    MIG-01: Migrate a legacy database containing known original values.
    Expected: Values and row counts preserved; unestablished source kind becomes unknown.
    """
    db_file = tmp_path / "legacy.db"
    conn = create_legacy_db(db_file)

    sample_runs = [
        ("TASK-101", "baseline", "gemini-2.5-pro", 1, "2026-09-01T12:00:00Z", 5000, 300, 100, 1000, 6400, 3, 12.5),
        ("TASK-101", "icm", "gemini-2.5-pro", 1, "2026-09-01T12:01:00Z", 2000, 250, 80, 4000, 6330, 2, 8.2),
        ("EXP-001", "baseline", "gemini-3.8-flash", 1, "2026-09-01T12:05:00Z", 8000, 400, 0, 0, 8400, 4, 15.0),
    ]

    with conn:
        for r in sample_runs:
            conn.execute(
                """
                INSERT INTO runs (
                    task_id, arm, model, run_index, timestamp,
                    input_tokens, output_tokens, thinking_tokens, cache_read_tokens,
                    total_tokens, num_turns, duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                r,
            )

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM runs")
    initial_count = cursor.fetchone()[0]
    assert initial_count == len(sample_runs)

    # Apply migration
    applied = ledger.migrate_db(conn)
    assert applied is True

    # Verify columns and data preservation
    cursor.execute("SELECT * FROM runs ORDER BY id ASC")
    migrated_rows = [dict(row) for row in cursor.fetchall()]

    assert len(migrated_rows) == len(sample_runs)

    for i, orig in enumerate(sample_runs):
        row = migrated_rows[i]
        assert row["task_id"] == orig[0]
        assert row["arm"] == orig[1]
        assert row["model"] == orig[2]
        assert row["run_index"] == orig[3]
        assert row["timestamp"] == orig[4]
        assert row["input_tokens"] == orig[5]
        assert row["output_tokens"] == orig[6]
        assert row["thinking_tokens"] == orig[7]
        assert row["cache_read_tokens"] == orig[8]
        assert row["total_tokens"] == orig[9]
        assert row["num_turns"] == orig[10]
        assert abs(row["duration_seconds"] - orig[11]) < 1e-5

        # Provenance classification: unestablished source kind must be unknown
        assert row["source_kind"] == "unknown"
        assert row["evidence_status"] == "unverified"
        assert "legacy_record_unknown_provenance" in json.loads(row["exclusion_reasons"])
        assert row["cost_status"] == "unavailable"

    conn.close()


def test_mig_02_migration_idempotent_no_duplicates(tmp_path: Path):
    """
    MIG-02: Apply the migration twice.
    Expected: Second application makes no destructive or duplicate changes.
    """
    db_file = tmp_path / "idempotent.db"
    conn = create_legacy_db(db_file)

    with conn:
        conn.execute(
            """
            INSERT INTO runs (
                task_id, arm, model, run_index, timestamp,
                input_tokens, output_tokens, thinking_tokens, cache_read_tokens,
                total_tokens, num_turns, duration_seconds
            ) VALUES ('MIG-TASK', 'baseline', 'gemini-2.5-pro', 1, '2026-09-01T10:00:00Z', 100, 10, 0, 0, 110, 1, 2.0)
            """
        )

    # First migration
    first_applied = ledger.migrate_db(conn)
    assert first_applied is True

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs")
    first_run = dict(cursor.fetchone())

    # Second migration
    second_applied = ledger.migrate_db(conn)
    assert second_applied is False  # Already migrated, no-op

    cursor.execute("SELECT * FROM runs")
    all_runs = [dict(r) for r in cursor.fetchall()]
    assert len(all_runs) == 1
    assert all_runs[0] == first_run

    conn.close()


def test_mig_03_migration_failure_rollback(tmp_path: Path):
    """
    MIG-03: Inject a migration failure.
    Expected: Transaction is rolled back, database remains in pre-migration state.
    """
    db_file = tmp_path / "rollback.db"
    conn = create_legacy_db(db_file)

    with conn:
        conn.execute(
            """
            INSERT INTO runs (
                task_id, arm, model, run_index, timestamp,
                input_tokens, output_tokens, thinking_tokens, cache_read_tokens,
                total_tokens, num_turns, duration_seconds
            ) VALUES ('FAIL-TASK', 'baseline', 'gemini-2.5-pro', 1, '2026-09-01T10:00:00Z', 500, 50, 0, 0, 550, 1, 3.5)
            """
        )

    # Use SQLite's native authorizer to simulate an authorization failure when dropping runs
    def authorizer_callback(action, arg1, arg2, db_name, trigger_name):
        # Action 2 is SQLITE_DROP_TABLE
        if action == sqlite3.SQLITE_DROP_TABLE and arg1 == "runs":
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    conn.set_authorizer(authorizer_callback)

    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        ledger.migrate_db(conn)

    # Remove authorizer to verify database state
    conn.set_authorizer(None)

    # Assert database rolled back: original runs table exists with original column structure
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(runs)")
    cols = {row[1] for row in cursor.fetchall()}

    assert "source_kind" not in cols  # Still legacy schema
    cursor.execute("SELECT COUNT(*) FROM runs")
    assert cursor.fetchone()[0] == 1

    cursor.execute("SELECT task_id, total_tokens FROM runs")
    row = cursor.fetchone()
    assert row["task_id"] == "FAIL-TASK"
    assert row["total_tokens"] == 550

    conn.close()

