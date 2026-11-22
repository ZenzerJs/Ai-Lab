import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

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


def test_unpriced_live_runs_preserve_token_and_duration_telemetry(tmp_path: Path):
    """Unpriced live runs keep mean_cost_usd=None and has_measured_data=False while reporting real tokens/duration."""
    db_file = tmp_path / "unpriced_bench.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)
    ev_file = tmp_path / "bench_live.ndjson"
    ev_file.write_text('{"event":"init"}\n{"event":"result"}\n', encoding="utf-8")
    import hashlib
    ev_hash = hashlib.sha256(ev_file.read_bytes()).hexdigest()

    for arm, inp, out, dur in [("baseline", 40_000, 5_000, 42.5), ("icm", 32_000, 4_000, 31.0)]:
        ledger.record_run(
            task_id="BENCH-002",
            arm=arm,
            model="unpriced-test-model",
            run_index=1,
            timestamp="2026-11-20T00:00:00Z",
            input_tokens=inp,
            output_tokens=out,
            cache_read_tokens=10_000,
            total_tokens=inp + out,
            num_turns=1,
            duration_seconds=dur,
            source_kind="live",
            evidence_status="verified",
            evidence_ref=str(ev_file),
            evidence_hash=ev_hash,
            execution_status="completed",
            verification_status="passed",
            conn=conn,
        )
    conn.close()

    payload = build_data.build_data_payload(db_path=db_file)
    assert payload["has_data"] is False
    assert len(payload["tasks"]) == 1
    task = payload["tasks"][0]
    assert task["has_measured_data"] is False
    assert task["arms"]["baseline"]["mean_cost_usd"] is None
    assert task["arms"]["baseline"]["mean_input_tokens"] == 40_000.0
    assert task["arms"]["baseline"]["mean_duration_seconds"] == 42.5
    assert task["arms"]["icm"]["mean_input_tokens"] == 32_000.0
    assert task["arms"]["icm"]["mean_duration_seconds"] == 31.0


def test_import_orphan_evidence_runs_idempotent_and_excluded(tmp_path: Path):
    """Importing orphan live_*.ndjson logs archives them without altering measured savings or tool errors."""
    import shutil

    db_file = tmp_path / "orphan_import.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    ev_dir = tmp_path / "evidence"
    ev_dir.mkdir()
    src_active = ROOT / "experiments/evidence/live_EXP-001_baseline_run1_1791060060.ndjson"
    src_icm = ROOT / "experiments/evidence/live_EXP-001_icm_run1_1791060101.ndjson"
    src_orphan = ROOT / "experiments/evidence/live_EXP-001_baseline_run1_1791059906.ndjson"
    for p in (src_active, src_icm, src_orphan):
        shutil.copy2(p, ev_dir / p.name)

    import hashlib
    for arm, p in [("baseline", ev_dir / src_active.name), ("icm", ev_dir / src_icm.name)]:
        parsed = ledger.validate_and_parse_telemetry(p.read_text(encoding="utf-8").splitlines())
        u = parsed["usage"]
        tm = parsed["tool_metrics"]
        ledger.record_run(
            task_id="EXP-001",
            arm=arm,
            model="gemini-3.8-flash-low",
            run_index=1,
            timestamp="2026-10-03T20:41:00+00:00",
            input_tokens=u["input_tokens"],
            output_tokens=u["output_tokens"],
            thinking_tokens=u["thinking_tokens"],
            cache_read_tokens=u["cache_read_tokens"],
            total_tokens=u["total_tokens"],
            num_turns=parsed["num_turns"],
            duration_seconds=parsed["duration_seconds"],
            source_kind="live",
            evidence_status="verified",
            evidence_ref=str(p),
            evidence_hash=hashlib.sha256(p.read_bytes()).hexdigest(),
            execution_status="completed",
            verification_status="passed",
            tool_calls_count=tm["tool_calls_count"],
            tool_errors_count=tm["tool_errors_count"],
            max_consecutive_tool_streak=tm["max_consecutive_tool_streak"],
            loop_detected=tm["loop_detected"],
            conn=conn,
        )

    before_cum = ledger.cumulative_savings(conn=conn)
    before_payload = build_data.build_data_payload(db_path=db_file)

    first = ledger.import_orphan_evidence_runs(evidence_dir=ev_dir, conn=conn)
    second = ledger.import_orphan_evidence_runs(evidence_dir=ev_dir, conn=conn)
    assert first == 1
    assert second == 0

    after_cum = ledger.cumulative_savings(conn=conn)
    after_payload = build_data.build_data_payload(db_path=db_file)

    assert after_cum["total_runs"] == before_cum["total_runs"] == 2
    assert after_cum["scheduled_count"] == 3
    assert after_cum["imported_runs_count"] == 1
    assert after_cum["total_baseline_cost_usd"] == before_cum["total_baseline_cost_usd"]
    assert after_cum["total_icm_cost_usd"] == before_cum["total_icm_cost_usd"]
    assert after_payload["quality_rubric"]["tool_errors"] == before_payload["quality_rubric"]["tool_errors"]
    imported_rows = [r for r in after_payload["runs"] if r["source_kind"] == "imported"]
    assert len(imported_rows) == 1
    assert imported_rows[0]["evidence_status"] == "verified"
    assert imported_rows[0]["is_comparison_eligible"] is False
    conn.close()


