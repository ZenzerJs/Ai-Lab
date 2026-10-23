import tempfile
import sqlite3
from pathlib import Path
import pytest
from scripts.run_experiment import execute_verification, get_next_run_index, parse_task_file
import scripts.ledger as ledger

def test_execute_verification_success():
    """Verify that a passing command returns 'passed'."""
    cmd = "python -c \"import sys; sys.exit(0)\""
    res = execute_verification(cmd, Path("."))
    assert res == "passed"

def test_execute_verification_failure():
    """Verify that a failing command returns 'failed'."""
    cmd = "python -c \"import sys; sys.exit(1)\""
    res = execute_verification(cmd, Path("."))
    assert res == "failed"

def test_execute_verification_not_run():
    """Verify that an empty command returns 'not_run'."""
    res = execute_verification(None, Path("."))
    assert res == "not_run"
    res2 = execute_verification("", Path("."))
    assert res2 == "not_run"

def test_get_next_run_index():
    """Verify get_next_run_index increments sequentially without overwriting."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    try:
        conn = ledger.get_connection(db_path=db_path)
        ledger.init_db(conn)
        conn.close()

        # Initially index is 1
        idx1 = get_next_run_index("TEST-001", "baseline", db_path=db_path)
        assert idx1 == 1

        # Record a run
        from datetime import datetime, timezone
        ledger.record_run(
            task_id="TEST-001",
            arm="baseline",
            model="gemini-3.8-flash-low",
            run_index=1,
            timestamp=datetime.now(timezone.utc).isoformat(),
            input_tokens=100,
            output_tokens=50,
            db_path=db_path,
        )

        # Next run index should be 2
        idx2 = get_next_run_index("TEST-001", "baseline", db_path=db_path)
        assert idx2 == 2
    finally:
        if db_path.exists():
            db_path.unlink()
