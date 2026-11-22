import tempfile
import sqlite3
import os
from pathlib import Path
import pytest
from scripts.run_experiment import execute_verification, get_next_run_index, parse_task_file
import scripts.ledger as ledger
import runner

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


# ---------------------------------------------------------------------------
# PR 1.1: Isolated git containment hardening
# ---------------------------------------------------------------------------

def _make_snapshot(tmp_path: Path) -> Path:
    snapshot_dir = tmp_path / "task_snapshot"
    snapshot_dir.mkdir()
    (snapshot_dir / "solution.py").write_text("def solve(): return 1\n", encoding="utf-8")
    return snapshot_dir


def test_workspace_git_toplevel_resolves_to_workspace_itself(tmp_path: Path):
    """git rev-parse --show-toplevel inside a disposable workspace resolves to itself, not the host repo."""
    import subprocess

    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=_make_snapshot(tmp_path),
        arm="baseline",
        workspace_root=tmp_path / "workspaces",
        run_id="git_top_test",
    )
    try:
        assert (ws.path / ".git").is_dir()
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(ws.path),
            capture_output=True,
            text=True,
            check=True,
        )
        assert Path(out.stdout.strip()).resolve() == ws.path.resolve()
        assert Path(out.stdout.strip()).resolve() != runner.WORKSPACE_ROOT.resolve()
    finally:
        ws.cleanup()


def test_init_git_snapshot_commit_is_deterministic(tmp_path: Path):
    """init_git produces a deterministic 'snapshot' commit with fixed author/committer identity."""
    import subprocess

    snapshot_dir = _make_snapshot(tmp_path)
    ws_a = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir, arm="baseline",
        workspace_root=tmp_path / "ws_a", run_id="det_a",
    )
    ws_b = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir, arm="icm",
        workspace_root=tmp_path / "ws_b", run_id="det_b",
    )
    try:
        fmt = "%an|%ae|%cn|%ce|%aI|%cI|%s"
        log_a = subprocess.run(
            ["git", "log", "-1", f"--format={fmt}"],
            cwd=str(ws_a.path), capture_output=True, text=True, check=True,
        ).stdout.strip()
        assert log_a == (
            "Ai-Lab|ailab@local|Ai-Lab|ailab@local|"
            "2026-01-01T00:00:00Z|2026-01-01T00:00:00Z|snapshot"
        )
        # Identical trees + fixed identity/dates -> identical commit hash
        rev_a = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ws_a.path), capture_output=True, text=True, check=True,
        ).stdout.strip()
        rev_b = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ws_b.path), capture_output=True, text=True, check=True,
        ).stdout.strip()
        assert rev_a == rev_b
        # Clean index after snapshot commit
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(ws_a.path), capture_output=True, text=True, check=True,
        ).stdout.strip()
        assert status == ""
    finally:
        ws_a.cleanup()
        ws_b.cleanup()


def test_git_dir_ignored_by_hash_tree_and_scope_telemetry(tmp_path: Path):
    """.git must never contaminate snapshot hashes, tree file maps, or scope drift detection."""
    import shutil as _shutil

    snapshot_dir = _make_snapshot(tmp_path)
    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir, arm="baseline",
        workspace_root=tmp_path / "workspaces", run_id="git_ignore_test",
    )
    try:
        assert (ws.path / ".git").is_dir()

        # _tree_files never lists .git internals
        files = runner._tree_files(ws.path)
        assert files
        assert not any(".git" in rel.split("/") for rel in files)

        # _hash_directory_tree output equals the hash of the same tree sans .git
        plain = tmp_path / "plain_tree"
        _shutil.copytree(
            ws.path, plain,
            ignore=_shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"),
        )
        assert runner._hash_directory_tree(ws.path) == runner._hash_directory_tree(plain)

        # scope_telemetry sees zero drift (snapshot copied verbatim, .git excluded)
        scope = runner.scope_telemetry(ws.path, snapshot_dir, {})
        assert not any(".git" in rel.split("/") for rel in scope["files_touched"])
        assert scope["files_touched"] == {}
        assert scope["scope_mismatch"] is False
    finally:
        ws.cleanup()


