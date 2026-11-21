import hashlib
import sqlite3

import build_data
import evaluate_all_quality
import ledger


def test_payload_uses_lite_as_governed_arm(tmp_path, monkeypatch):
    db = tmp_path / "usage.db"
    evidence = tmp_path / "live.ndjson"
    evidence.write_text('{"event":"start"}\n', encoding="utf-8")
    evidence_hash = hashlib.sha256(evidence.read_bytes()).hexdigest()
    monkeypatch.setattr(build_data, "OPS_DB_PATH", tmp_path / "missing.db")
    monkeypatch.setattr(evaluate_all_quality, "evaluate_all", lambda **_: {"tasks": [], "quality_ci": {}})

    for task in ("EXP-009", "EXP-010", "EXP-011"):
        for arm, tokens, errors in (("baseline", 1000, 4), ("icm_lite", 500, 1)):
            ledger.record_run(
                task_id=task,
                arm=arm,
                model="gemini-2.5-pro",
                run_index=1,
                timestamp="2026-09-10T12:00:00Z",
                input_tokens=tokens,
                output_tokens=tokens,
                cache_read_tokens=0,
                source_kind="live",
                evidence_status="verified",
                evidence_ref=str(evidence),
                evidence_hash=evidence_hash,
                verification_status="passed",
                tool_errors_count=errors,
                db_path=db,
            )

    payload = build_data.build_data_payload(db_path=db)
    assert [point["governed_arm"] for point in payload["timeline"]] == ["icm_lite"] * 3

    quality = payload["quality_rubric"]
    assert quality["tool_errors"] == {"baseline": 12, "icm": 3, "reduction_percent": 75.0}
    assert [row["task_id"] for row in quality["multi_file_outlines"]] == ["EXP-009", "EXP-010", "EXP-011"]
    assert all(row["raw_savings_percent"] == 50.0 for row in quality["multi_file_outlines"])

    stats = {stat["id"]: stat for stat in payload["headline"]["stats"]}
    assert stats["cost_reduction"]["ci95"] == [50.0, 50.0]
    assert stats["cost_reduction"]["n_icm"] == 3
    assert stats["cache_efficiency"]["n_icm"] == 3
    assert stats["tokens_per_pass"]["value"] == 50.0
    assert stats["tokens_per_pass"]["n_icm"] == 3


def test_operational_summary_counts_lite_runs_and_defects(tmp_path):
    db = tmp_path / "ops.db"
    with sqlite3.connect(db) as conn:
        conn.executescript("""
            CREATE TABLE runs (task_id, arm, run_index, num_turns, duration_seconds, timestamp, verification_status);
            INSERT INTO runs VALUES
                ('EXP-005', 'baseline', 1, 3, 9.0, '2026-09-10T12:00:00Z', 'passed'),
                ('EXP-005', 'icm_lite', 1, 1, 5.0, '2026-09-10T12:00:00Z', 'failed');
        """)

    operational = build_data.build_operational_block(ops_db_path=db)
    assert operational["runs"][1]["arm"] == "icm_lite"
    assert operational["tasks"][0]["icm"] == {"n": 1, "mean_turns": 1.0, "mean_duration_seconds": 5.0}
    assert operational["summary"]["icm"] == {
        "runs": 1, "total_turns": 1, "total_duration_seconds": 5.0, "defect_runs": 1,
    }