def test_iteration_lineage_multi_version_matched_cohort_and_model_isolation(tmp_path: Path, monkeypatch):
    """iteration_lineage groups by (model, version), excludes noise, preserves schema, and computes matched deltas."""
    monkeypatch.setattr(build_data, "OPS_DB_PATH", tmp_path / "missing.db")
    monkeypatch.setattr(evaluate_all_quality, "evaluate_all", lambda **_: {"tasks": [], "quality_ci": {}})

    db_file = tmp_path / "lineage.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    ev_file = tmp_path / "live.ndjson"
    ev_file.write_text('{"event": "init"}\n{"event": "result"}\n', encoding="utf-8")
    ev_hash = hashlib.sha256(ev_file.read_bytes()).hexdigest()

    def _add(
        task_id,
        arm,
        model,
        inp,
        out,
        cache=0,
        run_index=1,
        llm_calls=None,
        tpl=None,
        busts=None,
        cv=None,
        source_kind="live",
        evidence_status="verified",
        is_sim=False,
    ):
        ledger.record_run(
            task_id=task_id,
            arm=arm,
            model=model,
            run_index=run_index,
            timestamp="2026-11-22T12:00:00Z",
            input_tokens=inp,
            output_tokens=out,
            cache_read_tokens=cache,
            source_kind=source_kind,
            evidence_status=evidence_status,
            evidence_ref=str(ev_file) if source_kind == "live" else None,
            evidence_hash=ev_hash if source_kind == "live" else None,
            verification_status="passed",
            llm_calls_count=llm_calls,
            tools_per_llm_call=tpl,
            cache_bust_count=busts,
            contract_version=cv,
            is_simulation=is_sim,
            conn=conn,
        )

    # Model 1: gemini-2.5-pro (separate cache accounting)
    # Baseline runs BENCH-001 (x2), BENCH-002, and extra unmatched BENCH-EXTRA-BASE
    _add("BENCH-001", "baseline", "gemini-2.5-pro", 4000, 1000, cache=0, run_index=1, llm_calls=8, tpl=1.0, busts=2)
    _add("BENCH-001", "baseline", "gemini-2.5-pro", 4000, 1000, cache=0, run_index=2, llm_calls=8, tpl=1.0, busts=2)
    _add("BENCH-002", "baseline", "gemini-2.5-pro", 8000, 2000, cache=0, run_index=1, llm_calls=10, tpl=1.0, busts=1)
    _add("BENCH-EXTRA-BASE", "baseline", "gemini-2.5-pro", 100000, 20000, cache=0, run_index=1, llm_calls=20, tpl=1.0, busts=4)

    # icm (v1)
    _add("BENCH-001", "icm", "gemini-2.5-pro", 3000, 800, cache=1000, llm_calls=6, tpl=1.5, busts=1)
    _add("BENCH-002", "icm", "gemini-2.5-pro", 6000, 1600, cache=2000, llm_calls=6, tpl=1.5, busts=1)

    # icm_v2
    _add("BENCH-001", "icm_v2", "gemini-2.5-pro", 2000, 600, cache=4000, llm_calls=4, tpl=2.5, busts=0, cv="icm_v2")
    _add("BENCH-002", "icm_v2", "gemini-2.5-pro", 4000, 1200, cache=8000, llm_calls=4, tpl=2.5, busts=0, cv="icm_v2")

    # icm_v3 (includes unmatched BENCH-EXTRA-V3 that must not alter matched deltas)
    _add("BENCH-001", "icm_v3", "gemini-2.5-pro", 1200, 500, cache=6000, llm_calls=3, tpl=3.0, busts=0, cv="icm_v3")
    _add("BENCH-002", "icm_v3", "gemini-2.5-pro", 2400, 1000, cache=12000, llm_calls=3, tpl=3.0, busts=0, cv="icm_v3")
    _add("BENCH-EXTRA-V3", "icm_v3", "gemini-2.5-pro", 10, 10, cache=0, llm_calls=1, tpl=1.0, busts=0, cv="icm_v3")

    # icm_staged
    _add("BENCH-001", "icm_staged", "gemini-2.5-pro", 1000, 400, cache=7000, llm_calls=2, tpl=4.0, busts=0, cv="icm_staged")
    _add("BENCH-002", "icm_staged", "gemini-2.5-pro", 2000, 800, cache=14000, llm_calls=2, tpl=4.0, busts=0, cv="icm_staged")

    # Model 2: claude-sonnet-5-5 (subset cache accounting)
    _add("BENCH-001", "baseline", "claude-sonnet-5-5", 1000, 100, cache=200)
    _add("BENCH-001", "icm_v3", "claude-sonnet-5-5", 500, 50, cache=400, cv="icm_v3")

    # Model 3: unpriced-custom-model (must remain unpriced)
    _add("BENCH-001", "icm_v3", "unpriced-custom-model", 500, 50, cache=0, cv="icm_v3")

    # Noise: fixture, imported, simulation, unverified -> must be excluded from iteration_lineage
    _add("BENCH-NOISE", "icm_v3", "gemini-2.5-pro", 999999, 999999, source_kind="fixture", evidence_status="unverified", cv="icm_v3")
    _add("BENCH-NOISE", "icm_v3", "gemini-2.5-pro", 999999, 999999, source_kind="imported", evidence_status="verified", cv="icm_v3")
    _add("BENCH-NOISE", "icm_v3", "gemini-2.5-pro", 999999, 999999, source_kind="live", evidence_status="verified", is_sim=True, cv="icm_v3")
    _add("BENCH-NOISE", "icm_v3", "gemini-2.5-pro", 999999, 999999, source_kind="live", evidence_status="unverified", cv="icm_v3")
    conn.close()

    payload = build_data.build_data_payload(db_path=db_file)

    # Existing top-level schema keys preserved
    for key in (
        "schema_version",
        "generated_at",
        "build_identity",
        "has_data",
        "is_demo_report",
        "is_simulation",
        "headline",
        "declared_benchmarks",
        "cumulative",
        "tasks",
        "runs",
        "timeline",
        "pricing",
        "cascade",
        "operational",
        "quality_rubric",
        "campaign",
        "iteration_lineage",
    ):
        assert key in payload

    lineage = payload["iteration_lineage"]
    assert lineage["has_data"] is True
    assert {c["id"] for c in lineage["contracts"]} >= {"icm_v1", "icm_lite", "icm_v2", "icm_v3", "icm_staged"}

    gem_versions = [v for v in lineage["versions"] if v["model"] == "gemini-2.5-pro"]
    assert [v["version"] for v in gem_versions] == ["baseline", "icm_v1", "icm_v2", "icm_v3", "icm_staged"]
    gem_by_ver = {v["version"]: v for v in gem_versions}

    # BENCH-NOISE excluded everywhere
    for entry in lineage["versions"]:
        assert "BENCH-NOISE" not in entry["task_ids"]

    # Contract metadata populated from registry
    assert gem_by_ver["icm_v3"]["parent_version"] == "icm_v2"
    assert gem_by_ver["icm_v3"]["execution_strategy"] == "single_session"
    assert gem_by_ver["icm_staged"]["parent_version"] == "icm_v3"
    assert gem_by_ver["icm_staged"]["execution_strategy"] == "two_phase_staged"
    assert gem_by_ver["icm_staged"]["hypothesis"]
    assert len(gem_by_ver["icm_staged"]["changes_from_prev"]) > 0

    # Matched-cohort deltas strictly exclude BENCH-EXTRA-BASE and BENCH-EXTRA-V3
    assert gem_by_ver["icm_v3"]["task_ids"] == ["BENCH-001", "BENCH-002", "BENCH-EXTRA-V3"]
    assert gem_by_ver["icm_v3"]["matched_baseline_task_ids"] == ["BENCH-001", "BENCH-002"]

    # Verify exact per-task paired means vs baseline and vs parent_version
    gem_rates = ledger.get_pricing("gemini-2.5-pro", db_path=db_file)

    def _gem_cost(inp, out, cache):
        return round(
            (inp * gem_rates["input_usd_per_mtok"] + cache * gem_rates["cache_read_usd_per_mtok"] + out * gem_rates["output_usd_per_mtok"])
            / 1_000_000.0,
            6,
        )

    base_matched_mean = (_gem_cost(4000, 1000, 0) + _gem_cost(8000, 2000, 0)) / 2.0
    v2_matched_mean = (_gem_cost(2000, 600, 4000) + _gem_cost(4000, 1200, 8000)) / 2.0
    v3_matched_mean = (_gem_cost(1200, 500, 6000) + _gem_cost(2400, 1000, 12000)) / 2.0
    staged_matched_mean = (_gem_cost(1000, 400, 7000) + _gem_cost(2000, 800, 14000)) / 2.0

    expected_v3_vs_base = round((v3_matched_mean - base_matched_mean) / base_matched_mean * 100.0, 2)
    expected_v3_vs_v2 = round((v3_matched_mean - v2_matched_mean) / v2_matched_mean * 100.0, 2)
    expected_staged_vs_v3 = round((staged_matched_mean - v3_matched_mean) / v3_matched_mean * 100.0, 2)

    assert gem_by_ver["baseline"]["cost_delta_vs_baseline_pct"] is None
    assert gem_by_ver["icm_v1"]["cost_delta_vs_prev_version_pct"] is None
    assert gem_by_ver["icm_v3"]["cost_delta_vs_baseline_pct"] == expected_v3_vs_base
    assert gem_by_ver["icm_v3"]["savings_vs_baseline_pct"] == round(-expected_v3_vs_base, 2)
    assert gem_by_ver["icm_v3"]["cost_delta_vs_prev_version_pct"] == expected_v3_vs_v2
    assert gem_by_ver["icm_staged"]["cost_delta_vs_prev_version_pct"] == expected_staged_vs_v3

    # Diagnostics & separate cache accounting
    assert gem_by_ver["icm_v2"]["mean_llm_calls"] == 4.0
    assert gem_by_ver["icm_v2"]["mean_tools_per_call"] == 2.5
    assert gem_by_ver["icm_v2"]["total_cache_busts"] == 0
    assert gem_by_ver["icm_v2"]["mean_cache_hit_ratio"] == pytest.approx(12000 / (6000 + 12000))

    # Model isolation + subset cache accounting (claude-sonnet-5-5)
    claude_v3 = next(v for v in lineage["versions"] if v["model"] == "claude-sonnet-5-5" and v["version"] == "icm_v3")
    assert claude_v3["mean_cache_hit_ratio"] == pytest.approx(400 / 500)
    assert claude_v3["cost_delta_vs_prev_version_pct"] is None  # no claude icm_v2 parent

    # Unpriced model never blended into dollar averages
    unpriced_v3 = next(v for v in lineage["versions"] if v["model"] == "unpriced-custom-model" and v["version"] == "icm_v3")
    assert unpriced_v3["n_runs"] == 1
    assert unpriced_v3["priced_n_runs"] == 0
    assert unpriced_v3["mean_cost_usd"] is None
    assert unpriced_v3["cost_per_passing_patch_usd"] is None
    assert unpriced_v3["cost_delta_vs_baseline_pct"] is None
