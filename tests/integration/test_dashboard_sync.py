import hashlib
import json
import sqlite3
from pathlib import Path

import build_data
import evaluate_all_quality
import ledger


ROOT = Path(__file__).resolve().parents[2]


def test_fresh_temp_db_has_no_hardcoded_outlines_defects_or_tool_errors(tmp_path: Path):
    """Fresh temporary DB must yield zero hardcoded EXP-009..011 costs, defect_runs, or 11 vs 1 tool errors."""
    db_file = tmp_path / "fresh.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)
    conn.close()

    payload = build_data.build_data_payload(db_path=db_file)
    qr = payload["quality_rubric"]
    assert qr is not None
    assert qr["multi_file_outlines"] == []
    assert qr["tool_errors"] is None

    dumped = json.dumps(payload)
    for forbidden in ("0.2769", "0.358", "0.6814", "0.2981", "90.9"):
        assert forbidden not in dumped

    # Verify build_operational_block never fabricates defect_runs=2 when schema has no defect column
    ops_no_col_db = tmp_path / "ops_no_col.db"
    oconn = sqlite3.connect(str(ops_no_col_db))
    oconn.executescript(
        """
        CREATE TABLE runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            arm TEXT NOT NULL,
            model TEXT NOT NULL,
            run_index INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            num_turns INTEGER NOT NULL,
            duration_seconds REAL NOT NULL
        );
        INSERT INTO runs (task_id, arm, model, run_index, timestamp, num_turns, duration_seconds)
        VALUES ('EXP-005-G1', 'baseline', 'glm-5.3-flash', 1, '2026-09-10T00:00:00Z', 2, 10.0),
               ('EXP-005-G1', 'icm', 'glm-5.3-flash', 1, '2026-09-10T00:01:00Z', 4, 15.0);
        """
    )
    oconn.commit()
    oconn.close()

    ops = build_data.build_operational_block(ops_db_path=ops_no_col_db)
    assert ops["has_data"] is True
    assert ops["summary"]["baseline"]["defect_runs"] is None
    assert ops["summary"]["icm"]["defect_runs"] is None

    headline = build_data.build_headline_block([], {"has_measured_data": False}, operational=ops)
    assert headline is None

    # When verification_status column exists on ops DB, defect_runs is computed dynamically
    ops_with_col_db = tmp_path / "ops_with_col.db"
    oconn2 = sqlite3.connect(str(ops_with_col_db))
    oconn2.executescript(
        """
        CREATE TABLE runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            arm TEXT NOT NULL,
            model TEXT NOT NULL,
            run_index INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            num_turns INTEGER NOT NULL,
            duration_seconds REAL NOT NULL,
            verification_status TEXT NOT NULL
        );
        INSERT INTO runs (task_id, arm, model, run_index, timestamp, num_turns, duration_seconds, verification_status)
        VALUES ('EXP-005-G1', 'baseline', 'glm-5.3-flash', 1, '2026-09-10T00:00:00Z', 2, 10.0, 'failed'),
               ('EXP-005-G1', 'icm', 'glm-5.3-flash', 1, '2026-09-10T00:01:00Z', 4, 15.0, 'passed');
        """
    )
    oconn2.commit()
    oconn2.close()

    ops2 = build_data.build_operational_block(ops_db_path=ops_with_col_db)
    assert ops2["summary"]["baseline"]["defect_runs"] == 1
    assert ops2["summary"]["icm"]["defect_runs"] == 0
    headline2 = build_data.build_headline_block([], {"has_measured_data": False}, operational=ops2)
    assert headline2 is not None
    assert any(s["id"] == "defect_rate" and s["baseline"] == "1/1 defects" and s["icm"] == "0/1 defects" for s in headline2["stats"])


