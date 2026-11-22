"""Unit tests for PR 2.1: versioned contracts registry, byte-stable static prefix, ICM v3, and 3-tier auto-v3 router."""

import hashlib
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest
import tiktoken

import complexity_router
from complexity_router import (
    CONTRACTS_DIR,
    DEFAULT_CONTRACT_REGISTRY,
    ICM_LITE,
    ICM_STAGED,
    ICM_V1,
    ICM_V2,
    ICM_V3,
    ICM_V3_REPO_MAP_MAX_TOKENS,
    MODES,
    build_mode_prompt,
    build_static_context_prefix,
    classify_mode,
    load_contract_registry,
    resolve_contract_metadata,
    resolve_mode,
    verify_contract_registry,
    _workspace_footprint,
)
import repo_map
import runner


# ---------------------------------------------------------------------------
# (a) Versioned contracts/ registry & SHA-256 verification
# ---------------------------------------------------------------------------


def test_contract_registry_passes_and_has_expected_entries():
    verified = verify_contract_registry()
    assert set(verified) == {ICM_LITE, ICM_V1, ICM_V2, ICM_V3}

    registry = load_contract_registry()
    required_fields = {
        "id",
        "file",
        "sha256",
        "parent_version",
        "hypothesis",
        "changes_from_prev",
        "inject_repo_map",
        "repo_map_max_tokens",
        "execution_strategy",
    }
    for cid, entry in registry.items():
        assert required_fields.issubset(entry.keys())
        assert entry["id"] == cid
        assert entry["execution_strategy"] in ("single_session", "two_phase_staged")
        assert len(entry["sha256"]) == 64

    assert registry[ICM_V3]["parent_version"] == ICM_V2
    assert registry[ICM_V3]["inject_repo_map"] is True
    assert registry[ICM_V3]["repo_map_max_tokens"] == ICM_V3_REPO_MAP_MAX_TOKENS
    assert registry[ICM_V3]["execution_strategy"] == "single_session"

    # Existing template files remain intact and mirrored
    def _norm(p: Path) -> str:
        return p.read_text(encoding="utf-8").replace("\r\n", "\n")

    assert _norm(CONTRACTS_DIR / "icm_lite.md") == _norm(complexity_router.LITE_CONTRACT)
    assert _norm(CONTRACTS_DIR / "icm_v2.md") == _norm(complexity_router.V2_CONTRACT)


