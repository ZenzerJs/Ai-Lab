import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from types import SimpleNamespace

import pytest

import ledger
import run_experiment
import runner
from complexity_router import RoutingDecision, classify_mode, resolve_mode


@pytest.mark.parametrize(
    ("metadata", "arm"),
    [
        ({"target_files": ["new.py"], "estimated_loc": 149}, "icm_lite"),
        ({"target_files": ["new.py"], "estimated_loc": 150}, "icm"),
        ({"target_files": ["new.py", "test_new.py"], "estimated_loc": 15}, "icm"),
        ({"target_files": ["new.py", "./new.py"], "estimated_loc": 15}, "icm_lite"),
        ({"target_files_count": 1, "target_loc_range": "120-149"}, "icm_lite"),
        ({"target_files_count": 1, "target_loc_range": "120-150"}, "icm"),
        ({"target_files_count": 2, "target_files": ["new.py"], "estimated_loc": 15}, "icm"),
        ({"target_files": ["new.py"]}, "icm"),
        ({"target_files": [], "estimated_loc": 15}, "icm"),
        ({"target_files": ["../outside.py"], "estimated_loc": 15}, "icm"),
        ({"target_files": ["new.py"], "estimated_loc": "15"}, "icm"),
        ({"estimated_loc": 15}, "icm"),
        ({}, "icm"),
    ],
)
def test_auto_uses_declared_target_footprint_and_estimate(tmp_path, metadata, arm):
    assert resolve_mode("auto", metadata, tmp_path) == arm


@pytest.mark.parametrize(
    ("metadata", "arm", "loc_source", "loc"),
    [
        ({"target_files": ["new.py"], "estimated_loc": 149}, "icm_lite", "estimated_loc", 149),
        ({"target_files": ["new.py"], "estimated_loc": 150}, "icm", "estimated_loc", 150),
        ({"target_files_count": 1, "target_loc_range": "120-149"}, "icm_lite", "target_loc_range", 149),
        ({"target_files_count": 1, "target_loc_range": "120-150"}, "icm", "target_loc_range", 150),
        ({"target_files": ["new.py"]}, "icm", "unknown", None),
        ({}, "icm", "unknown", None),
    ],
)
def test_classify_mode_reports_loc_source(tmp_path, metadata, arm, loc_source, loc):
    decision = classify_mode("auto", metadata, tmp_path)
    assert isinstance(decision, RoutingDecision)
    assert decision.arm == arm
    assert decision.loc_source == loc_source
    assert decision.loc == loc
    assert decision.arm == resolve_mode("auto", metadata, tmp_path)


def test_classify_mode_uses_file_loc_for_single_existing_file(tmp_path):
    (tmp_path / "target.py").write_text("pass\n" * 149, encoding="utf-8")
    decision = classify_mode("auto", {"target_files": ["target.py"]}, tmp_path)
    assert decision.arm == "icm_lite"
    assert decision.loc_source == "file_loc"
    assert decision.loc == 149
    assert decision.single_file is True
    assert decision.target == "target.py"


@pytest.mark.parametrize(
    "mode, arm",
    [("icm-lite", "icm_lite"), ("icm", "icm"), ("baseline", "baseline")],
)
def test_classify_mode_explicit_modes_skip_scope_evidence(tmp_path, mode, arm):
    decision = classify_mode(mode, {"target_files": ["x.py"], "estimated_loc": 1}, tmp_path)
    assert decision.arm == arm
    assert decision.loc_source == "unknown"
    assert decision.loc is None


def test_classify_mode_rejects_unknown_mode(tmp_path):
    with pytest.raises(ValueError):
        classify_mode("wat", {}, tmp_path)


@pytest.mark.parametrize(
    "metadata",
    [
        {"estimated_loc": "15"},
        {"estimated_loc": -1},
        {"estimated_loc": 12.5},
        {"estimated_loc": True},
    ],
)
def test_malformed_estimated_loc_warns_and_falls_through(tmp_path, metadata):
    with pytest.warns(UserWarning, match="estimated_loc"):
        decision = classify_mode("auto", {"target_files": ["new.py"], **metadata}, tmp_path)
    assert decision.loc_source == "unknown"
    assert decision.arm == "icm"


@pytest.mark.parametrize(
    "loc_range",
    ["abc", "150-120", "120-", "-150", "120-150-200", ""],
)
def test_malformed_target_loc_range_warns_and_falls_through(tmp_path, loc_range):
    with pytest.warns(UserWarning, match="target_loc_range"):
        decision = classify_mode("auto", {"target_files_count": 1, "target_loc_range": loc_range}, tmp_path)
    assert decision.loc_source == "unknown"
    assert decision.arm == "icm"


