import hashlib
import sqlite3

import pytest

import build_data
import evaluate_all_quality
import ledger
from complexity_router import ICM_LITE, ICM_STAGED, ICM_V2, ICM_V3


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


@pytest.mark.parametrize("gov_arm", [ICM_V3, ICM_STAGED])
def test_v3_and_staged_governed_arm_parity(tmp_path, monkeypatch, gov_arm):
    db = tmp_path / f"{gov_arm}.db"
    evidence = tmp_path / "live.ndjson"
    evidence.write_text('{"event":"start"}\n', encoding="utf-8")
    evidence_hash = hashlib.sha256(evidence.read_bytes()).hexdigest()
    monkeypatch.setattr(build_data, "OPS_DB_PATH", tmp_path / "missing.db")
    monkeypatch.setattr(evaluate_all_quality, "evaluate_all", lambda **_: {"tasks": [], "quality_ci": {}})

    for task in ("EXP-009", "EXP-010"):
        for arm, tokens, errors in (("baseline", 1000, 4), (gov_arm, 400, 1)):
            ledger.record_run(
                task_id=task,
                arm=arm,
                model="gemini-2.5-pro",
                run_index=1,
                timestamp="2026-11-22T12:00:00Z",
                input_tokens=tokens,
                output_tokens=tokens,
                cache_read_tokens=0,
                source_kind="live",
                evidence_status="verified",
                evidence_ref=str(evidence),
                evidence_hash=evidence_hash,
                verification_status="passed",
                tool_errors_count=errors,
                contract_version=gov_arm if arm == gov_arm else None,
                db_path=db,
            )

    summary = ledger.task_summary("EXP-009", db_path=db)
    assert summary["governed_arm"] == gov_arm
    assert summary["savings"]["mean_savings_percent"] == pytest.approx(60.0)

    cum = ledger.cumulative_savings(db_path=db)
    assert cum["cumulative_savings_percent"] == pytest.approx(60.0)

    payload = build_data.build_data_payload(db_path=db)
    assert [point["governed_arm"] for point in payload["timeline"]] == [gov_arm] * 2
    assert payload["quality_rubric"]["tool_errors"] == {"baseline": 8, "icm": 2, "reduction_percent": 75.0}
    assert [row["task_id"] for row in payload["quality_rubric"]["multi_file_outlines"]] == ["EXP-009", "EXP-010"]

    verdicts = evaluate_all_quality._load_db_verdicts(db_path=db)
    assert verdicts[("EXP-009", "governed")] is True
    assert verdicts[("EXP-009", "baseline")] is True


def test_orphan_evidence_supports_v3_and_staged_and_skips_phase_intermediates(tmp_path):
    ev_dir = tmp_path / "evidence"
    ev_dir.mkdir()
    db = tmp_path / "orphan_v3_staged.db"

    # Standalone icm_v3 and icm_staged manifest runs MUST be imported
    (ev_dir / "live_TEST-001_gemini-2.5-pro_icm_v3_run1_1795500001.ndjson").write_text(
        '{"event":"init","init":{"model":"gemini-2.5-pro"}}\n',
        encoding="utf-8",
    )
    (ev_dir / "live_TEST-002_gemini-2.5-pro_icm_staged_run1_1795500002.ndjson").write_text(
        '{"event":"staged_summary","phase1_ref":"p1","phase2_ref":"p2"}\n',
        encoding="utf-8",
    )
    # Phase1 and Phase2 intermediates MUST match regex for phase group but NEVER be imported standalone
    p1_name = "live_TEST-002_gemini-2.5-pro_icm_staged_phase1_run1_1795500002.ndjson"
    p2_name = "live_TEST-002_gemini-2.5-pro_icm_staged_phase2_run1_1795500002.ndjson"
    (ev_dir / p1_name).write_text('{"event":"init","init":{"model":"gemini-2.5-pro"}}\n', encoding="utf-8")
    (ev_dir / p2_name).write_text('{"event":"init","init":{"model":"gemini-2.5-pro"}}\n', encoding="utf-8")

    m1 = ledger._ORPHAN_EVIDENCE_RE.match(p1_name)
    m2 = ledger._ORPHAN_EVIDENCE_RE.match(p2_name)
    assert m1 is not None and m1.group("arm") == ICM_STAGED and m1.group("phase") == "phase1"
    assert m2 is not None and m2.group("arm") == ICM_STAGED and m2.group("phase") == "phase2"

    imported = ledger.import_orphan_evidence_runs(evidence_dir=ev_dir, db_path=db)
    assert imported == 2
    assert ledger.import_orphan_evidence_runs(evidence_dir=ev_dir, db_path=db) == 0

    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT task_id, arm FROM runs ORDER BY task_id").fetchall()
    assert rows == [("TEST-001", ICM_V3), ("TEST-002", ICM_STAGED)]


def test_governed_arms_priority_keeps_legacy_and_v3_staged_consistent():
    assert build_data._governed_key({"baseline": {}, ICM_V2: {}, ICM_LITE: {}}) == ICM_V2
    assert build_data._governed_key({"baseline": {}, ICM_V3: {}, ICM_V2: {}}) == ICM_V3
    assert build_data._governed_key({"baseline": {}, ICM_STAGED: {}, ICM_V2: {}}) == ICM_STAGED
