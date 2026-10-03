"""
tests/unit/test_benchmarks.py - Acceptance Test Suite for Phase 3 Benchmark Pack

Covers acceptance criteria BEN-01 through BEN-04 across all six first-party tasks:
- BEN-01: Broken snapshot fails target check for the intended reason.
- BEN-02: Reference solution passes target checks and preserves passing checks.
- BEN-03: Deliberately flawed patch is rejected by protected checks.
- BEN-04: Workspace inspection verifies reference solutions and evaluators are inaccessible.

Total test count: 6 tasks x 4 acceptance criteria = 24 test cases.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest

import runner

BENCHMARKS_DIR = runner.WORKSPACE_ROOT / "benchmarks"
TASK_IDS = ["BENCH-001", "BENCH-002", "BENCH-003", "BENCH-004", "BENCH-005", "BENCH-006"]


def _copy_tree_files(src_dir: Path, dst_dir: Path) -> None:
    """Copy all files from src_dir into dst_dir preserving subdirectories."""
    for p in src_dir.rglob("*"):
        if p.is_file():
            rel = p.relative_to(src_dir)
            target = dst_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)


# ---------------------------------------------------------------------------
# BEN-01: Broken snapshot fails target check for the intended reason
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("task_id", TASK_IDS)
def test_ben_01_broken_snapshot_fails_target_check(task_id: str, tmp_path: Path):
    """
    BEN-01: Evaluate the initial broken snapshot.
    Expected: Target test fails for the intended reason.
    """
    task_dir = BENCHMARKS_DIR / task_id
    task_meta = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    expected_reason = task_meta["expected_broken_reason"]

    snapshot_dir = task_dir / "workspace"
    evaluator_dir = task_dir / "evaluator"
    evaluator = runner.ProtectedEvaluator(evaluator_dir)

    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir,
        arm="baseline",
        workspace_root=tmp_path / "workspaces",
        run_id=f"ben01_{task_id.lower().replace('-', '_')}",
    )

    try:
        verif = evaluator.evaluate_workspace(ws.path)

        assert verif.passed is False, f"Broken snapshot for {task_id} unexpectedly passed evaluation!"
        assert verif.verification_status == "failed"

        # Assert expected broken failure reason is documented in reasons or output
        has_reason = any(expected_reason in r for r in verif.reasons) or (expected_reason in verif.output)
        assert has_reason, (
            f"Expected broken failure reason '{expected_reason}' was not found for {task_id}.\n"
            f"Evaluator reasons: {verif.reasons}\nEvaluator output:\n{verif.output}"
        )
    finally:
        ws.cleanup()


# ---------------------------------------------------------------------------
# BEN-02: Reference solution passes target checks and preserves passing checks
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("task_id", TASK_IDS)
def test_ben_02_reference_solution_passes(task_id: str, tmp_path: Path):
    """
    BEN-02: Evaluate the reference solution.
    Expected: Target tests pass and previously passing checks remain green.
    """
    task_dir = BENCHMARKS_DIR / task_id
    snapshot_dir = task_dir / "workspace"
    reference_dir = task_dir / "reference"
    evaluator_dir = task_dir / "evaluator"
    evaluator = runner.ProtectedEvaluator(evaluator_dir)

    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir,
        arm="baseline",
        workspace_root=tmp_path / "workspaces",
        run_id=f"ben02_{task_id.lower().replace('-', '_')}",
    )

    try:
        # Apply reference solution files into workspace
        _copy_tree_files(reference_dir, ws.path)

        # 1. Protected evaluator evaluation
        verif = evaluator.evaluate_workspace(ws.path)
        assert verif.passed is True, (
            f"Reference solution for {task_id} failed protected checks!\n"
            f"Reasons: {verif.reasons}\nOutput:\n{verif.output}"
        )
        assert verif.verification_status == "passed"
        assert verif.reasons == []

        # 2. Previously passing checks remain green
        vis_test = ws.path / "tests" / "test_visible.py"
        if vis_test.exists():
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ws.path) + os.pathsep + env.get("PYTHONPATH", "")
            res_vis = subprocess.run(
                [sys.executable, "-m", "pytest", str(vis_test)],
                cwd=str(ws.path),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            assert res_vis.returncode == 0, f"Visible test regression in {task_id}:\n{res_vis.stderr}\n{res_vis.stdout}"

        acct_test = ws.path / "tests" / "test_accounting.py"
        if task_id == "BENCH-006" and acct_test.exists():
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ws.path) + os.pathsep + env.get("PYTHONPATH", "")
            res_acct = subprocess.run(
                [sys.executable, "-m", "pytest", str(acct_test)],
                cwd=str(ws.path),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            assert res_acct.returncode == 0, f"Accounting tests failed on genuine implementation:\n{res_acct.stderr}"

    finally:
        ws.cleanup()


# ---------------------------------------------------------------------------
# BEN-03: Deliberately flawed patch is rejected by protected checks
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("task_id", TASK_IDS)
def test_ben_03_flawed_solution_rejected(task_id: str, tmp_path: Path):
    """
    BEN-03: Evaluate a deliberately wrong patch.
    Expected: Protected tests reject it.
    """
    task_dir = BENCHMARKS_DIR / task_id
    snapshot_dir = task_dir / "workspace"
    flawed_dir = task_dir / "flawed"
    evaluator_dir = task_dir / "evaluator"
    evaluator = runner.ProtectedEvaluator(evaluator_dir)

    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir,
        arm="baseline",
        workspace_root=tmp_path / "workspaces",
        run_id=f"ben03_{task_id.lower().replace('-', '_')}",
    )

    try:
        # Apply flawed solution files into workspace
        _copy_tree_files(flawed_dir, ws.path)

        verif = evaluator.evaluate_workspace(ws.path)
        assert verif.passed is False, f"Deliberately flawed patch for {task_id} was improperly accepted by evaluator!"
        assert verif.verification_status == "failed"
    finally:
        ws.cleanup()


# ---------------------------------------------------------------------------
# BEN-04: Workspace inspection verifies reference solutions and evaluators are inaccessible
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("task_id", TASK_IDS)
def test_ben_04_workspace_inaccessibility(task_id: str, tmp_path: Path):
    """
    BEN-04: Inspect workspace and accessible history.
    Expected: Reference answers and evaluator-only material inaccessible to agent.
    """
    task_dir = BENCHMARKS_DIR / task_id
    snapshot_dir = task_dir / "workspace"
    evaluator_dir = task_dir / "evaluator"
    reference_dir = task_dir / "reference"

    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir,
        arm="baseline",
        workspace_root=tmp_path / "workspaces",
        run_id=f"ben04_{task_id.lower().replace('-', '_')}",
    )

    try:
        ws_resolved = ws.path.resolve()

        # 1. Structural inaccessibility: Evaluator and reference dirs are strictly external
        with pytest.raises(ValueError):
            evaluator_dir.resolve().relative_to(ws_resolved)

        with pytest.raises(ValueError):
            reference_dir.resolve().relative_to(ws_resolved)

        # 2. File tree inspection: No evaluator or reference artifacts present inside workspace
        for p in ws.path.rglob("*"):
            if p.is_file():
                rel = p.relative_to(ws.path).as_posix()
                # Must not contain evaluator files or reference answer directories
                assert "evaluator" not in rel.lower(), f"Evaluator leaked into workspace: {rel}"
                assert "reference" not in rel.lower(), f"Reference solution leaked into workspace: {rel}"

        # 3. Content inspection: INSTRUCTIONS.md does not leak reference code or secrets
        instructions_file = ws.path / "INSTRUCTIONS.md"
        assert instructions_file.exists()
        inst_text = instructions_file.read_text(encoding="utf-8")
        assert "ALL CHECKS PASSED" not in inst_text
        assert "REASON:" not in inst_text

        # 4. Protected Evaluator SHA-256 integrity verification
        evaluator = runner.ProtectedEvaluator(evaluator_dir)
        is_valid, computed_hash = evaluator.verify_hash()
        assert is_valid is True
        assert len(computed_hash) == 64

        # 5. Tamper detection: tampering triggers evaluator_tampered
        tampered_evaluator = runner.ProtectedEvaluator(evaluator_dir, expected_hash="0" * 64)
        tamper_verif = tampered_evaluator.evaluate_workspace(ws.path)
        assert tamper_verif.passed is False
        assert tamper_verif.verification_status == "evaluator_error"
        assert "evaluator_tampered" in tamper_verif.reasons

    finally:
        ws.cleanup()


# ---------------------------------------------------------------------------
# Deep Hardening & Security Verifications (BEN-03 / BEN-04 Extensions)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("prohibited_file", [
    "irrelevant_analytics.py",
    "irrelevant_utils.py",
    "legacy_notes_2023.md",
    "INSTRUCTIONS.md",
])
def test_bench005_scope_violation_tamper_rejected(prohibited_file: str, tmp_path: Path):
    """BENCH-005: Any alteration to prohibited files must be rejected with prohibited_file_modified."""
    task_dir = BENCHMARKS_DIR / "BENCH-005"
    evaluator = runner.ProtectedEvaluator(task_dir / "evaluator")
    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=task_dir / "workspace",
        arm="baseline",
        workspace_root=tmp_path / "workspaces",
        run_id=f"scope_{prohibited_file.replace('.', '_')}",
    )
    try:
        # Apply valid reference fix to config_loader.py
        shutil.copy2(task_dir / "reference" / "config_loader.py", ws.path / "config_loader.py")

        # Tamper with the prohibited file
        target_path = ws.path / prohibited_file
        target_path.write_text("TAMPERED CONTENT", encoding="utf-8")

        verif = evaluator.evaluate_workspace(ws.path)
        assert verif.passed is False
        assert verif.verification_status == "failed"
        assert any("prohibited_file_modified" in r for r in verif.reasons) or ("prohibited_file_modified" in verif.output)
    finally:
        ws.cleanup()


def test_bench006_implementation_tampering_rejected(tmp_path: Path):
    """BENCH-006: Any modification to accounting_validator.py must be rejected with prohibited_file_modified."""
    task_dir = BENCHMARKS_DIR / "BENCH-006"
    evaluator = runner.ProtectedEvaluator(task_dir / "evaluator")
    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=task_dir / "workspace",
        arm="baseline",
        workspace_root=tmp_path / "workspaces",
        run_id="tamper_acct_val",
    )
    try:
        # Apply reference test suite
        shutil.copy2(task_dir / "reference" / "tests" / "test_accounting.py", ws.path / "tests" / "test_accounting.py")

        # Tamper with accounting_validator.py (e.g. comment out or change validation)
        val_file = ws.path / "accounting_validator.py"
        val_content = val_file.read_text(encoding="utf-8") + "\n# TAMPERED COMMENT\n"
        val_file.write_text(val_content, encoding="utf-8")

        verif = evaluator.evaluate_workspace(ws.path)
        assert verif.passed is False
        assert verif.verification_status == "failed"
        assert any("prohibited_file_modified" in r for r in verif.reasons) or ("prohibited_file_modified" in verif.output)
    finally:
        ws.cleanup()


def test_runtime_evaluator_tampering_detected(tmp_path: Path):
    """RUN-10 / BEN-04: Subprocess tampering with evaluator during evaluation is caught immediately."""
    # Setup dummy evaluator directory
    eval_dir = tmp_path / "eval_tamper"
    eval_dir.mkdir()
    eval_py = eval_dir / "evaluator.py"
    eval_py.write_text("""
import sys
from pathlib import Path
# Simulate malicious payload attempting to modify evaluator during grading
with open(__file__, "a") as f:
    f.write("\\n# Tamper payload appended during execution\\n")
print("ALL CHECKS PASSED")
sys.exit(0)
""", encoding="utf-8")

    ws_dir = tmp_path / "ws_tamper"
    ws_dir.mkdir()

    evaluator = runner.ProtectedEvaluator(eval_dir)
    verif = evaluator.evaluate_workspace(ws_dir)

    assert verif.passed is False
    assert verif.verification_status == "evaluator_error"
    assert "evaluator_tampered_during_execution" in verif.reasons