def test_malformed_estimate_falls_back_to_valid_loc_range(tmp_path):
    metadata = {"target_files_count": 1, "estimated_loc": "lots", "target_loc_range": "10-20"}
    with pytest.warns(UserWarning, match="estimated_loc"):
        decision = classify_mode("auto", metadata, tmp_path)
    assert decision.loc_source == "target_loc_range"
    assert decision.loc == 20
    assert decision.arm == "icm_lite"


@pytest.mark.parametrize("task_id", ["BENCH-007", "BENCH-008", "BENCH-009", "BENCH-010", "BENCH-011", "BENCH-012", "BENCH-013", "BENCH-014", "BENCH-015", "BENCH-016", "BENCH-017", "BENCH-018", "BENCH-019", "BENCH-020"])
def test_bench_multifile_metadata_routes_to_full_icm(task_id):
    task_dir = runner.WORKSPACE_ROOT / "benchmarks" / task_id
    metadata = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    assert len(metadata["target_files"]) == 4
    assert all((task_dir / "workspace" / name).is_file() for name in metadata["target_files"])
    assert resolve_mode("auto", metadata, task_dir / "workspace") == "icm"


@pytest.mark.parametrize(("line_count", "arm"), [(149, "icm_lite"), (150, "icm")])
def test_auto_counts_physical_lines_of_the_named_file_only(tmp_path, line_count, arm):
    (tmp_path / "target.py").write_text("pass\n" * line_count, encoding="utf-8")
    (tmp_path / "unrelated.py").write_text("pass\n" * 200, encoding="utf-8")
    assert resolve_mode("auto", {"target_files": ["target.py"]}, tmp_path) == arm


@pytest.mark.parametrize(
    ("task", "flags", "arm", "markers"),
    [
        ("BENCH-005", ["--mode", "auto"], "icm_lite", ("Single-Stage Contract",)),
        ("BENCH-007", ["--mode", "auto"], "icm", ("5-stage ICM", "05_retro")),
        ("BENCH-007", ["--mode", "icm-lite"], "icm_lite", ("Single-Stage Contract",)),
        ("BENCH-001", ["--mode", "icm"], "icm", ("5-stage ICM", "05_retro")),
        ("BENCH-001", ["--mode", "baseline"], "baseline", ()),
        ("BENCH-001", ["--arm", "icm"], "icm", ("4-stage ICM contract",)),
        ("BENCH-001", [], "baseline", ()),
    ],
)
def test_benchmark_cli_selects_prompt_and_ledger_arm(tmp_path, monkeypatch, task, flags, arm, markers):
    evidence_dir = tmp_path / "evidence"
    db = tmp_path / "runs.db"
    monkeypatch.setattr(runner, "DEFAULT_EVIDENCE_DIR", evidence_dir)
    prepare_workspace = runner.WorkspaceManager.prepare_arm_workspace

    def prepare_in_tmp(**kwargs):
        return prepare_workspace(**{**kwargs, "workspace_root": tmp_path / "workspaces"})

    monkeypatch.setattr(runner.WorkspaceManager, "prepare_arm_workspace", prepare_in_tmp)
    monkeypatch.setattr(sys, "argv", ["runner.py", "--live-bench", task, "--db", str(db), *flags])
    instructions = (runner.WORKSPACE_ROOT / "benchmarks" / task / "workspace" / "INSTRUCTIONS.md").read_text(encoding="utf-8")
    calls = []

    def fake_cli(cmd, **kwargs):
        calls.append(cmd[cmd.index("-p") + 1])
        return subprocess.CompletedProcess(cmd, returncode=1, stdout=b"", stderr=b"")

    monkeypatch.setattr(runner.subprocess, "run", fake_cli)
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 0

    (prompt,) = calls
    if markers:
        assert prompt.endswith("\n\n" + instructions)
        assert all(marker in prompt for marker in markers)
        if arm == "icm_lite":
            assert "05_retro" not in prompt
    else:
        assert prompt == instructions
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT arm FROM runs").fetchall() == [(arm,)]
    assert len(list(evidence_dir.glob(f"live_{task}_*_{arm}_run1_*.ndjson"))) == 1