def test_rollback_preserves_isolated_git_repo(tmp_path: Path):
    """rollback_to_backup restores files but keeps the workspace .git intact and hash-clean."""
    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=_make_snapshot(tmp_path), arm="baseline",
        workspace_root=tmp_path / "workspaces", run_id="rb_git_test",
    )
    try:
        pre_hash = ws.snapshot_tree_hash()
        ws.capture_backup()

        (ws.path / "solution.py").write_text("def solve(): return 999\n", encoding="utf-8")
        (ws.path / "rogue.py").write_text("x = 1\n", encoding="utf-8")

        restored = ws.rollback_to_backup()
        assert restored == pre_hash
        assert not (ws.path / "rogue.py").exists()
        assert (ws.path / "solution.py").read_text(encoding="utf-8") == "def solve(): return 1\n"
        assert (ws.path / ".git").is_dir()
        # Backup itself must not contain .git either
        assert not (ws.backup_dir / ".git").exists()
    finally:
        ws.cleanup()


def test_is_safe_host_target_allows_os_temp_and_refuses_host_paths(tmp_path: Path):
    """OS-temp workspaces outside WORKSPACE_ROOT are safe; host paths outside tmp/ are refused."""
    snap = _make_snapshot(tmp_path)

    # OS temp outside WORKSPACE_ROOT -> safe
    os_temp = Path(tempfile.gettempdir()) / "ai_lab_disposable_workspaces" / "x_baseline"
    ws_temp = runner.DisposableWorkspace(path=os_temp, arm="baseline", snapshot_dir=snap, run_id="t")
    assert ws_temp._is_safe_host_target() is True

    # tmp_path (outside the repo checkout) -> safe
    ws_out = runner.DisposableWorkspace(path=tmp_path / "ws", arm="baseline", snapshot_dir=snap, run_id="t")
    assert ws_out._is_safe_host_target() is True

    # Inside WORKSPACE_ROOT under tmp/ -> allowed
    ws_tmp = runner.DisposableWorkspace(
        path=runner.WORKSPACE_ROOT / "tmp" / "d", arm="baseline", snapshot_dir=snap, run_id="t"
    )
    assert ws_tmp._is_safe_host_target() is True

    # Host root and host subdirectories outside tmp/ -> refused
    for bad in (runner.WORKSPACE_ROOT, runner.WORKSPACE_ROOT / "scripts", runner.WORKSPACE_ROOT.parent):
        ws_bad = runner.DisposableWorkspace(path=bad, arm="baseline", snapshot_dir=snap, run_id="t")
        assert ws_bad._is_safe_host_target() is False, bad


def test_canonical_workspace_deterministic_name_per_task_and_arm(tmp_path: Path):
    """canonical_workspace yields a deterministic <task_id>_<arm> dir reusable across runs."""
    snapshot_dir = _make_snapshot(tmp_path)
    ws_root = tmp_path / "workspaces"

    ws1 = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir, arm="baseline", workspace_root=ws_root,
        run_id="run_1", canonical_workspace=True, task_id="BENCH-042", init_git=False,
    )
    try:
        assert ws1.path.name == "BENCH-042_baseline"
    finally:
        ws1.cleanup()

    # A later run with a different run_id resolves to the same directory
    ws2 = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir, arm="baseline", workspace_root=ws_root,
        run_id="run_999", canonical_workspace=True, task_id="BENCH-042", init_git=False,
    )
    assert ws2.path == ws1.path
    ws2.cleanup()

    # Different arm -> different canonical dir
    ws3 = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir, arm="icm", workspace_root=ws_root,
        run_id="run_1", canonical_workspace=True, task_id="BENCH-042", init_git=False,
    )
    assert ws3.path.name == "BENCH-042_icm"
    ws3.cleanup()


def test_canonical_workspace_marker_blocks_foreign_dir(tmp_path: Path):
    """A pre-existing canonical dir without an ownership marker is still refused."""
    ws_root = tmp_path / "workspaces"
    squatter = ws_root / "BENCH-042_baseline"
    squatter.mkdir(parents=True)
    (squatter / "foreign.txt").write_text("not ours\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="missing ownership marker"):
        runner.WorkspaceManager.prepare_arm_workspace(
            snapshot_dir=_make_snapshot(tmp_path), arm="baseline",
            workspace_root=ws_root, run_id="r1",
            canonical_workspace=True, task_id="BENCH-042",
        )
    assert squatter.exists()


def test_init_git_false_leaves_workspace_without_git_dir(tmp_path: Path):
    """init_git=False preserves the old no-.git behavior."""
    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=_make_snapshot(tmp_path), arm="baseline",
        workspace_root=tmp_path / "workspaces", run_id="no_git_test", init_git=False,
    )
    try:
        assert not (ws.path / ".git").exists()
    finally:
        ws.cleanup()


