"""Unit tests for ICM v2 governed arm, AST complexity router fallback, and scope logging."""

import hashlib
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from types import SimpleNamespace

import pytest
import tiktoken

import build_data
import complexity_router
from complexity_router import (
    ICM_LITE,
    ICM_V2,
    ICM_V2_REPO_MAP_MAX_TOKENS,
    MODES,
    SYMBOL_THRESHOLD,
    V2_CONTRACT,
    build_compact_repo_map,
    build_mode_prompt,
    classify_mode,
    count_ast_symbols,
    resolve_mode,
)
import evaluate_all_quality
import ledger
import repo_map
import run_experiment
import runner


# ---------------------------------------------------------------------------
# Audit P1-4: AST symbol count + LOC complexity router fallback
# ---------------------------------------------------------------------------


def test_count_ast_symbols_python_classes_functions_and_async(tmp_path):
    src = tmp_path / "sample.py"
    src.write_text(
        "class Engine:\n"
        "    def start(self):\n"
        "        pass\n"
        "    async def stop(self):\n"
        "        pass\n"
        "\n"
        "def helper():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    assert count_ast_symbols(src) == 4


def test_count_ast_symbols_typescript_and_missing_file(tmp_path):
    ts = tmp_path / "mod.ts"
    ts.write_text(
        "export interface Item { id: string; }\n"
        "export class Store { get() { return 1; } }\n"
        "export function load(): void {}\n",
        encoding="utf-8",
    )
    assert count_ast_symbols(ts) >= 3
    assert count_ast_symbols(tmp_path / "missing.py") is None
    assert count_ast_symbols(None) is None


def test_ast_symbol_threshold_routes_dense_small_file_to_full_icm(tmp_path):
    """A single file <150 LOC with >= SYMBOL_THRESHOLD AST symbols must route to full icm."""
    dense = tmp_path / "dense.py"
    dense.write_text(
        "".join(f"def fn_{i}(x):\n    return x + {i}\n" for i in range(SYMBOL_THRESHOLD)),
        encoding="utf-8",
    )
    assert len(dense.read_text(encoding="utf-8").splitlines()) < complexity_router.LOC_THRESHOLD

    decision = classify_mode("auto", {"target_files": ["dense.py"]}, tmp_path)
    assert decision.loc_source == "file_loc"
    assert decision.ast_symbol_count == SYMBOL_THRESHOLD
    assert decision.arm == "icm"


def test_ast_symbol_fallback_allows_simple_small_file_to_icm_lite(tmp_path):
    simple = tmp_path / "simple.py"
    simple.write_text(
        "".join(f"def fn_{i}(x):\n    return x + {i}\n" for i in range(SYMBOL_THRESHOLD - 1)),
        encoding="utf-8",
    )
    decision = classify_mode("auto", {"target_files": ["simple.py"]}, tmp_path)
    assert decision.loc_source == "file_loc"
    assert decision.ast_symbol_count == SYMBOL_THRESHOLD - 1
    assert decision.arm == ICM_LITE


def test_scope_telemetry_logs_declared_vs_actual_scope(tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "a.py").write_text("def alpha():\n    return 1\n", encoding="utf-8")
    (snapshot / "b.py").write_text("def beta():\n    return 2\n", encoding="utf-8")

    workspace = tmp_path / "workspace"
    shutil.copytree(snapshot, workspace)
    (workspace / "a.py").write_text("def alpha():\n    return 42\n", encoding="utf-8")
    (workspace / "extra.py").write_text("class Extra:\n    pass\n", encoding="utf-8")

    scope = runner.scope_telemetry(
        workspace,
        snapshot,
        {"target_files": ["a.py"], "target_files_count": 1, "estimated_loc": 20},
    )
    assert scope["declared_scope"] == {
        "target_files": ["a.py"],
        "target_files_count": 1,
        "estimated_loc": 20,
        "target_loc_range": None,
    }
    assert scope["actual_scope"]["files_touched"] == ["a.py", "extra.py"]
    assert scope["actual_scope"]["files_touched_count"] == 2
    assert scope["actual_scope"]["lines_touched"] > 0
    assert scope["actual_scope"]["ast_symbols_touched"] == 2
    assert scope["scope_mismatch"] is True


# ---------------------------------------------------------------------------
# ICM v2 contract, deterministic AST repo map prefix, and legacy continuity
# ---------------------------------------------------------------------------


def test_icm_v2_mode_and_legacy_arms_preserved(tmp_path):
    assert "icm-v2" in MODES
    assert set(("auto", "icm", "icm-lite", "icm-v2", "baseline")).issubset(MODES)
    assert resolve_mode("icm-v2", {}, tmp_path) == ICM_V2
    assert resolve_mode("icm-lite", {}, tmp_path) == ICM_LITE
    assert resolve_mode("icm", {}, tmp_path) == "icm"
    assert resolve_mode("baseline", {}, tmp_path) == "baseline"


def test_icm_v2_contract_template_directives():
    text = V2_CONTRACT.read_text(encoding="utf-8")
    assert "Repro -> Surgical Diff -> Verify" in text
    assert "01_intake.md" in text
    assert "05_retro" in text
    assert "Loop-Breaker" in text
    assert "2 consecutive failing" in text
    assert "caller symbol" in text
    assert "1-line" in text
    assert "filter_output.py" not in text
    assert "pytest -q --tb=short" in text
    assert "INSTRUCTIONS.md" in text
    assert "edge-case" in text


def test_compact_repo_map_is_deterministic_and_within_token_budget(tmp_path):
    for i in range(12):
        f = tmp_path / f"mod_{i:02d}.py"
        f.write_text(
            f'"""Module {i} docstring describing service utilities."""\n'
            f"class Service{i}:\n"
            f'    """Service {i} class docstring."""\n'
            f"    def compute_{i}(self, payload: dict, retries: int = 3) -> dict:\n"
            f'        """Compute transformed payload for service {i}."""\n'
            f"        return payload\n"
            f"    def validate_{i}(self, payload: dict) -> bool:\n"
            f"        return bool(payload)\n",
            encoding="utf-8",
        )

    map_a = build_compact_repo_map(tmp_path, max_tokens=ICM_V2_REPO_MAP_MAX_TOKENS)
    map_b = build_compact_repo_map(tmp_path, max_tokens=ICM_V2_REPO_MAP_MAX_TOKENS)
    assert map_a == map_b
    assert "# Repository Map" in map_a
    assert "mod_00.py" in map_a
    assert str(tmp_path) not in map_a  # relative POSIX paths only

    enc = tiktoken.get_encoding(repo_map.ENCODING_NAME)
    assert len(enc.encode(map_a)) <= ICM_V2_REPO_MAP_MAX_TOKENS


def test_build_mode_prompt_icm_v2_injects_static_ast_prefix_before_instructions(tmp_path):
    (tmp_path / "calc.py").write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n",
        encoding="utf-8",
    )
    instructions = "Fix the off-by-one bug in calc.py."

    prompt_1 = build_mode_prompt(instructions, ICM_V2, workspace=tmp_path)
    prompt_2 = build_mode_prompt(instructions, ICM_V2, workspace=tmp_path)

    assert prompt_1 == prompt_2
    assert prompt_1.endswith("\n\n" + instructions)
    assert "## Pre-Injected AST Symbol Map" in prompt_1
    assert "def add(a: int, b: int) -> int:" in prompt_1
    assert prompt_1.index("Loop-Breaker") < prompt_1.index("## Pre-Injected AST Symbol Map")
    assert prompt_1.index("## Pre-Injected AST Symbol Map") < prompt_1.index(instructions)

    # Legacy prompts remain unchanged
    assert build_mode_prompt(instructions, "baseline", workspace=tmp_path) == instructions
    lite_prompt = build_mode_prompt(instructions, ICM_LITE, workspace=tmp_path)
    assert "Single-Stage Contract" in lite_prompt
    assert "## Pre-Injected AST Symbol Map" not in lite_prompt