@pytest.mark.parametrize(
    ("target_files", "flags", "arms", "markers"),
    [
        ('["new.py"]', ["--mode", "auto"], ["icm_lite"], ["Single-Stage Contract"]),
        ('["new.py", "test_new.py"]', ["--mode", "auto"], ["icm"], ["05_retro"]),
        ('["new.py"]', ["--arm", "icm-subagents"], ["icm-subagents"], ["01_intake ->"]),
        ('["new.py"]', [], ["baseline", "icm"], [None, "01_intake ->"]),
    ],
)
def test_experiment_cli_routes_live_prompts(tmp_path, monkeypatch, target_files, flags, arms, markers):
    task = tmp_path / "task.md"
    task.write_text(
        f"---\ntask_id: TEST-001\ntarget_files: {target_files}\nestimated_loc: 149\n---\nImplement the task.",
        encoding="utf-8",
    )
    db = tmp_path / "runs.db"
    monkeypatch.setattr(run_experiment, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(run_experiment.shutil, "which", lambda _: "mock-cli")
    monkeypatch.setattr(sys, "argv", ["run_experiment.py", "--task", str(task), "--runs", "1", "--db", str(db), *flags])
    prompts = []

    def fake_cli(cmd, **kwargs):
        assert cmd[0] == "mock-cli"
        prompts.append(cmd[cmd.index("-p") + 1])
        return SimpleNamespace(stdout=io.BytesIO(), returncode=0, wait=lambda: None)

    monkeypatch.setattr(run_experiment.subprocess, "Popen", fake_cli)
    run_experiment.main()

    assert len(prompts) == len(markers)
    for prompt, marker in zip(prompts, markers):
        if marker is None:
            assert prompt == "Implement the task."
        else:
            assert marker in prompt
            assert prompt.endswith("\n\nImplement the task.")
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT arm FROM runs ORDER BY id").fetchall() == [(arm,) for arm in arms]


def test_experiment_dry_run_isolates_lite_fixtures_from_legacy_both(tmp_path, monkeypatch):
    db = tmp_path / "runs.db"
    fixtures = tmp_path / "fixtures.ndjson"
    events = run_experiment.DEFAULT_FIXTURES_PATH.read_text(encoding="utf-8").splitlines()
    lite_events = []
    for line in filter(str.strip, events):
        event = json.loads(line)
        if event["task_id"] == "MOCK-001" and event["arm"] == "icm":
            lite_events.append(json.dumps({**event, "arm": "icm_lite"}))
    fixtures.write_text("\n".join(events + lite_events), encoding="utf-8")
    argv = ["run_experiment.py", "--task", "MOCK-001", "--dry-run", "--db", str(db), "--fixtures", str(fixtures)]
    monkeypatch.setattr(sys, "argv", [*argv, "--mode", "icm-lite"])
    run_experiment.main()
    monkeypatch.setattr(sys, "argv", argv)
    run_experiment.main()

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT arm, COUNT(*) FROM runs GROUP BY arm ORDER BY arm").fetchall() == [
            ("baseline", 3), ("icm", 3), ("icm_lite", 3),
        ]


def test_scope_telemetry_flags_files_outside_declared_scope(tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "target.py").write_text("a = 1\n", encoding="utf-8")
    (snapshot / "other.py").write_text("x = 1\n", encoding="utf-8")
    workspace = tmp_path / "workspace"
    shutil.copytree(snapshot, workspace)
    (workspace / "target.py").write_text("a = 2\nb = 3\n", encoding="utf-8")
    (workspace / "stray.py").write_text("s = 0\n", encoding="utf-8")

    scope = runner.scope_telemetry(workspace, snapshot, {"target_files": ["target.py"]})
    assert scope["files_touched"]["target.py"]["kind"] == "modified"
    assert scope["files_touched"]["stray.py"]["kind"] == "added"
    assert scope["scope_mismatch"] is True
    assert scope["lines_touched"] > 0


def test_scope_telemetry_clean_when_touched_matches_declared(tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "target.py").write_text("a = 1\n", encoding="utf-8")
    workspace = tmp_path / "workspace"
    shutil.copytree(snapshot, workspace)
    (workspace / "target.py").write_text("a = 2\n", encoding="utf-8")

    scope = runner.scope_telemetry(workspace, snapshot, {"target_files": ["target.py"]})
    assert scope["scope_mismatch"] is False
    assert list(scope["files_touched"]) == ["target.py"]


def test_scope_telemetry_tolerates_malformed_target_files(tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "target.py").write_text("a = 1\n", encoding="utf-8")
    workspace = tmp_path / "workspace"
    shutil.copytree(snapshot, workspace)
    (workspace / "target.py").write_text("a = 2\n", encoding="utf-8")

    for declared in ([None], [""], ["nested/../target.py"], ["target.py", 7]):
        scope = runner.scope_telemetry(workspace, snapshot, {"target_files": declared})
        assert scope["files_touched"].keys() == {"target.py"}
    assert runner.scope_telemetry(workspace, snapshot, {"target_files": ["nested/../target.py"]})["scope_mismatch"] is False
    assert runner.scope_telemetry(workspace, snapshot, {"target_files": [None]})["scope_mismatch"] is True