def test_git_env_leak_cannot_redirect_snapshot_commit(tmp_path: Path, monkeypatch):
    """Exported host GIT_DIR/GIT_WORK_TREE must not redirect the workspace's git init."""
    host_dir = tmp_path / "host_checkout"
    host_dir.mkdir()
    (host_dir / "precious.py").write_text("x = 1\n", encoding="utf-8")
    host_git = host_dir / ".git"
    monkeypatch.setenv("GIT_DIR", str(host_git))
    monkeypatch.setenv("GIT_WORK_TREE", str(host_dir))

    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=_make_snapshot(tmp_path), arm="baseline",
        workspace_root=tmp_path / "workspaces", run_id="git_leak_test",
    )
    try:
        # Workspace got its own repo; host dir was not committed into
        assert (ws.path / ".git").is_dir()
        assert not host_git.exists()
        import subprocess
        clean_env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(ws.path), capture_output=True, text=True, check=True, env=clean_env,
        ).stdout.strip()
        assert Path(top).resolve() == ws.path.resolve()
    finally:
        ws.cleanup()


def test_workspace_root_owned_by_other_account_refused(tmp_path: Path, monkeypatch):
    """A base_temp owned by another local account is untrusted and refused."""
    other_root = tmp_path / "foreign_root"
    other_root.mkdir()
    monkeypatch.setenv("AI_LAB_WORKSPACE_ROOT", str(other_root))
    monkeypatch.setattr(runner.os, "getuid", lambda: -1)

    with pytest.raises(RuntimeError, match="owned by another local account"):
        runner.WorkspaceManager.prepare_arm_workspace(
            snapshot_dir=_make_snapshot(tmp_path), arm="baseline", run_id="r",
        )


def test_canonical_workspace_refuses_overwrite_while_owner_alive(tmp_path: Path):
    """A canonical dir owned by a live run on this host cannot be reclaimed."""
    snapshot_dir = _make_snapshot(tmp_path)
    ws1 = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir, arm="baseline",
        workspace_root=tmp_path / "workspaces", run_id="run_live",
        canonical_workspace=True, task_id="BENCH-042",
    )
    try:
        # Marker records our own live pid -> second canonical prepare must refuse
        with pytest.raises(RuntimeError, match="still in use by live run"):
            runner.WorkspaceManager.prepare_arm_workspace(
                snapshot_dir=snapshot_dir, arm="baseline",
                workspace_root=tmp_path / "workspaces", run_id="run_other",
                canonical_workspace=True, task_id="BENCH-042",
            )
        assert ws1.path.exists()
    finally:
        ws1.cleanup()


def test_workspace_inside_checkout_outside_tmp_refused(tmp_path: Path, monkeypatch):
    """base_temp inside WORKSPACE_ROOT but outside tmp/ is rejected outright."""
    monkeypatch.setenv(
        "AI_LAB_WORKSPACE_ROOT", str(runner.WORKSPACE_ROOT / "nested_ws_root")
    )
    with pytest.raises(ValueError, match="inside the host checkout"):
        runner.WorkspaceManager.prepare_arm_workspace(
            snapshot_dir=_make_snapshot(tmp_path), arm="baseline", run_id="r",
        )


def test_workspace_inside_checkout_tmp_warns(tmp_path: Path, monkeypatch):
    """base_temp under WORKSPACE_ROOT/tmp remains allowed but warns about host leakage."""
    monkeypatch.setenv(
        "AI_LAB_WORKSPACE_ROOT", str(runner.WORKSPACE_ROOT / "tmp" / "ws_root")
    )
    with pytest.warns(UserWarning, match="host AGENTS.md"):
        ws = runner.WorkspaceManager.prepare_arm_workspace(
            snapshot_dir=_make_snapshot(tmp_path), arm="baseline",
            run_id="tmp_ws_test", init_git=False,
        )
    try:
        assert runner.WORKSPACE_ROOT.resolve() in ws.path.resolve().parents
        assert ws._is_safe_host_target() is True
    finally:
        ws.cleanup()