def test_tool_errors_only_from_db_linked_ndjson_and_ignores_orphans(tmp_path: Path):
    """tool_errors must count only DB-linked NDJSON files (deduped by step_index) and ignore orphan NDJSONs."""
    db_file = tmp_path / "linked.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    # Orphan NDJSON not linked to any DB row — must NEVER be read
    orphan = tmp_path / "live_EXP-999_baseline_run1_999.ndjson"
    orphan.write_text(
        "\n".join(
            json.dumps({"event": "step_update", "step_update": {"step_index": i, "step_type": "tool", "state": "ERROR"}})
            for i in range(50)
        )
        + "\n",
        encoding="utf-8",
    )

    base_ev = tmp_path / "base.ndjson"
    base_ev.write_text(
        "\n".join(
            [
                json.dumps({"event": "step_update", "step_update": {"step_index": 1, "step_type": "tool", "state": "RUNNING"}}),
                json.dumps({"event": "step_update", "step_update": {"step_index": 1, "step_type": "tool", "state": "ERROR"}}),
                json.dumps({"event": "step_update", "step_update": {"step_index": 2, "step_type": "tool", "state": "ERROR"}}),
                json.dumps({"event": "step_update", "step_update": {"step_index": 2, "step_type": "tool", "state": "COMPLETED"}}),
                json.dumps({"event": "step_update", "step_update": {"step_index": 3, "step_type": "tool", "state": "ERROR"}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    icm_ev = tmp_path / "icm.ndjson"
    icm_ev.write_text(
        "\n".join(
            [
                json.dumps({"event": "step_update", "step_update": {"step_index": 1, "step_type": "tool", "state": "COMPLETED"}}),
                json.dumps({"event": "step_update", "step_update": {"step_index": 2, "step_type": "tool", "state": "ERROR"}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    ledger.record_run(
        task_id="EXP-001",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-10-01T00:00:00Z",
        input_tokens=1000,
        output_tokens=100,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(base_ev),
        evidence_hash=hashlib.sha256(base_ev.read_bytes()).hexdigest(),
        verification_status="passed",
        conn=conn,
    )
    ledger.record_run(
        task_id="EXP-001",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-10-01T00:01:00Z",
        input_tokens=500,
        output_tokens=50,
        source_kind="live",
        evidence_status="verified",
        evidence_ref=str(icm_ev),
        evidence_hash=hashlib.sha256(icm_ev.read_bytes()).hexdigest(),
        verification_status="passed",
        conn=conn,
    )
    conn.close()

    payload = build_data.build_data_payload(db_path=db_file)
    assert payload["quality_rubric"]["tool_errors"] == {
        "baseline": 2,
        "icm": 1,
        "reduction_percent": 50.0,
    }


def test_tool_errors_reads_tool_errors_count_column_when_present(tmp_path: Path):
    """If runs.tool_errors_count column is populated, use it directly without needing NDJSON on disk."""
    db_file = tmp_path / "col_errors.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(runs)").fetchall()}
    if "tool_errors_count" not in cols:
        conn.execute("ALTER TABLE runs ADD COLUMN tool_errors_count INTEGER")
    conn.execute(
        """
        INSERT INTO runs (task_id, arm, model, run_index, timestamp, input_tokens, output_tokens, num_turns, duration_seconds, tool_errors_count)
        VALUES ('EXP-001', 'baseline', 'gemini-2.5-pro', 1, '2026-10-01T00:00:00Z', 1000, 100, 2, 5.0, 4),
               ('EXP-001', 'icm', 'gemini-2.5-pro', 1, '2026-10-01T00:01:00Z', 500, 50, 1, 3.0, 1)
        """
    )
    conn.commit()
    conn.close()

    payload = build_data.build_data_payload(db_path=db_file)
    assert payload["quality_rubric"]["tool_errors"] == {
        "baseline": 4,
        "icm": 1,
        "reduction_percent": 75.0,
    }


def test_evaluate_all_quality_mappings_and_real_verdicts(tmp_path: Path):
    """Verify EXP-003/EXP-004 swap fix, EXP-006 dedup fix, no out_of_scope fabrication, and real verdicts."""
    db_file = tmp_path / "verdicts.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)
    ledger.record_run(
        task_id="EXP-005",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-10-01T00:00:00Z",
        input_tokens=1000,
        output_tokens=100,
        source_kind="live",
        evidence_status="verified",
        verification_status="failed",
        conn=conn,
    )
    ledger.record_run(
        task_id="EXP-005",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-10-01T00:01:00Z",
        input_tokens=500,
        output_tokens=50,
        source_kind="live",
        evidence_status="verified",
        verification_status="passed",
        conn=conn,
    )
    conn.close()

    res = evaluate_all_quality.evaluate_all(db_path=db_file)
    by_id = {row["task_id"]: row for row in res["tasks"]}

    # EXP-003 is dead_code_finder.py (concise -> maintainability 5); EXP-004 is retry_transport.py (maintainability 1)
    assert by_id["EXP-003"]["governed"]["maintainability"] == 5
    assert by_id["EXP-004"]["governed"]["maintainability"] == 1

    # No synthetic out_of_scope_*.py penalties
    assert by_id["EXP-001"]["baseline"]["process"] == 5
    assert by_id["EXP-003"]["baseline"]["process"] == 5

    # EXP-006 must NOT score sandbox/vanilla/index.html as a duplicate of EXP-005
    if not (ROOT / "sandbox/exp006_vanilla/index.html").is_file():
        assert "EXP-006" not in by_id

    # Real test_passed verdicts: DB verdicts respected for EXP-005; no verdict/test for EXP-008 -> False (correctness=0)
    assert by_id["EXP-005"]["baseline"]["correctness"] == 0
    assert by_id["EXP-005"]["governed"]["correctness"] == 5
    assert by_id["EXP-008"]["baseline"]["correctness"] == 0
    assert by_id["EXP-008"]["governed"]["correctness"] == 0
    assert by_id["EXP-001"]["governed"]["correctness"] == 5


def test_dashboard_tsx_sources_have_no_stale_hardcoded_literals():
    """Overview.tsx and Experiments.tsx must contain zero stale hardcoded benchmark literals."""
    overview_text = (ROOT / "dashboard/src/components/workspace/Overview.tsx").read_text(encoding="utf-8")
    experiments_text = (ROOT / "dashboard/src/components/workspace/Experiments.tsx").read_text(encoding="utf-8")
    combined = overview_text + "\n" + experiments_text

    for stale in (
        "+56.3%",
        "$0.6814",
        "$0.2981",
        "90.9% reduction",
        "+1.00 pt mean gain",
        "+0.29 to +1.71",
        "?? 11",
        "?? 1",
    ):
        assert stale not in combined