def test_verify_contract_registry_detects_tampered_sha_and_missing_file(tmp_path):
    copied_contracts = tmp_path / "contracts"
    shutil.copytree(CONTRACTS_DIR, copied_contracts)
    reg_copy = copied_contracts / "registry.json"

    # CRLF normalization keeps verification green cross-platform
    v3_copy = copied_contracts / "icm_v3.md"
    v3_copy.write_bytes(v3_copy.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
    assert verify_contract_registry(reg_copy)[ICM_V3] == load_contract_registry(DEFAULT_CONTRACT_REGISTRY)[ICM_V3]["sha256"]

    # Tampering contract markdown content fails verification
    v3_copy.write_text(v3_copy.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify_contract_registry(reg_copy)

    # Restore content, then tamper registry sha256 directly
    shutil.copy2(CONTRACTS_DIR / "icm_v3.md", v3_copy)
    reg_text = reg_copy.read_text(encoding="utf-8")
    orig_sha = load_contract_registry(reg_copy)[ICM_V3]["sha256"]
    tampered_sha = ("0" if orig_sha[0] != "0" else "1") + orig_sha[1:]
    reg_copy.write_text(reg_text.replace(orig_sha, tampered_sha), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify_contract_registry(reg_copy)

    # Missing contract file fails verification
    shutil.copy2(DEFAULT_CONTRACT_REGISTRY, reg_copy)
    v3_copy.unlink()
    with pytest.raises(ValueError, match="Missing contract file"):
        verify_contract_registry(reg_copy)


# ---------------------------------------------------------------------------
# (b) Byte-deterministic static context prefix & test runner detection
# ---------------------------------------------------------------------------


def test_static_context_prefix_is_byte_identical_across_temp_copies(tmp_path):
    src = runner.WORKSPACE_ROOT / "benchmarks" / "BENCH-018" / "workspace"
    copy_a = tmp_path / "alpha_snapshot_01"
    copy_b = tmp_path / "zzz_completely_different_dir_99"
    shutil.copytree(src, copy_a)
    shutil.copytree(src, copy_b)

    # Add transient caches that must be ignored identically
    for copy_dir in (copy_a, copy_b):
        (copy_dir / "__pycache__").mkdir(exist_ok=True)
        (copy_dir / "__pycache__" / "ledger.cpython-314.pyc").write_bytes(b"\x00\x01")
        (copy_dir / ".pytest_cache").mkdir(exist_ok=True)
        (copy_dir / ".pytest_cache" / "README.md").write_text("cache\n", encoding="utf-8")
        (copy_dir / "temp.pyo").write_bytes(b"\x00")

    prefix_a = build_static_context_prefix(copy_a, max_tokens=ICM_V3_REPO_MAP_MAX_TOKENS)
    prefix_b = build_static_context_prefix(copy_b, max_tokens=ICM_V3_REPO_MAP_MAX_TOKENS)

    assert hashlib.sha256(prefix_a.encode("utf-8")).hexdigest() == hashlib.sha256(prefix_b.encode("utf-8")).hexdigest()
    assert str(copy_a) not in prefix_a
    assert str(copy_b) not in prefix_b
    assert "alpha_snapshot_01" not in prefix_a
    assert "zzz_completely_different_dir_99" not in prefix_b

    # Expected sections and ignore rules
    assert "### Workspace Files" in prefix_a
    assert "- environment.json\n- ledger.py\n- models.py\n- rates.py\n- reconciler.py\n- tests/test_visible.py" in prefix_a
    assert "INSTRUCTIONS.md" not in prefix_a
    assert "__pycache__" not in prefix_a
    assert ".pytest_cache" not in prefix_a
    assert "temp.pyo" not in prefix_a
    assert "### Detected Test Runner\npytest -q --tb=short" in prefix_a
    assert "### Pre-Injected AST Symbol Map\n# Repository Map" in prefix_a

    # Verify AST map section stays within budget
    ast_section = prefix_a.split("### Pre-Injected AST Symbol Map\n", 1)[1]
    enc = tiktoken.get_encoding(repo_map.ENCODING_NAME)
    assert len(enc.encode(ast_section)) <= ICM_V3_REPO_MAP_MAX_TOKENS


def test_static_context_prefix_test_runner_detection(tmp_path):
    # Empty / no tests -> none detected
    ws_none = tmp_path / "none_ws"
    ws_none.mkdir()
    (ws_none / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    assert "### Detected Test Runner\nnone detected" in build_static_context_prefix(ws_none)

    # unittest under tests/
    ws_unit = tmp_path / "unit_ws"
    (ws_unit / "tests").mkdir(parents=True)
    (ws_unit / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (ws_unit / "tests" / "test_app.py").write_text(
        "import unittest\n\nclass TestApp(unittest.TestCase):\n    def test_ok(self):\n        self.assertEqual(1, 1)\n",
        encoding="utf-8",
    )
    assert "### Detected Test Runner\npython -m unittest discover -s tests" in build_static_context_prefix(ws_unit)

    # pyproject.toml with pytest overrides even without pytest import
    ws_pyp = tmp_path / "pyp_ws"
    ws_pyp.mkdir()
    (ws_pyp / "pyproject.toml").write_text("[tool.pytest.ini_options]\ntestpaths = ['tests']\n", encoding="utf-8")
    assert "### Detected Test Runner\npytest -q --tb=short" in build_static_context_prefix(ws_pyp)


# ---------------------------------------------------------------------------
# (c) 3-tier search-space routing in auto-v3
# ---------------------------------------------------------------------------


def _populate_workspace(root: Path, num_files: int, lines_per_file: int) -> None:
    root.mkdir(parents=True, exist_ok=True)
    body = "x = 1\n" * lines_per_file
    for i in range(num_files):
        (root / f"mod_{i:02d}.py").write_text(body, encoding="utf-8")


def test_auto_v3_three_tier_routing_and_ignored_artifacts(tmp_path):
    registry = load_contract_registry()

    # Tier 1: <=12 files and <=1500 LOC -> icm_lite (ignoring .git, __pycache__, INSTRUCTIONS.md)
    t1 = tmp_path / "tier1"
    _populate_workspace(t1, num_files=12, lines_per_file=100)
    (t1 / "INSTRUCTIONS.md").write_text("long instructions\n" * 2000, encoding="utf-8")
    (t1 / ".git").mkdir()
    (t1 / ".git" / "config").write_text("a\n" * 2000, encoding="utf-8")
    (t1 / "__pycache__").mkdir()
    (t1 / "__pycache__" / "mod_00.cpython-314.pyc").write_bytes(b"\x00" * 100)
    assert _workspace_footprint(t1) == (12, 1200)

    d1 = classify_mode("auto-v3", {}, t1)
    assert d1.arm == ICM_LITE
    assert d1.loc_source == "workspace_footprint"
    assert d1.loc == 1200
    assert d1.contract_version == ICM_LITE
    assert d1.contract_hash == registry[ICM_LITE]["sha256"]

    # Tier 2a: 13 <= file_count <= 50 even with small total LOC -> icm_v3
    t2_files = tmp_path / "tier2_files"
    _populate_workspace(t2_files, num_files=13, lines_per_file=10)
    d2_files = classify_mode("auto-v3", {}, t2_files)
    assert d2_files.arm == ICM_V3
    assert d2_files.loc_source == "workspace_footprint"
    assert d2_files.loc == 130
    assert d2_files.contract_version == ICM_V3
    assert d2_files.contract_hash == registry[ICM_V3]["sha256"]

    # Tier 2b: total_loc > 1500 with file_count <= 50 -> icm_v3
    t2_loc = tmp_path / "tier2_loc"
    _populate_workspace(t2_loc, num_files=4, lines_per_file=400)
    d2_loc = classify_mode("auto-v3", {}, t2_loc)
    assert d2_loc.arm == ICM_V3
    assert d2_loc.loc == 1600
    assert d2_loc.contract_version == ICM_V3
    assert d2_loc.contract_hash == registry[ICM_V3]["sha256"]

    # Tier 3a: file_count > 50 -> icm_staged
    t3_files = tmp_path / "tier3_files"
    _populate_workspace(t3_files, num_files=51, lines_per_file=5)
    d3_files = classify_mode("auto-v3", {}, t3_files)
    assert d3_files.arm == ICM_STAGED
    assert d3_files.loc == 255
    assert d3_files.contract_version == ICM_STAGED
    assert d3_files.contract_hash is None  # registered in PR 2.2

    # Tier 3b: multi_stage metadata overrides even small workspaces -> icm_staged
    d3_meta = classify_mode("auto-v3", {"multi_stage": True}, t1)
    assert d3_meta.arm == ICM_STAGED
    assert d3_meta.contract_version == ICM_STAGED


def test_explicit_v3_and_staged_modes_and_contract_metadata(tmp_path):
    assert {"auto", "auto-v3", "icm", "icm-lite", "icm-v2", "icm-v3", "icm-staged", "baseline"}.issubset(MODES)
    registry = load_contract_registry()

    assert resolve_mode("icm-v3", {}, tmp_path) == ICM_V3
    assert resolve_mode("icm-staged", {}, tmp_path) == ICM_STAGED

    d_v3 = classify_mode("icm-v3", {}, tmp_path)
    assert d_v3.contract_version == ICM_V3
    assert d_v3.contract_hash == registry[ICM_V3]["sha256"]

    d_icm = classify_mode("icm", {}, tmp_path)
    assert d_icm.contract_version == ICM_V1
    assert d_icm.contract_hash == registry[ICM_V1]["sha256"]

    d_base = classify_mode("baseline", {}, tmp_path)
    assert d_base.contract_version is None
    assert d_base.contract_hash is None

    assert resolve_contract_metadata("baseline") == (None, None)
    assert resolve_contract_metadata(ICM_V3) == (ICM_V3, registry[ICM_V3]["sha256"])


# ---------------------------------------------------------------------------
# (d) ICM v3 prompt rules + static prefix + manifest validation
# ---------------------------------------------------------------------------


def test_build_mode_prompt_icm_v3_contains_rules_and_static_prefix(tmp_path):
    ws = runner.WORKSPACE_ROOT / "benchmarks" / "BENCH-018" / "workspace"
    instructions = "Implement ledger reconciliation rounding rules."

    prompt = build_mode_prompt(instructions, ICM_V3, workspace=ws)
    assert prompt.endswith("\n\n" + instructions)

    # Zero-ceremony & tasks/ containment
    assert "01_intake.md" in prompt
    assert "05_retro.md" in prompt
    assert "tasks/" in prompt

    # 3-turn batch-first cadence
    assert "Turn 1" in prompt
    assert "Turn 2" in prompt
    assert "<=8-line" in prompt
    assert "Turn 3" in prompt
    assert "INSTRUCTIONS.md" in prompt

    # Pragmatic edit fallback
    assert ">120 LOC" in prompt
    assert "CRLF" in prompt
    assert "full-file write" in prompt

    # Loop-breaker & strict containment
    assert "2 consecutive" in prompt
    assert "1-line" in prompt
    assert ".." in prompt
    assert "missing external scripts" in prompt

    # Static context prefix appears before instructions
    assert "## Static Workspace Context" in prompt
    assert "### Workspace Files" in prompt
    assert "### Detected Test Runner\npytest -q --tb=short" in prompt
    assert "### Pre-Injected AST Symbol Map" in prompt
    assert prompt.index("## Static Workspace Context") < prompt.index(instructions)

    # Manifest governance detection recognizes ICM v3 prompts
    manifest = runner.RunManifest(
        manifest_id="MAN-V3",
        task_id="T-V3",
        task_version="1.0",
        created_at="2026-11-22T00:00:00Z",
        task_contract={"task_id": "T-V3"},
        arms={
            "baseline": runner.ArmConfig(arm="baseline", model="gemini-4-hydrogen-low", prompt=instructions),
            ICM_V3: runner.ArmConfig(arm=ICM_V3, model="gemini-4-hydrogen-low", prompt=prompt),
        },
    )
    val = runner.validate_manifest_configuration(manifest)
    assert val["intentional_governance_diffs"][ICM_V3]["prompt_has_icm_scaffolding"] is True
    assert val["intentional_governance_diffs"]["baseline"]["prompt_has_icm_scaffolding"] is False


# ---------------------------------------------------------------------------
# (e) run_benchmark_live persists contract_version & contract_hash to SQLite
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("flag_pair", "expected_arm", "expected_contract"),
    [
        (["--mode", "icm-v3"], ICM_V3, ICM_V3),
        (["--mode", "auto-v3"], ICM_LITE, ICM_LITE),
        (["--arm", "icm_v3"], ICM_V3, ICM_V3),
        (["--arm", "baseline"], "baseline", None),
    ],
)
def test_run_benchmark_live_persists_contract_version_and_hash(tmp_path, monkeypatch, flag_pair, expected_arm, expected_contract):
    evidence_dir = tmp_path / "evidence"
    db = tmp_path / "runs.db"
    monkeypatch.setattr(runner, "DEFAULT_EVIDENCE_DIR", evidence_dir)
    prepare_workspace = runner.WorkspaceManager.prepare_arm_workspace

    def prepare_in_tmp(**kwargs):
        return prepare_workspace(**{**kwargs, "workspace_root": tmp_path / "workspaces"})

    monkeypatch.setattr(runner.WorkspaceManager, "prepare_arm_workspace", prepare_in_tmp)
    monkeypatch.setattr(sys, "argv", ["runner.py", "--live-bench", "BENCH-018", "--db", str(db), *flag_pair])
    captured_prompts = []

    def fake_cli(cmd, **kwargs):
        captured_prompts.append(cmd[cmd.index("-p") + 1])
        return subprocess.CompletedProcess(cmd, returncode=1, stdout=b"", stderr=b"")

    monkeypatch.setattr(runner.subprocess, "run", fake_cli)
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 0

    (prompt,) = captured_prompts
    if expected_arm == ICM_V3:
        assert "## Static Workspace Context" in prompt
        assert "### Workspace Files" in prompt
        assert "reconciler.py" in prompt

    registry = load_contract_registry()
    expected_hash = registry[expected_contract]["sha256"] if expected_contract else None

    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT arm, contract_version, contract_hash FROM runs").fetchone()
    assert row == (expected_arm, expected_contract, expected_hash)