# ---------------------------------------------------------------------------
# Runner & run_experiment integration with --mode icm-v2
# ---------------------------------------------------------------------------


def test_runner_live_bench_icm_v2_injects_ast_map_and_logs_scope(tmp_path, monkeypatch, capsys):
    evidence_dir = tmp_path / "evidence"
    db = tmp_path / "runs.db"
    monkeypatch.setattr(runner, "DEFAULT_EVIDENCE_DIR", evidence_dir)
    prepare_workspace = runner.WorkspaceManager.prepare_arm_workspace

    def prepare_in_tmp(**kwargs):
        return prepare_workspace(**{**kwargs, "workspace_root": tmp_path / "workspaces"})

    monkeypatch.setattr(runner.WorkspaceManager, "prepare_arm_workspace", prepare_in_tmp)
    monkeypatch.setattr(
        sys,
        "argv",
        ["runner.py", "--live-bench", "BENCH-005", "--db", str(db), "--mode", "icm-v2"],
    )
    captured_prompts = []

    def fake_cli(cmd, **kwargs):
        captured_prompts.append(cmd[cmd.index("-p") + 1])
        cwd = Path(kwargs["cwd"])
        (cwd / "config_loader.py").write_text("# modified\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode=1, stdout=b"", stderr=b"")

    monkeypatch.setattr(runner.subprocess, "run", fake_cli)
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 0

    (prompt,) = captured_prompts
    assert "Repro -> Surgical Diff -> Verify" in prompt
    assert "Loop-Breaker" in prompt
    assert "## Pre-Injected AST Symbol Map" in prompt
    assert "config_loader.py" in prompt

    out = capsys.readouterr().out
    assert "declared_scope=" in out
    assert "actual_scope=" in out

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT arm FROM runs").fetchall() == [(ICM_V2,)]
        scope_row = conn.execute(
            "SELECT status, target_path FROM run_events WHERE phase = 'scope'"
        ).fetchone()
    assert scope_row is not None
    scope_payload = json.loads(scope_row[1])
    assert scope_payload["declared_scope"]["target_files"] == ["config_loader.py"]
    assert scope_payload["actual_scope"]["files_touched"] == ["config_loader.py"]
    assert len(list(evidence_dir.glob("live_BENCH-005_*_icm_v2_run1_*.ndjson"))) == 1


def test_run_experiment_cli_supports_icm_v2(tmp_path, monkeypatch):
    (tmp_path / "widget.py").write_text("def render() -> str:\n    return 'ok'\n", encoding="utf-8")
    task = tmp_path / "task.md"
    task.write_text(
        "---\ntask_id: TEST-V2\ntarget_files: ['widget.py']\n---\nFix widget rendering.",
        encoding="utf-8",
    )
    db = tmp_path / "runs.db"
    monkeypatch.setattr(run_experiment, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(run_experiment.shutil, "which", lambda _: "mock-cli")
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_experiment.py", "--task", str(task), "--runs", "1", "--db", str(db), "--mode", "icm-v2"],
    )
    prompts = []

    def fake_cli(cmd, **kwargs):
        prompts.append(cmd[cmd.index("-p") + 1])
        return SimpleNamespace(stdout=io.BytesIO(), returncode=0, wait=lambda: None)

    monkeypatch.setattr(run_experiment.subprocess, "Popen", fake_cli)
    run_experiment.main()

    assert len(prompts) == 1
    assert "## Pre-Injected AST Symbol Map" in prompts[0]
    assert "def render() -> str:" in prompts[0]
    assert prompts[0].endswith("\n\nFix widget rendering.")
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT arm FROM runs").fetchall() == [(ICM_V2,)]


# ---------------------------------------------------------------------------
# Ledger, dashboard build_data, quality evaluator, and wrapper shims
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["live_TEST-001_icm_v2_run1_123.ndjson", "live_TEST-001_model_icm_v2_run1_123.ndjson"],
)
def test_ledger_imports_orphan_icm_v2_evidence(tmp_path, name):
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / name).write_text(
        '{"event":"init","init":{"model":"gemini-2.5-pro"}}\n',
        encoding="utf-8",
    )
    db = tmp_path / "runs.db"

    assert ledger.import_orphan_evidence_runs(evidence_dir=evidence_dir, db_path=db) == 1
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT arm FROM runs").fetchall() == [(ICM_V2,)]