def test_tree_files_keeps_internal_symlinks_rejects_escapes(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "real.py").write_text("a = 1\n", encoding="utf-8")
    outside = tmp_path / "outside.py"
    outside.write_text("secret = 1\n", encoding="utf-8")
    (root / "inner_link.py").symlink_to(root / "real.py")
    (root / "link.py").symlink_to(outside)
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "deep.py").write_text("d = 1\n", encoding="utf-8")
    (root / "dir_link").symlink_to(nested, target_is_directory=True)

    files = runner._tree_files(root)
    assert set(files) == {"real.py", "inner_link.py"}


def test_run_benchmark_live_warns_on_malformed_task_json(tmp_path, monkeypatch):
    task_dir = runner.WORKSPACE_ROOT / "benchmarks" / "BENCH-001"
    metadata_path = task_dir / "task.json"
    original = metadata_path.read_text(encoding="utf-8")
    evidence_dir = tmp_path / "evidence"
    db = tmp_path / "runs.db"
    monkeypatch.setattr(runner, "DEFAULT_EVIDENCE_DIR", evidence_dir)
    prepare_workspace = runner.WorkspaceManager.prepare_arm_workspace

    def prepare_in_tmp(**kwargs):
        return prepare_workspace(**{**kwargs, "workspace_root": tmp_path / "workspaces"})

    monkeypatch.setattr(runner.WorkspaceManager, "prepare_arm_workspace", prepare_in_tmp)

    def fake_cli(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=1, stdout=b"", stderr=b"")

    monkeypatch.setattr(runner.subprocess, "run", fake_cli)
    try:
        metadata_path.write_text("not json {", encoding="utf-8")
        with pytest.warns(UserWarning, match="task.json"):
            runner.run_benchmark_live(
                task_id="BENCH-001", arm="baseline", run_index=1,
                db_path=db, workspace_root=tmp_path / "workspaces",
            )
        metadata_path.write_text('["a", "b"]', encoding="utf-8")
        with pytest.warns(UserWarning, match="task.json"):
            runner.run_benchmark_live(
                task_id="BENCH-001", arm="baseline", run_index=1,
                db_path=db, workspace_root=tmp_path / "workspaces",
            )
    finally:
        metadata_path.write_text(original, encoding="utf-8")


def test_live_bench_logs_scope_telemetry_and_run_event(tmp_path, monkeypatch, capsys):
    evidence_dir = tmp_path / "evidence"
    db = tmp_path / "runs.db"
    monkeypatch.setattr(runner, "DEFAULT_EVIDENCE_DIR", evidence_dir)
    prepare_workspace = runner.WorkspaceManager.prepare_arm_workspace

    def prepare_in_tmp(**kwargs):
        return prepare_workspace(**{**kwargs, "workspace_root": tmp_path / "workspaces"})

    monkeypatch.setattr(runner.WorkspaceManager, "prepare_arm_workspace", prepare_in_tmp)
    monkeypatch.setattr(sys, "argv", ["runner.py", "--live-bench", "BENCH-001", "--db", str(db), "--mode", "auto"])

    def fake_cli(cmd, **kwargs):
        cwd = Path(kwargs["cwd"])
        (cwd / "date_range.py").write_text("# touched\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode=1, stdout=b"", stderr=b"")

    monkeypatch.setattr(runner.subprocess, "run", fake_cli)
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 0

    out = capsys.readouterr().out
    assert "Scope telemetry" in out
    assert "loc_source=estimated_loc" in out or "loc_source=" in out
    with sqlite3.connect(db) as conn:
        phases = conn.execute(
            "SELECT phase, status FROM run_events ORDER BY seq"
        ).fetchall()
    assert ("scope", "scope_ok") in phases


@pytest.mark.parametrize("name", ["live_TEST-001_icm_lite_run1_123.ndjson", "live_TEST-001_model_icm_lite_run1_123.ndjson"])
def test_lite_evidence_is_imported_under_its_own_arm(tmp_path, name):
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / name).write_text('{"event":"init","init":{"model":"gemini-2.5-pro"}}\n', encoding="utf-8")
    db = tmp_path / "runs.db"

    assert ledger.import_orphan_evidence_runs(evidence_dir=evidence_dir, db_path=db) == 1
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT arm FROM runs").fetchall() == [("icm_lite",)]