def test_ledger_and_build_data_accept_icm_v2_as_governed_arm(tmp_path, monkeypatch):
    db = tmp_path / "usage.db"
    evidence = tmp_path / "live.ndjson"
    evidence.write_text('{"event":"start"}\n', encoding="utf-8")
    evidence_hash = hashlib.sha256(evidence.read_bytes()).hexdigest()
    monkeypatch.setattr(build_data, "OPS_DB_PATH", tmp_path / "missing.db")
    monkeypatch.setattr(evaluate_all_quality, "evaluate_all", lambda **_: {"tasks": [], "quality_ci": {}})

    for task in ("BENCH-V2-1", "BENCH-V2-2", "BENCH-V2-3"):
        for arm, tokens, errors in (("baseline", 2000, 6), (ICM_V2, 800, 1)):
            ledger.record_run(
                task_id=task,
                arm=arm,
                model="gemini-2.5-pro",
                run_index=1,
                timestamp="2026-11-22T08:00:00Z",
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

    summary = ledger.task_summary("BENCH-V2-1", db_path=db)
    assert summary["governed_arm"] == ICM_V2
    assert summary["savings"]["mean_savings_percent"] == pytest.approx(60.0)

    cum = ledger.cumulative_savings(db_path=db)
    assert cum["cumulative_savings_percent"] == pytest.approx(60.0)

    payload = build_data.build_data_payload(db_path=db)
    assert [point["governed_arm"] for point in payload["timeline"]] == [ICM_V2] * 3
    assert payload["quality_rubric"]["tool_errors"] == {
        "baseline": 18,
        "icm": 3,
        "reduction_percent": 83.3,
    }

    verdicts = evaluate_all_quality._load_db_verdicts(db_path=db)
    assert verdicts[("BENCH-V2-1", "governed")] is True
    assert verdicts[("BENCH-V2-1", "baseline")] is True


def test_operational_summary_counts_icm_v2_as_governed(tmp_path):
    db = tmp_path / "ops.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE runs (task_id, arm, run_index, num_turns, duration_seconds, timestamp, verification_status);
            INSERT INTO runs VALUES
                ('EXP-005', 'baseline', 1, 4, 12.0, '2026-11-22T08:00:00Z', 'passed'),
                ('EXP-005', 'icm_v2', 1, 2, 4.5, '2026-11-22T08:00:00Z', 'passed');
            """
        )

    operational = build_data.build_operational_block(ops_db_path=db)
    assert operational["runs"][1]["arm"] == ICM_V2
    assert operational["tasks"][0]["icm"] == {"n": 1, "mean_turns": 2.0, "mean_duration_seconds": 4.5}
    assert operational["summary"]["icm"] == {
        "runs": 1,
        "total_turns": 2,
        "total_duration_seconds": 4.5,
        "defect_runs": 0,
    }


def test_build_data_shims_are_minimal_wrappers():
    dashboard_dir = Path(build_data.__file__).resolve().parent
    ps1 = (dashboard_dir / "build_data.ps1").read_text(encoding="utf-8").splitlines()
    sh = (dashboard_dir / "build_data.sh").read_text(encoding="utf-8").splitlines()
    assert len(ps1) <= 5
    assert len(sh) <= 5
    assert any("build_data.py" in line for line in ps1)
    assert any("build_data.py" in line for line in sh)


def test_ts_export_wrappers_do_not_double_count_ast_symbols(tmp_path):
    ts = tmp_path / "exports.ts"
    ts.write_text(
        "".join(f"export function fn{i}(): number {{ return {i}; }}\n" for i in range(5)),
        encoding="utf-8",
    )
    assert count_ast_symbols(ts) == 5
    decision = classify_mode("auto", {"target_files": ["exports.ts"]}, tmp_path)
    assert decision.arm == ICM_LITE


def test_scope_telemetry_counts_only_diff_touched_ast_symbols(tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "mod.py").write_text(
        "# header\n"
        "def keep_a():\n    return 1\n\n"
        "def keep_b():\n    return 2\n\n"
        "def removed_fn():\n    return 3\n",
        encoding="utf-8",
    )
    workspace = tmp_path / "workspace"
    shutil.copytree(snapshot, workspace)

    # Comment-only edit outside any symbol -> 0 touched symbols
    (workspace / "mod.py").write_text(
        "# updated header\n"
        "def keep_a():\n    return 1\n\n"
        "def keep_b():\n    return 2\n\n"
        "def removed_fn():\n    return 3\n",
        encoding="utf-8",
    )
    scope_comment = runner.scope_telemetry(workspace, snapshot, {"target_files": ["mod.py"]})
    assert scope_comment["actual_scope"]["ast_symbols_touched"] == 0

    # Delete removed_fn without touching keep_a or keep_b -> 1 touched symbol
    (workspace / "mod.py").write_text(
        "# header\n"
        "def keep_a():\n    return 1\n\n"
        "def keep_b():\n    return 2\n",
        encoding="utf-8",
    )
    scope_delete = runner.scope_telemetry(workspace, snapshot, {"target_files": ["mod.py"]})
    assert scope_delete["actual_scope"]["ast_symbols_touched"] == 1


def test_governed_arms_priority_matches_ledger_for_icm_v2_and_icm_lite():
    arms = {"baseline": {}, ICM_LITE: {}, ICM_V2: {}}
    assert build_data._governed_key(arms) == ICM_V2


def test_exported_arrow_functions_trigger_complexity_escalation(tmp_path):
    ts = tmp_path / "arrows.ts"
    ts.write_text(
        "".join(f"export const fn{i} = (x: number): number => x + {i};\n" for i in range(10)),
        encoding="utf-8",
    )
    assert count_ast_symbols(ts) == 10
    decision = classify_mode("auto", {"target_files": ["arrows.ts"]}, tmp_path)
    assert decision.arm == "icm"


def test_scope_telemetry_counts_decorator_and_typescript_body_edits(tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "dec.py").write_text(
        "def dec(f):\n    return f\n\n"
        "@dec\n"
        "def target():\n    return 1\n",
        encoding="utf-8",
    )
    (snapshot / "mod.ts").write_text(
        "export function alpha(): number {\n  return 1;\n}\n\n"
        "export function beta(): number {\n  return 2;\n}\n",
        encoding="utf-8",
    )
    workspace = tmp_path / "workspace"
    shutil.copytree(snapshot, workspace)

    # Decorator-only edit on target() -> 1 touched symbol
    (workspace / "dec.py").write_text(
        "def dec(f):\n    return f\n\n"
        "@dec  # updated\n"
        "def target():\n    return 1\n",
        encoding="utf-8",
    )
    # Body-only edit inside TypeScript alpha() -> 1 touched symbol
    (workspace / "mod.ts").write_text(
        "export function alpha(): number {\n  return 42;\n}\n\n"
        "export function beta(): number {\n  return 2;\n}\n",
        encoding="utf-8",
    )
    scope = runner.scope_telemetry(workspace, snapshot, {"target_files": ["dec.py", "mod.ts"]})
    assert scope["actual_scope"]["ast_symbols_touched"] == 2


