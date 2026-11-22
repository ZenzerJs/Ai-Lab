#!/usr/bin/env python3
"""
scripts/runner.py - Execution & Disposable Workspace Harness for Ai-Lab

Implements Phase 2 safe preparation, isolation, configuration validation,
protected evaluators, offline/fixture execution, lifecycle handling, and
manual import adapters:
- RUN-01, RUN-02, RUN-03: Disposable workspaces, separate arms, host protection.
- RUN-04, RUN-05: Run manifests, mismatch rejection, intentional governance diffs.
- RUN-06, RUN-07: Lifecycle timeout and interruption/resume preservation.
- RUN-08: Offline execution workflow asserting zero provider/paid API calls.
- RUN-09, RUN-10: Protected evaluators outside workspace and SHA-256 tamper detection.
- RUN-11: Manual adapter with correctness evaluation and unavailable usage/cost.
"""

import argparse
import copy
from contextlib import contextmanager
import dataclasses
import difflib
import hashlib
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Set, Tuple

# Ensure UTF-8 output encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Path setup
SCRIPTS_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import stat
import ledger
import pricing
from complexity_router import (
    ICM_LITE,
    ICM_STAGED,
    ICM_V2,
    ICM_V3,
    MODES,
    RoutingDecision,
    build_mode_prompt,
    build_staged_exec_prompt,
    build_staged_prompts,
    classify_mode,
    count_ast_symbols,
    extract_ast_symbol_spans,
    resolve_contract_metadata,
    resolve_mode,
)

DEVIN_API_BASE_URL = "https://api.devin.ai"

DEFAULT_FIXTURES_PATH = WORKSPACE_ROOT / "experiments" / "fixtures" / "mock_stream.ndjson"
DEFAULT_EVIDENCE_DIR = WORKSPACE_ROOT / "experiments" / "evidence"


def extract_acus_consumed(session_payload: Mapping[str, Any]) -> Optional[float]:
    """Extract and validate `acus_consumed` from a Devin session API payload."""
    if not isinstance(session_payload, Mapping):
        raise ValueError(f"Expected Devin session payload dict, got {type(session_payload).__name__}")
    raw = session_payload.get("acus_consumed")
    if raw is None and isinstance(session_payload.get("usage"), Mapping):
        raw = session_payload["usage"].get("acus_consumed")
    if raw is None and isinstance(session_payload.get("session"), Mapping):
        raw = session_payload["session"].get("acus_consumed")
    return pricing.validate_acus_consumed(raw)


def fetch_devin_session_acus(
    devin_id: str,
    org_id: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 15.0,
) -> Optional[float]:
    """Fetch `acus_consumed` from `GET /v3/organizations/{org_id}/sessions/{devin_id}`.

    Reads `DEVIN_ORG_ID`, `DEVIN_API_KEY`, and `DEVIN_API_BASE_URL` from the
    environment when omitted. Returns `None` if the API key is not configured
    or if the session payload omits `acus_consumed`.
    """
    session_id = str(devin_id or "").strip()
    if not session_id:
        raise ValueError("devin_id must be a non-empty string")
    resolved_org = str(org_id or os.environ.get("DEVIN_ORG_ID") or "").strip()
    if not resolved_org:
        raise ValueError("org_id (or DEVIN_ORG_ID) is required to query Devin session telemetry")
    resolved_key = str(api_key or os.environ.get("DEVIN_API_KEY") or "").strip()
    if not resolved_key:
        return None

    api_root = str(base_url or os.environ.get("DEVIN_API_BASE_URL") or DEVIN_API_BASE_URL).rstrip("/")
    url = (
        f"{api_root}/v3/organizations/{urllib.parse.quote(resolved_org, safe='')}"
        f"/sessions/{urllib.parse.quote(session_id, safe='')}"
    )
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {resolved_key}",
            "Accept": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw_body = resp.read().decode("utf-8")
    payload = json.loads(raw_body)
    return extract_acus_consumed(payload)

SENSITIVE_ENV_PATTERNS = ("KEY", "TOKEN", "SECRET", "PASS", "CREDENTIAL", "AUTH")


def sanitize_subprocess_env(base_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Sanitize environment passed to untrusted subprocesses, stripping API keys and secrets (RUN-08)."""
    source = dict(base_env if base_env is not None else os.environ)
    safe_env = {}
    for k, v in source.items():
        k_upper = k.upper()
        if any(pat in k_upper for pat in SENSITIVE_ENV_PATTERNS):
            continue
        safe_env[k] = v
    # Enforce offline invariant flags and prevent bytecode cache pollution
    safe_env["OFFLINE_MODE"] = "1"
    safe_env["AI_LAB_OFFLINE"] = "1"
    safe_env["PYTHONDONTWRITEBYTECODE"] = "1"
    return safe_env


def _safe_rmtree(path: Path) -> None:
    """Remove a directory tree safely, handling read-only permissions on Windows (RUN-03)."""
    if not path.exists():
        return

    def _handle_readonly(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception:
            pass

    try:
        if sys.version_info >= (3, 12):
            def _onexc(func, p, exc):
                _handle_readonly(func, p, None)
            shutil.rmtree(path, onexc=_onexc)
        else:
            shutil.rmtree(path, onerror=_handle_readonly)
    except Exception:
        shutil.rmtree(path, ignore_errors=True)


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class ConfigurationMismatchError(ValueError):
    """Raised when unintentional model or configuration mismatches occur between arms (RUN-04)."""
    pass


class EvaluatorTamperingError(RuntimeError):
    """Raised when an evaluator file's hash does not match its expected hash (RUN-10)."""
    pass


class OfflineModeViolationError(RuntimeError):
    """Raised if any live provider or paid API call is attempted during offline execution (RUN-08)."""
    pass


class NetworkAccessBlockedError(OfflineModeViolationError):
    """Raised when active network/socket access is attempted during offline execution (RUN-08)."""
    pass


class TimeoutRunError(RuntimeError):
    """Raised when a run exceeds its allocated time budget (RUN-06)."""
    pass


class InterruptedRunError(RuntimeError):
    """Raised when an execution is interrupted before completion (RUN-07)."""
    pass


# ---------------------------------------------------------------------------
# Data Models: ArmConfig & RunManifest (RUN-04, RUN-05)
# ---------------------------------------------------------------------------

@dataclass
class ArmConfig:
    """Configuration for a single experimental arm."""
    arm: str
    model: str
    prompt: str
    model_settings: Dict[str, Any] = field(default_factory=lambda: {"temperature": 0.0, "top_p": 1.0})
    governance_instructions: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    subagents: List[str] = field(default_factory=list)
    resource_budget: Dict[str, Any] = field(default_factory=lambda: {
        "timeout_seconds": 600.0,
        "max_cost_usd": 10.0,
        "max_turns": 10,
    })
    evidence_destinations: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArmConfig":
        return cls(
            arm=data["arm"],
            model=data["model"],
            prompt=data["prompt"],
            model_settings=data.get("model_settings", {"temperature": 0.0, "top_p": 1.0}),
            governance_instructions=data.get("governance_instructions"),
            skills=list(data.get("skills") or []),
            subagents=list(data.get("subagents") or []),
            resource_budget=data.get("resource_budget", {"timeout_seconds": 600.0, "max_cost_usd": 10.0, "max_turns": 10}),
            evidence_destinations=data.get("evidence_destinations", {}),
        )


@dataclass
class RunManifest:
    """Execution manifest linking task contract, arm configurations, and evidence destinations."""
    manifest_id: str
    task_id: str
    task_version: str
    created_at: str
    task_contract: Dict[str, Any]
    arms: Dict[str, ArmConfig]
    intentional_governance_diffs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "task_id": self.task_id,
            "task_version": self.task_version,
            "created_at": self.created_at,
            "task_contract": self.task_contract,
            "arms": {k: v.to_dict() for k, v in self.arms.items()},
            "intentional_governance_diffs": self.intentional_governance_diffs,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunManifest":
        arms = {k: ArmConfig.from_dict(v) for k, v in data.get("arms", {}).items()}
        return cls(
            manifest_id=data["manifest_id"],
            task_id=data["task_id"],
            task_version=data.get("task_version", "1.0.0"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            task_contract=data.get("task_contract", {}),
            arms=arms,
            intentional_governance_diffs=data.get("intentional_governance_diffs", {}),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "RunManifest":
        return cls.from_dict(json.loads(json_str))


def validate_manifest_configuration(
    manifest: RunManifest,
    enforce_model_match: bool = True,
) -> Dict[str, Any]:
    """
    Validate run configuration across arms (RUN-04, RUN-05).
    - RUN-04: Unintentional model/config mismatches are rejected or segregated.
    - RUN-05: Intentional governance differences are recorded while keeping task contract shared.
    """
    if not manifest.arms:
        raise ConfigurationMismatchError("Manifest must contain at least one configured arm.")

    # 1. Verify shared task contract
    contract = manifest.task_contract
    if not contract or not contract.get("task_id"):
        raise ConfigurationMismatchError("Manifest must define a shared task_contract with task_id.")

    if contract.get("task_id") != manifest.task_id:
        raise ConfigurationMismatchError(
            f"Task contract ID mismatch: '{contract.get('task_id')}' != manifest task_id '{manifest.task_id}'."
        )

    arms_list = list(manifest.arms.values())
    first_arm = arms_list[0]

    # 2. Model & config matching (RUN-04)
    model_mismatches = []
    settings_mismatches = []
    budget_mismatches = []
    for other_arm in arms_list[1:]:
        if other_arm.model != first_arm.model:
            model_mismatches.append(f"Arm '{first_arm.arm}' ({first_arm.model}) vs Arm '{other_arm.arm}' ({other_arm.model})")
        if other_arm.model_settings != first_arm.model_settings:
            settings_mismatches.append(
                f"Arm '{first_arm.arm}' ({first_arm.model_settings}) vs Arm '{other_arm.arm}' ({other_arm.model_settings})"
            )
        if other_arm.resource_budget != first_arm.resource_budget:
            budget_mismatches.append(
                f"Arm '{first_arm.arm}' ({first_arm.resource_budget}) vs Arm '{other_arm.arm}' ({other_arm.resource_budget})"
            )

    is_segregated = bool(manifest.metadata.get("segregated", False))
    allow_mismatch = bool(
        manifest.metadata.get("allow_model_mismatch", False)
        or manifest.metadata.get("allow_config_mismatch", False)
    )
    has_any_mismatch = bool(model_mismatches or settings_mismatches or budget_mismatches)

    if model_mismatches:
        if not allow_mismatch and not is_segregated and enforce_model_match:
            raise ConfigurationMismatchError(
                f"Unintentional model mismatch rejected to prevent invalid pooling: {'; '.join(model_mismatches)}. "
                f"Set allow_model_mismatch=True or segregated=True if intentional."
            )

    if settings_mismatches and enforce_model_match and not allow_mismatch and not is_segregated:
        raise ConfigurationMismatchError(
            f"Unintentional model_settings mismatch rejected: {'; '.join(settings_mismatches)}. "
            f"Set allow_config_mismatch=True or segregated=True if intentional."
        )

    if budget_mismatches and enforce_model_match and not allow_mismatch and not is_segregated:
        raise ConfigurationMismatchError(
            f"Unintentional resource_budget mismatch rejected: {'; '.join(budget_mismatches)}. "
            f"Set allow_config_mismatch=True or segregated=True if intentional."
        )

    if has_any_mismatch and not is_segregated:
        manifest.metadata["segregated"] = True
        is_segregated = True

    # 3. Governance differences recording (RUN-05)
    gov_diffs: Dict[str, Any] = {}
    for arm_cfg in arms_list:
        gov_diffs[arm_cfg.arm] = {
            "governance_instructions": arm_cfg.governance_instructions,
            "skills": arm_cfg.skills,
            "subagents": arm_cfg.subagents,
            "prompt_has_icm_scaffolding": bool(
                arm_cfg.governance_instructions
                or "ICM" in arm_cfg.prompt
                or "01_intake" in arm_cfg.prompt
                or "Loop-Breaker" in arm_cfg.prompt
                or "Batch-First" in arm_cfg.prompt
            ),
        }

    manifest.intentional_governance_diffs = gov_diffs

    return {
        "valid": True,
        "is_segregated": is_segregated,
        "model": first_arm.model,
        "arms_count": len(manifest.arms),
        "intentional_governance_diffs": gov_diffs,
    }


# ---------------------------------------------------------------------------
# Disposable Workspace Isolation (RUN-01, RUN-02, RUN-03)
# ---------------------------------------------------------------------------

def _hash_directory_tree(root_dir: Path) -> str:
    """Compute SHA-256 over sorted relative file paths and bytes, ignoring transient caches."""
    if not root_dir.exists():
        return ""
    h = hashlib.sha256()
    for p in sorted(root_dir.rglob("*")):
        if not p.is_file():
            continue
        rel_path = p.relative_to(root_dir)
        if "__pycache__" in rel_path.parts or ".pytest_cache" in rel_path.parts or ".git" in rel_path.parts or p.suffix in (".pyc", ".pyo"):
            continue
        h.update(rel_path.as_posix().encode("utf-8"))
        h.update(b"\x00")
        h.update(p.read_bytes())
        h.update(b"\x00")
    return h.hexdigest()


def _tree_files(root_dir: Path) -> Dict[str, Path]:
    """Map relative POSIX paths to files, ignoring transient caches like _hash_directory_tree."""
    files: Dict[str, Path] = {}
    if not root_dir.exists():
        return files
    root_res = root_dir.resolve()
    for p in sorted(root_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root_dir)
        if "__pycache__" in rel.parts or ".pytest_cache" in rel.parts or ".git" in rel.parts or p.suffix in (".pyc", ".pyo"):
            continue
        try:
            p.resolve().relative_to(root_res)
        except (ValueError, OSError, RuntimeError):
            continue
        files[rel.as_posix()] = p
    return files


def _count_changed_lines(before: Path, after: Path) -> int:
    """Count lines added or removed between two versions of a file."""
    try:
        old_lines = before.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        old_lines = []
    try:
        new_lines = after.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        new_lines = []
    return sum(
        1
        for line in difflib.unified_diff(old_lines, new_lines, lineterm="")
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    )


def _count_touched_ast_symbols(old: Optional[Path], new: Optional[Path]) -> int:
    """Count AST symbols actually added, removed, or overlapping changed lines in a diff."""
    if old is None and new is None:
        return 0
    if old is None:
        return count_ast_symbols(new) or 0
    if new is None:
        return count_ast_symbols(old) or 0

    try:
        old_src = old.read_text(encoding="utf-8", errors="replace")
        new_src = new.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0

    old_lines = old_src.splitlines()
    new_lines = new_src.splitlines()
    changed_old: Set[int] = set()
    changed_new: Set[int] = set()
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old_lines, new_lines).get_opcodes():
        if tag in ("replace", "delete"):
            changed_old.update(range(i1 + 1, i2 + 1))
        if tag in ("replace", "insert"):
            changed_new.update(range(j1 + 1, j2 + 1))

    if not changed_old and not changed_new:
        return 0

    old_spans = extract_ast_symbol_spans(old, old_src)
    new_spans = extract_ast_symbol_spans(new, new_src)
    if old_spans is not None and new_spans is not None:
        touched_symbols: Set[str] = set()
        for qname, start, end in old_spans:
            if any(start <= ln <= end for ln in changed_old):
                touched_symbols.add(qname)
        for qname, start, end in new_spans:
            if any(start <= ln <= end for ln in changed_new):
                touched_symbols.add(qname)
        return len(touched_symbols)

    old_count = count_ast_symbols(old) or 0
    new_count = count_ast_symbols(new) or 0
    return abs(new_count - old_count)


def scope_telemetry(workspace_dir: Path, snapshot_dir: Path, metadata: Mapping[str, Any]) -> Dict[str, Any]:
    """Compare a post-run workspace to its snapshot and flag scope drift.

    Returns the files the run actually touched, total added/removed lines, and a
    scope_mismatch flag when the touched set differs from the declared target_files.
    """
    after = _tree_files(workspace_dir)
    before = _tree_files(snapshot_dir)
    touched: Dict[str, Dict[str, Any]] = {}
    for rel in sorted(set(before) | set(after)):
        old = before.get(rel)
        new = after.get(rel)
        if old is not None and new is not None and old.read_bytes() == new.read_bytes():
            continue
        if old is None:
            kind = "added"
        elif new is None:
            kind = "removed"
        else:
            kind = "modified"
        touched[rel] = {"kind": kind, "lines": (len(new.read_text(encoding="utf-8", errors="replace").splitlines()) if old is None else len(old.read_text(encoding="utf-8", errors="replace").splitlines()) if new is None else _count_changed_lines(old, new))}
    declared = metadata.get("target_files")
    declared_set = {
        Path(os.path.normpath(f)).as_posix()
        for f in declared
        if isinstance(f, str) and f.strip()
    } if isinstance(declared, list) else set()
    scope_mismatch = set(touched) != declared_set if declared_set else bool(touched)
    lines_touched = sum(entry["lines"] for entry in touched.values())
    ast_symbols_touched = sum(
        _count_touched_ast_symbols(before.get(rel), after.get(rel))
        for rel in touched
    )

    declared_scope = {
        "target_files": sorted(declared_set),
        "target_files_count": metadata.get("target_files_count", len(declared_set)),
        "estimated_loc": metadata.get("estimated_loc"),
        "target_loc_range": metadata.get("target_loc_range"),
    }
    actual_scope = {
        "files_touched": sorted(touched.keys()),
        "files_touched_count": len(touched),
        "lines_touched": lines_touched,
        "ast_symbols_touched": ast_symbols_touched,
    }
    return {
        "files_touched": touched,
        "lines_touched": lines_touched,
        "declared_files": sorted(declared_set),
        "scope_mismatch": scope_mismatch,
        "declared_scope": declared_scope,
        "actual_scope": actual_scope,
    }


class DisposableWorkspace:
    """
    Isolated disposable workspace directory prepared from a pinned task snapshot.
    Guarantees:
    - Writes inside this workspace do NOT affect other workspaces or the source checkout.
    - Cleanup removes ONLY this disposable directory, never running git clean/checkout on host.
    """
    def __init__(self, path: Path, arm: str, snapshot_dir: Path, run_id: str):
        self.path = path.resolve()
        self.arm = arm
        self.snapshot_dir = snapshot_dir.resolve()
        self.run_id = run_id
        self._is_cleaned = False

    @property
    def backup_dir(self) -> Path:
        """Sibling hidden directory holding the initial pre-run backup."""
        return self.path.parent / f".backup_{self.path.name}"

    def _is_safe_host_target(self) -> bool:
        """Return True iff self.path does not point at host repo files outside tmp/.

        Paths inside the host checkout are only allowed under WORKSPACE_ROOT/"tmp";
        OS-temp disposable workspaces outside WORKSPACE_ROOT are always safe.
        """
        p_res = self.path.resolve()
        ws_res = WORKSPACE_ROOT.resolve()
        tmp_dir = (WORKSPACE_ROOT / "tmp").resolve()
        try:
            p_res.relative_to(tmp_dir)
            return True
        except ValueError:
            pass
        if p_res == ws_res or ws_res in p_res.parents or p_res in ws_res.parents:
            return False
        return True

    def snapshot_tree_hash(self) -> str:
        """Compute deterministic SHA-256 over workspace files, ignoring __pycache__/.pytest_cache."""
        return _hash_directory_tree(self.path)

    def capture_backup(self) -> Path:
        """Copy initial workspace snapshot into sibling hidden .backup_<name> directory."""
        if not self.path.exists():
            raise FileNotFoundError(f"Workspace directory not found: {self.path}")
        if not self._is_safe_host_target():
            raise RuntimeError(f"Refusing to capture backup for unsafe host path: {self.path}")
        bdir = self.backup_dir
        if bdir.exists():
            _safe_rmtree(bdir)
        shutil.copytree(
            self.path,
            bdir,
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc", "*.pyo", ".git"),
            dirs_exist_ok=True,
        )
        return bdir

    def rollback_to_backup(self) -> str:
        """Restore workspace cleanly to exact initial backup files and return restored tree hash."""
        bdir = self.backup_dir
        if not bdir.exists():
            raise FileNotFoundError(f"Backup directory not found for rollback: {bdir}")
        if not self._is_safe_host_target():
            raise RuntimeError(f"Refusing to roll back unsafe host path: {self.path}")

        if self.path.exists():
            for item in list(self.path.iterdir()):
                if item.name == ".git":
                    # Preserve the workspace's isolated git repo across rollback.
                    continue
                if item.is_dir() and not item.is_symlink():
                    _safe_rmtree(item)
                else:
                    try:
                        os.chmod(item, stat.S_IWRITE)
                    except OSError:
                        pass
                    item.unlink()
        else:
            self.path.mkdir(parents=True, exist_ok=True)

        shutil.copytree(
            bdir,
            self.path,
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc", "*.pyo", ".git"),
            dirs_exist_ok=True,
        )
        return self.snapshot_tree_hash()

    def cleanup(self) -> None:
        """Safely destroy this disposable directory without touching any host files (RUN-03)."""
        if self._is_cleaned:
            return

        bdir = self.backup_dir
        p_res = self.path.resolve()
        snap_res = self.snapshot_dir.resolve()

        if not self._is_safe_host_target():
            # Host safety violation: refuse to delete files in host repo outside of tmp/
            return

        if bdir.exists():
            _safe_rmtree(bdir)

        if not self.path.exists():
            self._is_cleaned = True
            return

        if p_res == snap_res or snap_res in p_res.parents or p_res in snap_res.parents:
            # Snapshot safety violation: refuse to delete snapshot directory
            return

        _safe_rmtree(self.path)
        external_marker = self.path.parent / f".ai_lab_marker_{self.path.name}.json"
        if external_marker.exists():
            try:
                external_marker.unlink()
            except OSError:
                pass
        self._is_cleaned = True

    def __enter__(self) -> "DisposableWorkspace":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()


DISPOSABLE_MARKER = ".ai_lab_disposable_workspace"
SAFE_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")


def _validate_identifier(identifier: str, field_name: str) -> None:
    if not identifier or not SAFE_IDENTIFIER_PATTERN.match(identifier):
        raise ValueError(
            f"Invalid {field_name} '{identifier}': must contain only alphanumeric characters, underscores, and hyphens."
        )


# Deterministic identity/timestamps for the isolated workspace snapshot commit.
WORKSPACE_GIT_ENV = {
    "GIT_AUTHOR_NAME": "Ai-Lab",
    "GIT_AUTHOR_EMAIL": "ailab@local",
    "GIT_COMMITTER_NAME": "Ai-Lab",
    "GIT_COMMITTER_EMAIL": "ailab@local",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
    # Block system/global git config from leaking into the isolated repo.
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
}


def _pid_alive(pid: int) -> bool:
    """Return True iff a process with the given pid is currently running."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        # The process exists under another UID.
        return True
    except OSError:
        return False


def _init_workspace_git(ws_dir: Path) -> None:
    """Create an isolated .git repository inside a disposable workspace.

    Runs `git init`, `git add -A`, and `git commit -m "snapshot"` with fixed
    author/committer env vars so the snapshot commit is fully deterministic and
    `git rev-parse --show-toplevel` resolves to the workspace itself.

    Uses subprocess.Popen rather than subprocess.run so harness tests that
    monkeypatch subprocess.run to fake the agent CLI cannot intercept this.
    Inherited GIT_* variables (GIT_DIR, GIT_WORK_TREE, ...) are stripped so a
    caller's environment cannot redirect the snapshot commit into the host repo.
    """
    if shutil.which("git") is None:
        warnings.warn("git executable not found; skipping disposable workspace .git initialization")
        return
    git_env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    git_env.update(WORKSPACE_GIT_ENV)
    # Never fall back to a repository above the workspace's parent dir.
    git_env["GIT_CEILING_DIRECTORIES"] = str(ws_dir.parent)
    for cmd in (
        ["git", "init"],
        ["git", "add", "-A"],
        ["git", "commit", "--allow-empty", "-m", "snapshot"],
    ):
        proc = subprocess.Popen(
            cmd,
            cwd=str(ws_dir),
            env=git_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _, err = proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"git initialization failed in workspace '{ws_dir}' "
                f"({' '.join(cmd)}): {err.decode('utf-8', errors='replace').strip()}"
            )


class WorkspaceManager:
    """Manages creation and cleanup of disposable workspaces."""

    @staticmethod
    def prepare_arm_workspace(
        snapshot_dir: Path,
        arm: str,
        workspace_root: Optional[Path] = None,
        run_id: Optional[str] = None,
        init_git: bool = True,
        canonical_workspace: bool = False,
        task_id: Optional[str] = None,
    ) -> DisposableWorkspace:
        """
        Prepare an isolated disposable workspace directory from a pinned task snapshot (RUN-01, RUN-03).
        Preserves user uncommitted files and repository state completely.
        Validates identifiers, enforces path containment within workspace root, and verifies ownership.

        When workspace_root is None the workspace is placed under the OS temp
        directory (or AI_LAB_WORKSPACE_ROOT), never inside the host checkout, so
        agent CLIs cannot inherit the host AGENTS.md or host .git repository.
        With init_git=True (default) the workspace receives its own isolated
        .git repository containing a deterministic "snapshot" commit.
        With canonical_workspace=True the directory name is deterministic per
        (task_id, arm) instead of the volatile PID/timestamp run_id.
        """
        if not snapshot_dir.exists():
            raise FileNotFoundError(f"Snapshot directory not found: {snapshot_dir}")

        if not run_id:
            run_id = f"run_{int(time.time() * 1000)}"

        _validate_identifier(run_id, "run_id")
        _validate_identifier(arm, "arm")

        if workspace_root is None:
            base_temp = Path(
                os.environ.get("AI_LAB_WORKSPACE_ROOT")
                or (Path(tempfile.gettempdir()) / "ai_lab_disposable_workspaces")
            ).resolve()
        else:
            base_temp = Path(workspace_root).resolve()

        canonical_label: Optional[str] = None
        if canonical_workspace:
            if task_id is not None:
                _validate_identifier(task_id, "task_id")
            canonical_label = re.sub(
                r"[^a-zA-Z0-9_-]", "-", task_id or snapshot_dir.parent.name
            )
            _validate_identifier(canonical_label, "task_id")

        ws_name = f"{canonical_label}_{arm}" if canonical_workspace else f"{run_id}_{arm}"
        ws_dir = (base_temp / ws_name).resolve()

        # Enforce strict path containment within base_temp (pure path math — no
        # disk state yet, so rejected paths never create directories).
        try:
            ws_dir.relative_to(base_temp)
        except ValueError:
            raise ValueError(
                f"Path containment violation: workspace directory '{ws_dir}' escapes root '{base_temp}'"
            )

        # A workspace inside the host checkout is only usable under tmp/: anywhere
        # else makes _is_safe_host_target() reject backups and skip cleanup.
        ws_res = WORKSPACE_ROOT.resolve()
        if ws_dir == ws_res or ws_res in ws_dir.parents:
            tmp_dir = (WORKSPACE_ROOT / "tmp").resolve()
            try:
                ws_dir.relative_to(tmp_dir)
                warnings.warn(
                    f"Workspace '{ws_dir}' is inside the host checkout under tmp/: "
                    "host AGENTS.md and .git remain reachable to agent CLIs."
                )
            except ValueError:
                raise ValueError(
                    f"Workspace directory '{ws_dir}' lies inside the host checkout "
                    f"outside '{tmp_dir}': backup and cleanup would refuse it."
                )

        if not base_temp.exists():
            base_temp.mkdir(parents=True, mode=0o700)
        # A workspace root other local accounts can control is untrusted: they
        # could substitute the tree the evaluator grades.
        base_stat = base_temp.stat()
        if hasattr(os, "getuid") and base_stat.st_uid != os.getuid():
            raise RuntimeError(
                f"Refusing to use workspace root '{base_temp}': owned by another local account."
            )
        if os.name == "posix" and stat.S_IMODE(base_stat.st_mode) & 0o022:
            raise RuntimeError(
                f"Refusing to use workspace root '{base_temp}': writable by group/other local accounts."
            )

        if ws_dir == base_temp:
            raise ValueError(f"Workspace path cannot be the root directory '{base_temp}'")

        # Refuse to delete existing directory unless ownership is established
        if ws_dir.exists():
            external_marker = base_temp / f".ai_lab_marker_{ws_dir.name}.json"
            internal_marker = ws_dir / DISPOSABLE_MARKER
            marker = external_marker if external_marker.exists() else (internal_marker if internal_marker.exists() else None)
            if not marker:
                raise RuntimeError(
                    f"Refusing to delete existing directory '{ws_dir}': missing ownership marker."
                )
            try:
                marker_data = json.loads(marker.read_text(encoding="utf-8"))
                if marker_data.get("arm") != arm:
                    raise RuntimeError(
                        f"Refusing to delete existing directory '{ws_dir}': marker ownership mismatch."
                    )
                if canonical_workspace:
                    if marker_data.get("task_id") != canonical_label:
                        raise RuntimeError(
                            f"Refusing to delete existing directory '{ws_dir}': marker ownership mismatch."
                        )
                    # A canonical dir may be reused across runs, but never while
                    # the run that created it is still alive on this host.
                    owner_pid = marker_data.get("pid")
                    if (
                        isinstance(owner_pid, int)
                        and marker_data.get("host") == socket.gethostname()
                        and _pid_alive(owner_pid)
                    ):
                        raise RuntimeError(
                            f"Refusing to delete existing directory '{ws_dir}': "
                            f"canonical workspace still in use by live run (pid={owner_pid})."
                        )
                elif marker_data.get("run_id") != run_id:
                    raise RuntimeError(
                        f"Refusing to delete existing directory '{ws_dir}': marker ownership mismatch."
                    )
            except Exception as exc:
                if isinstance(exc, RuntimeError):
                    raise
                raise RuntimeError(
                    f"Refusing to delete existing directory '{ws_dir}': invalid marker ({exc})."
                )
            _safe_rmtree(ws_dir)
            if external_marker.exists():
                try:
                    external_marker.unlink()
                except OSError:
                    pass

        # Copy snapshot into disposable workspace
        shutil.copytree(snapshot_dir, ws_dir, dirs_exist_ok=True)

        # Write external ownership marker file (stored outside ws_dir to preserve snapshot files)
        external_marker = base_temp / f".ai_lab_marker_{ws_dir.name}.json"
        marker_payload = {
            "run_id": run_id,
            "arm": arm,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "disposable": True,
            "pid": os.getpid(),
            "host": socket.gethostname(),
        }
        if canonical_workspace:
            marker_payload["task_id"] = canonical_label
        external_marker.write_text(json.dumps(marker_payload), encoding="utf-8")

        if init_git and not (ws_dir / ".git").exists():
            _init_workspace_git(ws_dir)

        return DisposableWorkspace(
            path=ws_dir,
            arm=arm,
            snapshot_dir=snapshot_dir,
            run_id=run_id,
        )

    @staticmethod
    def prepare_two_arms(
        snapshot_dir: Path,
        workspace_root: Optional[Path] = None,
        run_id: Optional[str] = None,
    ) -> Tuple[DisposableWorkspace, DisposableWorkspace]:
        """
        Prepare two arms from the same snapshot with identical starting states and
        separate writable directories (RUN-01).
        """
        if not run_id:
            run_id = f"run_{int(time.time() * 1000)}"

        ws_a = WorkspaceManager.prepare_arm_workspace(
            snapshot_dir=snapshot_dir,
            arm="baseline",
            workspace_root=workspace_root,
            run_id=run_id,
        )
        ws_b = WorkspaceManager.prepare_arm_workspace(
            snapshot_dir=snapshot_dir,
            arm="icm",
            workspace_root=workspace_root,
            run_id=run_id,
        )
        return ws_a, ws_b


# ---------------------------------------------------------------------------
# Protected Evaluators & Hash Verification (RUN-09, RUN-10)
# ---------------------------------------------------------------------------

@dataclass
class VerificationResult:
    """Outcome of grading by a protected evaluator."""
    verification_status: str  # 'passed', 'failed', 'evaluator_error', 'not_run'
    passed: bool
    reasons: List[str] = field(default_factory=list)
    evaluator_hash: Optional[str] = None
    output: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class ProtectedEvaluator:
    """
    Evaluator stored strictly outside the writable agent workspace (RUN-09).
    Verifies SHA-256 integrity hash before grading to detect tampering (RUN-10).
    Note: Storing evaluators outside the workspace directory provides organizational
    separation and tamper detection via SHA-256 verification, but does not provide
    OS-level filesystem sandboxing if an agent process has broad host filesystem access.
    """
    def __init__(
        self,
        evaluator_path: Path,
        expected_hash: Optional[str] = None,
        test_callable: Optional[Callable[[Path], Tuple[bool, str]]] = None,
    ):
        self.evaluator_path = evaluator_path.resolve()
        self.expected_hash = expected_hash
        self.test_callable = test_callable

        if not self.evaluator_path.exists():
            raise FileNotFoundError(f"Protected evaluator file not found: {self.evaluator_path}")

        if self.expected_hash is None:
            self.expected_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of the evaluator file or directory."""
        if not self.evaluator_path.exists():
            return ""
        if self.evaluator_path.is_file():
            return hashlib.sha256(self.evaluator_path.read_bytes()).hexdigest()

        # If directory, compute hash of all sorted files, ignoring transient cache files
        h = hashlib.sha256()
        for p in sorted(self.evaluator_path.rglob("*")):
            if p.is_file():
                parts = p.parts
                if "__pycache__" in parts or ".pytest_cache" in parts or p.suffix in (".pyc", ".pyo"):
                    continue
                rel = p.relative_to(self.evaluator_path).as_posix().encode("utf-8")
                h.update(rel)
                h.update(p.read_bytes())
        return h.hexdigest()

    def verify_hash(self) -> Tuple[bool, str]:
        """Verify actual hash against expected hash (RUN-10)."""
        actual = self.compute_hash()
        is_valid = (actual.lower() == (self.expected_hash or "").lower())
        return is_valid, actual

    def evaluate_workspace(self, workspace_path: Path) -> VerificationResult:
        """
        Evaluate agent submission in workspace_path using protected evaluator checks.
        Workspace modifications to test files have no effect on grading (RUN-09).
        Tampering with evaluator fails verification with evaluator_error (RUN-10).
        """
        # 1. Tamper detection (RUN-10)
        is_valid, actual_hash = self.verify_hash()
        if not is_valid:
            return VerificationResult(
                verification_status="evaluator_error",
                passed=False,
                reasons=["evaluator_hash_mismatch", "evaluator_tampered"],
                evaluator_hash=actual_hash,
                output=f"Evaluator hash mismatch: expected {self.expected_hash}, got {actual_hash}",
            )

        # 2. Execution of protected checks (RUN-09)
        # If custom callable supplied:
        if self.test_callable is not None:
            try:
                passed, out = self.test_callable(workspace_path)
                status = "passed" if passed else "failed"
                reasons = [] if passed else ["test_assertion_failed"]
                return VerificationResult(
                    verification_status=status,
                    passed=passed,
                    reasons=reasons,
                    evaluator_hash=actual_hash,
                    output=out,
                )
            except Exception as exc:
                return VerificationResult(
                    verification_status="evaluator_error",
                    passed=False,
                    reasons=[f"evaluator_execution_exception: {exc}"],
                    evaluator_hash=actual_hash,
                    output=str(exc),
                )

        # Execution of protected checks via Python subprocess (RUN-08, RUN-09)
        env = sanitize_subprocess_env(os.environ)
        env["PYTHONPATH"] = str(workspace_path) + os.pathsep + env.get("PYTHONPATH", "")

        cmd = None
        if self.evaluator_path.is_file() and self.evaluator_path.suffix == ".py":
            cmd = [sys.executable, str(self.evaluator_path)]
        elif self.evaluator_path.is_dir():
            eval_py = self.evaluator_path / "evaluator.py"
            if eval_py.exists():
                cmd = [sys.executable, str(eval_py)]
            else:
                cmd = [sys.executable, "-m", "pytest", str(self.evaluator_path)]

        if cmd is not None:
            try:
                res = subprocess.run(
                    cmd,
                    cwd=str(workspace_path),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=45,
                    check=False,
                )

                # Re-verify hash after execution to detect runtime tampering (RUN-10)
                is_valid_post, post_hash = self.verify_hash()
                if not is_valid_post:
                    return VerificationResult(
                        verification_status="evaluator_error",
                        passed=False,
                        reasons=["evaluator_hash_mismatch", "evaluator_tampered_during_execution"],
                        evaluator_hash=post_hash,
                        output=f"Evaluator tampering detected during execution! Expected hash {self.expected_hash}, got {post_hash}",
                    )

                passed = (res.returncode == 0)
                status = "passed" if passed else "failed"
                reasons = [] if passed else ["test_failure"]
                out = res.stdout + ("\n" + res.stderr if res.stderr else "")
                if not passed:
                    for line in out.splitlines():
                        line_s = line.strip()
                        if line_s.startswith("REASON:"):
                            r_val = line_s.split("REASON:", 1)[1].strip()
                            if r_val and r_val not in reasons:
                                reasons.append(r_val)
                return VerificationResult(
                    verification_status=status,
                    passed=passed,
                    reasons=reasons,
                    evaluator_hash=actual_hash,
                    output=out.strip(),
                )
            except subprocess.TimeoutExpired:
                return VerificationResult(
                    verification_status="failed",
                    passed=False,
                    reasons=["evaluator_timeout"],
                    evaluator_hash=actual_hash,
                    output="Protected evaluator timed out during execution.",
                )
            except Exception as exc:
                return VerificationResult(
                    verification_status="evaluator_error",
                    passed=False,
                    reasons=[f"evaluator_runner_error: {exc}"],
                    evaluator_hash=actual_hash,
                    output=str(exc),
                )

        return VerificationResult(
            verification_status="not_run",
            passed=False,
            reasons=["no_supported_evaluator_strategy"],
            evaluator_hash=actual_hash,
        )


# ---------------------------------------------------------------------------
# Offline & Fixture Execution Adapter (RUN-08)
# ---------------------------------------------------------------------------

@dataclass
class ExecutionResult:
    """Outcome of an arm execution step."""
    execution_status: str  # 'completed', 'timed_out', 'interrupted', 'failed'
    duration_seconds: float
    num_turns: int
    usage: Optional[Dict[str, Any]] = None
    partial_events: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    evidence_ref: Optional[str] = None
    evidence_hash: Optional[str] = None


@contextmanager
def block_network():
    """
    Context manager that intercepts socket creation/connection attempts to prevent
    accidental network calls during offline execution.
    Note: This provides Python process-level socket interception to guard against outbound
    network calls, but does not provide OS-level container sandboxing.
    """
    orig_connect = socket.socket.connect
    orig_create_connection = socket.create_connection

    def _blocked_connect(self, *args, **kwargs):
        raise NetworkAccessBlockedError(
            f"Network access is blocked in offline mode: socket.connect attempted with args {args}"
        )

    def _blocked_create_connection(*args, **kwargs):
        raise NetworkAccessBlockedError(
            f"Network access is blocked in offline mode: socket.create_connection attempted with args {args}"
        )

    socket.socket.connect = _blocked_connect
    socket.create_connection = _blocked_create_connection
    try:
        yield
    finally:
        socket.socket.connect = orig_connect
        socket.create_connection = orig_create_connection


class OfflineExecutionAdapter:
    """
    Offline execution workflow asserting zero provider or paid API invocations (RUN-08).
    Replays fixture telemetry streams and provides process-level socket interception to guard
    against outbound network calls (note: does not provide OS-level container sandboxing).
    """
    def __init__(self, fixtures_path: Optional[Path] = None):
        self.fixtures_path = fixtures_path or DEFAULT_FIXTURES_PATH
        self.provider_invocations_count = 0
        self.paid_api_calls_count = 0

    def assert_zero_provider_calls(self) -> None:
        """Assert zero provider or paid API invocations (RUN-08)."""
        if self.provider_invocations_count > 0 or self.paid_api_calls_count > 0:
            raise OfflineModeViolationError(
                f"Offline invariant violated: {self.provider_invocations_count} provider calls, "
                f"{self.paid_api_calls_count} paid calls recorded."
            )

    def execute_mock(
        self,
        task_id: str,
        arm: str,
        run_index: int = 1,
        simulate_timeout: bool = False,
        simulate_interruption: bool = False,
        simulate_failure: bool = False,
        timeout_seconds: float = 600.0,
    ) -> ExecutionResult:
        """
        Execute offline run by replaying mock fixtures without any external network calls (RUN-08).
        Supports simulated timeout (RUN-06), simulated interruption (RUN-07), and simulated failure.
        """
        with block_network():
            # Enforce zero live calls
            self.assert_zero_provider_calls()

            if simulate_timeout:
                return ExecutionResult(
                    execution_status="timed_out",
                    duration_seconds=timeout_seconds,
                    num_turns=1,
                    usage={"input_tokens": 1500, "output_tokens": 200, "thinking_tokens": 0, "cache_read_tokens": 500, "total_tokens": 2200},
                    partial_events=['{"event": "start"}', '{"event": "turn_1", "usage": {"input_tokens": 1500, "output_tokens": 200}}'],
                    error_message="Simulated run timeout exceeded.",
                )

            if simulate_interruption:
                return ExecutionResult(
                    execution_status="interrupted",
                    duration_seconds=2.5,
                    num_turns=1,
                    usage={"input_tokens": 1000, "output_tokens": 100, "thinking_tokens": 0, "cache_read_tokens": 200, "total_tokens": 1300},
                    partial_events=['{"event": "start"}', '{"event": "interrupted"}'],
                    error_message="Simulated execution interrupted.",
                )

            if simulate_failure:
                return ExecutionResult(
                    execution_status="failed",
                    duration_seconds=1.0,
                    num_turns=1,
                    usage={"input_tokens": 500, "output_tokens": 50, "thinking_tokens": 0, "cache_read_tokens": 0, "total_tokens": 550},
                    partial_events=['{"event": "start"}', '{"event": "error", "message": "Simulated agent process failure."}'],
                    error_message="Simulated agent process failure.",
                )

            # Standard replay from fixtures
            if self.fixtures_path.exists():
                lines = self.fixtures_path.read_text(encoding="utf-8").splitlines()
                events = []
                for l in lines:
                    l_str = l.strip()
                    if not l_str:
                        continue
                    try:
                        ev = json.loads(l_str)
                        if ev.get("task_id") == task_id and ev.get("arm") == arm and ev.get("run_index", 1) == run_index:
                            events.append(l_str)
                    except Exception:
                        continue

                if events:
                    parsed = ledger.validate_and_parse_telemetry(events)
                    return ExecutionResult(
                        execution_status="completed",
                        duration_seconds=parsed["duration_seconds"],
                        num_turns=parsed["num_turns"],
                        usage=parsed["usage"],
                        partial_events=events,
                        evidence_ref=self.fixtures_path.name,
                    )

            # Default synthetic fixture event if task not in mock_stream
            default_events = [
                json.dumps({"event": "start", "task_id": task_id, "arm": arm, "run_index": run_index}),
                json.dumps({
                    "event": "run_complete",
                    "task_id": task_id,
                    "arm": arm,
                    "run_index": run_index,
                    "usage": {"input_tokens": 25000, "output_tokens": 1200, "thinking_tokens": 100, "cache_read_tokens": 5000, "total_tokens": 31300},
                    "num_turns": 3,
                    "duration_seconds": 12.0,
                }),
            ]
            parsed = ledger.validate_and_parse_telemetry(default_events)
            return ExecutionResult(
                execution_status="completed",
                duration_seconds=parsed["duration_seconds"],
                num_turns=parsed["num_turns"],
                usage=parsed["usage"],
                partial_events=default_events,
                evidence_ref="synthetic_fixture",
            )


# ---------------------------------------------------------------------------
# Manual Preparation & Import Adapter (RUN-11)
# ---------------------------------------------------------------------------

class ManualExecutionAdapter:
    """
    Adapter for manual run preparation, completion recording, and evidence import.
    Handles situations where external automation is unavailable or telemetry is absent (RUN-11).
    """

    @staticmethod
    def prepare_manual_package(
        manifest: RunManifest,
        arm: str,
        export_dir: Path,
    ) -> Path:
        """Export workspace files, prompts, and run manifest for manual execution."""
        export_dir.mkdir(parents=True, exist_ok=True)
        arm_cfg = manifest.arms[arm]

        # Write manifest
        manifest_file = export_dir / "manifest.json"
        manifest_file.write_text(manifest.to_json(), encoding="utf-8")

        # Write instructions
        instructions_file = export_dir / "INSTRUCTIONS.md"
        instructions = f"""# Manual Execution Package
- **Manifest ID:** {manifest.manifest_id}
- **Task ID:** {manifest.task_id} (Version: {manifest.task_version})
- **Arm:** {arm.upper()}
- **Model:** {arm_cfg.model}

## Task Prompt:
{arm_cfg.prompt}

## Governance Instructions:
{arm_cfg.governance_instructions or "None"}
"""
        instructions_file.write_text(instructions, encoding="utf-8")
        return export_dir

    @staticmethod
    def record_manual_completion(
        task_id: str,
        arm: str,
        run_index: int,
        workspace_path: Path,
        evaluator: ProtectedEvaluator,
        telemetry_stream: Optional[List[str]] = None,
        model: Optional[str] = None,
        manifest_id: Optional[str] = None,
        acus_consumed: Optional[float] = None,
        db_path: Optional[Path] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Dict[str, Any]:
        """
        Record manual completion in ledger.
        RUN-11: When manual adapter lacks usage telemetry, correctness is still
        evaluated and recorded while usage counters remain None and cost remains unavailable.
        """
        # 1. Evaluate correctness using protected evaluator
        verif = evaluator.evaluate_workspace(workspace_path)

        # 2. Parse telemetry if supplied, otherwise usage and cost are unavailable
        exclusion_reasons = []
        resolved_acus = pricing.validate_acus_consumed(acus_consumed)
        if telemetry_stream:
            parsed = ledger.validate_and_parse_telemetry(telemetry_stream)
            u = parsed["usage"]
            num_turns = parsed["num_turns"]
            duration = parsed["duration_seconds"]
            if resolved_acus is None:
                resolved_acus = parsed.get("acus_consumed")
            cost_status = None
        else:
            # RUN-11: Lacks usage telemetry -> None (unknown), cost unavailable
            u = {
                "input_tokens": None,
                "output_tokens": None,
                "thinking_tokens": None,
                "cache_read_tokens": None,
                "total_tokens": None,
            }
            num_turns = 1
            duration = 0.0
            cost_status = "unavailable"
            exclusion_reasons.append("missing_usage_telemetry")

        if verif.reasons:
            for r in verif.reasons:
                if r not in exclusion_reasons:
                    exclusion_reasons.append(r)
        if verif.verification_status == "evaluator_error" and "evaluator_error" not in exclusion_reasons:
            exclusion_reasons.append("evaluator_error")

        run_id = ledger.record_run(
            task_id=task_id,
            arm=arm,
            model=model or "manual-agent",
            run_index=run_index,
            timestamp=datetime.now(timezone.utc).isoformat(),
            input_tokens=u["input_tokens"],
            output_tokens=u["output_tokens"],
            thinking_tokens=u.get("thinking_tokens"),
            cache_read_tokens=u.get("cache_read_tokens"),
            total_tokens=u["total_tokens"],
            num_turns=num_turns,
            duration_seconds=duration,
            source_kind="imported",
            evidence_status="unverified" if not telemetry_stream else "verified",
            exclusion_reasons=exclusion_reasons,
            cost_status=cost_status,
            acus_consumed=resolved_acus,
            execution_status="completed",
            verification_status=verif.verification_status,
            manifest_id=manifest_id,
            evaluator_hash=verif.evaluator_hash,
            db_path=db_path,
            conn=conn,
        )

        return {
            "run_id": run_id,
            "verification": verif,
            "usage": u,
            "has_usage_telemetry": u["input_tokens"] is not None,
            "cost_status": cost_status,
        }


# ---------------------------------------------------------------------------
# Lifecycle Execution & Interruption/Resume Protocol (RUN-06, RUN-07)
# ---------------------------------------------------------------------------

def _persist_run_lifecycle_events(
    conn: sqlite3.Connection,
    run_id: int,
    pre_hash: Optional[str],
    post_hash: Optional[str],
    verif_status: str,
    tool_events: List[Dict[str, Any]],
    rolled_back: bool,
    restored_hash: Optional[str],
    start_ts: Optional[str] = None,
    scope: Optional[Dict[str, Any]] = None,
    context_reset: Optional[Dict[str, Any]] = None,
    phase1_tool_count: Optional[int] = None,
) -> None:
    """Persist start, tool transitions, context_reset, verify, scope telemetry, and rollback events to SQLite."""
    seq = 1
    ledger.record_run_event(
        run_id=run_id,
        seq=seq,
        phase="start",
        status="started",
        diff_hash=pre_hash,
        timestamp=start_ts,
        conn=conn,
    )
    split_idx = (
        len(tool_events)
        if context_reset is None or phase1_tool_count is None
        else max(0, min(int(phase1_tool_count), len(tool_events)))
    )
    for ev in tool_events[:split_idx]:
        seq += 1
        ledger.record_run_event(
            run_id=run_id,
            seq=seq,
            phase=str(ev.get("phase") or "tool"),
            status=str(ev.get("status") or "DONE"),
            tool_name=ev.get("tool_name"),
            target_path=ev.get("target_path"),
            conn=conn,
        )
    if context_reset is not None:
        seq += 1
        ledger.record_run_event(
            run_id=run_id,
            seq=seq,
            phase="context_reset",
            status=str(context_reset.get("status") or "DONE"),
            tool_name=str(context_reset.get("tool_name") or "context_reset"),
            target_path=context_reset.get("target_path"),
            diff_hash=context_reset.get("diff_hash"),
            rollback_ref=context_reset.get("rollback_ref"),
            conn=conn,
        )
    for ev in tool_events[split_idx:]:
        seq += 1
        ledger.record_run_event(
            run_id=run_id,
            seq=seq,
            phase=str(ev.get("phase") or "tool"),
            status=str(ev.get("status") or "DONE"),
            tool_name=ev.get("tool_name"),
            target_path=ev.get("target_path"),
            conn=conn,
        )
    if verif_status != "not_run":
        seq += 1
        ledger.record_run_event(
            run_id=run_id,
            seq=seq,
            phase="verify",
            status=verif_status,
            diff_hash=post_hash,
            conn=conn,
        )
    if scope is not None:
        seq += 1
        ledger.record_run_event(
            run_id=run_id,
            seq=seq,
            phase="scope",
            status="scope_mismatch" if scope.get("scope_mismatch") else "scope_ok",
            target_path=json.dumps(
                {
                    "files_touched": scope.get("files_touched"),
                    "lines_touched": scope.get("lines_touched"),
                    "declared_files": scope.get("declared_files"),
                    "loc_source": scope.get("loc_source"),
                    "declared_scope": scope.get("declared_scope"),
                    "actual_scope": scope.get("actual_scope"),
                }
            ),
            conn=conn,
        )
    if rolled_back:
        seq += 1
        ledger.record_run_event(
            run_id=run_id,
            seq=seq,
            phase="rollback",
            status="rolled_back",
            diff_hash=restored_hash,
            rollback_ref=pre_hash,
            conn=conn,
        )


def execute_run_with_lifecycle(
    manifest: RunManifest,
    arm: str,
    workspace: DisposableWorkspace,
    evaluator: Optional[ProtectedEvaluator] = None,
    adapter: Optional[OfflineExecutionAdapter] = None,
    run_index: int = 1,
    timeout_seconds: Optional[float] = None,
    simulate_timeout: bool = False,
    simulate_interruption: bool = False,
    simulate_failure: bool = False,
    db_path: Optional[Path] = None,
    conn: Optional[sqlite3.Connection] = None,
    rollback_on_failure: bool = True,
) -> Dict[str, Any]:
    """
    Execute an arm run with lifecycle tracking:
    - RUN-06: Simulate timeout -> Timed-out attempt retained with partial evidence.
    - RUN-07: Simulate interruption -> Preserves original attempt without invented completion.
    - Captures pre-run snapshot hash & backup, records run_events, and rolls back on failure.
    """
    arm_cfg = manifest.arms[arm]
    model = arm_cfg.model
    if timeout_seconds is None:
        timeout_seconds = float(arm_cfg.resource_budget.get("timeout_seconds", 600.0))

    if adapter is None:
        adapter = OfflineExecutionAdapter()

    start_ts = datetime.now(timezone.utc).isoformat()
    can_snapshot = workspace.path.exists() and workspace._is_safe_host_target()
    pre_hash: Optional[str] = None
    if can_snapshot:
        if not workspace.backup_dir.exists():
            workspace.capture_backup()
        pre_hash = _hash_directory_tree(workspace.backup_dir)

    # Execute step via adapter
    exec_res = adapter.execute_mock(
        task_id=manifest.task_id,
        arm=arm,
        run_index=run_index,
        simulate_timeout=simulate_timeout,
        simulate_interruption=simulate_interruption,
        simulate_failure=simulate_failure,
        timeout_seconds=timeout_seconds,
    )

    post_hash: Optional[str] = workspace.snapshot_tree_hash() if can_snapshot else None
    tool_metrics = (
        ledger.extract_ndjson_tool_metrics(exec_res.partial_events)
        if exec_res.partial_events
        else {"tool_calls_count": None, "tool_errors_count": None, "max_consecutive_tool_streak": None, "loop_detected": None, "events": []}
    )

    exclusion_reasons: List[str] = []
    if exec_res.execution_status == "timed_out":
        exclusion_reasons.extend(["timeout", "partial_telemetry"])
    elif exec_res.execution_status == "interrupted":
        exclusion_reasons.append("interrupted_attempt")
    elif exec_res.execution_status == "failed":
        exclusion_reasons.append("execution_failed")

    # Verification step & tamper check (RUN-09, RUN-10)
    verif = None
    if evaluator:
        is_valid, actual_hash = evaluator.verify_hash()
        ev_hash = actual_hash
        if not is_valid:
            verif_status = "evaluator_error"
            for r in ["evaluator_hash_mismatch", "evaluator_tampered", "evaluator_error"]:
                if r not in exclusion_reasons:
                    exclusion_reasons.append(r)
            verif = VerificationResult(
                verification_status="evaluator_error",
                passed=False,
                reasons=["evaluator_hash_mismatch", "evaluator_tampered"],
                evaluator_hash=actual_hash,
                output=f"Evaluator hash mismatch: expected {evaluator.expected_hash}, got {actual_hash}",
            )
        elif exec_res.execution_status == "completed":
            verif = evaluator.evaluate_workspace(workspace.path)
            verif_status = verif.verification_status
            ev_hash = verif.evaluator_hash
            if verif.reasons:
                for r in verif.reasons:
                    if r not in exclusion_reasons:
                        exclusion_reasons.append(r)
        else:
            verif_status = "not_run"
    else:
        verif_status = "not_run"
        ev_hash = None

    rolled_back = False
    restored_hash: Optional[str] = None
    if (
        verif_status in ("failed", "evaluator_error")
        and rollback_on_failure
        and can_snapshot
        and workspace.backup_dir.exists()
    ):
        restored_hash = workspace.rollback_to_backup()
        rolled_back = True

    u = exec_res.usage or {
        "input_tokens": None,
        "output_tokens": None,
        "thinking_tokens": None,
        "cache_read_tokens": None,
        "total_tokens": None,
    }

    has_tool_events = bool(tool_metrics["events"])
    should_close = False
    active_conn = conn
    if active_conn is None:
        active_conn = ledger.get_connection(db_path)
        should_close = True

    try:
        run_id = ledger.record_run(
            task_id=manifest.task_id,
            arm=arm,
            model=model,
            run_index=run_index,
            timestamp=datetime.now(timezone.utc).isoformat(),
            input_tokens=u["input_tokens"],
            output_tokens=u["output_tokens"],
            thinking_tokens=u.get("thinking_tokens"),
            cache_read_tokens=u.get("cache_read_tokens"),
            total_tokens=u["total_tokens"],
            num_turns=exec_res.num_turns,
            duration_seconds=exec_res.duration_seconds,
            source_kind="fixture",
            evidence_status="unverified",
            exclusion_reasons=exclusion_reasons,
            evidence_ref=exec_res.evidence_ref,
            execution_status=exec_res.execution_status,
            verification_status=verif_status,
            manifest_id=manifest.manifest_id,
            evaluator_hash=ev_hash,
            tool_calls_count=tool_metrics["tool_calls_count"] if has_tool_events else None,
            tool_errors_count=tool_metrics["tool_errors_count"] if has_tool_events else None,
            max_consecutive_tool_streak=tool_metrics["max_consecutive_tool_streak"] if has_tool_events else None,
            loop_detected=tool_metrics["loop_detected"] if has_tool_events else None,
            db_path=db_path,
            conn=active_conn,
        )

        _persist_run_lifecycle_events(
            conn=active_conn,
            run_id=run_id,
            pre_hash=pre_hash,
            post_hash=post_hash,
            verif_status=verif_status,
            tool_events=tool_metrics["events"],
            rolled_back=rolled_back,
            restored_hash=restored_hash,
            start_ts=start_ts,
        )
    finally:
        if should_close:
            active_conn.close()

    return {
        "run_id": run_id,
        "execution": exec_res,
        "verification": verif,
        "execution_status": exec_res.execution_status,
        "verification_status": verif_status,
        "pre_hash": pre_hash,
        "post_hash": post_hash,
        "restored_hash": restored_hash,
        "rolled_back": rolled_back,
    }


def resume_interrupted_run(
    task_id: str,
    arm: str,
    original_run_index: int,
    manifest: RunManifest,
    workspace: DisposableWorkspace,
    evaluator: Optional[ProtectedEvaluator] = None,
    adapter: Optional[OfflineExecutionAdapter] = None,
    db_path: Optional[Path] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Resume an interrupted execution (RUN-07).
    Guarantees:
    - Original interrupted attempt is preserved intact in ledger.
    - No invented completion or duplicate run index overwrite.
    - Resumed run is recorded under a fresh run index (max_run_index + 1).
    """
    should_close = False
    if conn is None:
        conn = ledger.get_connection(db_path)
        should_close = True

    try:
        # 1. Assert original interrupted attempt exists in ledger
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM runs WHERE task_id = ? AND arm = ? AND run_index = ?",
            (task_id, arm, original_run_index),
        )
        orig_row = cursor.fetchone()
        if not orig_row:
            raise RuntimeError(f"Cannot resume: original run attempt {original_run_index} not found.")

        orig_dict = dict(orig_row)
        if orig_dict.get("execution_status") != "interrupted":
            raise RuntimeError(
                f"Cannot resume run {original_run_index}: status is '{orig_dict.get('execution_status')}', not 'interrupted'."
            )

        # 2. Schedule new attempt with incremented run_index to preserve original record
        cursor.execute(
            "SELECT MAX(run_index) FROM runs WHERE task_id = ? AND arm = ?",
            (task_id, arm),
        )
        max_idx = cursor.fetchone()[0]
        next_run_index = (max_idx or original_run_index) + 1
        resumed_res = execute_run_with_lifecycle(
            manifest=manifest,
            arm=arm,
            workspace=workspace,
            evaluator=evaluator,
            adapter=adapter,
            run_index=next_run_index,
            simulate_timeout=False,
            simulate_interruption=False,
            conn=conn,
        )

        # 3. Assert original row was not modified
        cursor.execute(
            "SELECT execution_status FROM runs WHERE id = ?",
            (orig_dict["id"],),
        )
        assert cursor.fetchone()[0] == "interrupted", "Original interrupted run status was corrupted!"

        return {
            "original_run_id": orig_dict["id"],
            "original_run_index": original_run_index,
            "resumed_run_id": resumed_res["run_id"],
            "resumed_run_index": next_run_index,
            "resumed_result": resumed_res,
        }
    finally:
        if should_close:
            conn.close()


# ---------------------------------------------------------------------------
# Fixture-Only End-to-End Smoke Workflow
# ---------------------------------------------------------------------------

def run_fixture_smoke_flow(
    db_path: Optional[Path] = None,
    tmp_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Complete fixture-only end-to-end smoke flow:
    1. Prepares temporary database.
    2. Builds a pinned task snapshot with solution and test.
    3. Builds protected evaluator outside workspace.
    4. Validates manifest with shared contract and intentional governance diffs.
    5. Prepares disposable workspaces for baseline and ICM arms.
    6. Verifies isolation and host preservation.
    7. Executes offline workflow (asserting 0 provider calls).
    8. Grades with protected evaluator.
    9. Records runs and verifies ledger reporting.
    10. Safely destroys disposable workspaces.
    """
    created_tmp = False
    if tmp_root is None:
        tmp_root = Path(tempfile.mkdtemp(prefix="smoke_fixture_"))
        created_tmp = True

    try:
        if db_path is None:
            db_path = tmp_root / "smoke_usage.db"

        # Initialize temporary DB
        conn = ledger.get_connection(db_path)
        ledger.seed_pricing(conn=conn)

        # 1. Pinned Task Snapshot
        snapshot_dir = tmp_root / "task_snapshot"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        (snapshot_dir / "solution.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")
        (snapshot_dir / "README.md").write_text("# Add Task\nImplement add(a, b).\n", encoding="utf-8")

        # 2. Protected Evaluator (outside workspace)
        evaluator_dir = tmp_root / "evaluator"
        evaluator_dir.mkdir(parents=True, exist_ok=True)
        evaluator_script = evaluator_dir / "test_eval.py"
        evaluator_script.write_text("""
import sys
from pathlib import Path
import solution

assert solution.add(2, 3) == 5, "Failed 2+3"
assert solution.add(-1, 1) == 0, "Failed -1+1"
print("ALL TESTS PASSED")
""", encoding="utf-8")
        evaluator = ProtectedEvaluator(evaluator_script)

        # 3. Build Manifest (RUN-04, RUN-05)
        task_id = "SMOKE-001"
        arm_base = ArmConfig(
            arm="baseline",
            model="gemini-2.5-pro",
            prompt="Implement add(a, b) in solution.py",
        )
        arm_icm = ArmConfig(
            arm="icm",
            model="gemini-2.5-pro",
            prompt="Implement add(a, b) in solution.py",
            governance_instructions="Follow 01_intake -> 02_plan -> 03_exec -> 04_verify",
            skills=["caveman", "ponytail"],
        )
        manifest = RunManifest(
            manifest_id="MAN-SMOKE-001",
            task_id=task_id,
            task_version="1.0.0",
            created_at=datetime.now(timezone.utc).isoformat(),
            task_contract={
                "task_id": task_id,
                "task_version": "1.0.0",
                "evaluator_hash": evaluator.expected_hash,
            },
            arms={"baseline": arm_base, "icm": arm_icm},
        )
        val_res = validate_manifest_configuration(manifest)
        assert val_res["valid"] is True

        # 4. Disposable Workspaces (RUN-01, RUN-02, RUN-03)
        ws_root = tmp_root / "workspaces"
        ws_base, ws_icm = WorkspaceManager.prepare_two_arms(
            snapshot_dir=snapshot_dir,
            workspace_root=ws_root,
            run_id="smoke_run_01",
        )

        try:
            assert ws_base.path != ws_icm.path
            assert (ws_base.path / "solution.py").exists()
            assert (ws_icm.path / "solution.py").exists()

            # Write in arm A, assert arm B and snapshot unchanged (RUN-02)
            (ws_base.path / "solution.py").write_text("def add(a, b): return a + b + 0\n", encoding="utf-8")
            assert (ws_icm.path / "solution.py").read_text(encoding="utf-8") == "def add(a, b): return a + b\n"
            assert (snapshot_dir / "solution.py").read_text(encoding="utf-8") == "def add(a, b): return a + b\n"

            # 5. Offline Execution (RUN-08)
            adapter = OfflineExecutionAdapter()
            res_base = execute_run_with_lifecycle(
                manifest=manifest,
                arm="baseline",
                workspace=ws_base,
                evaluator=evaluator,
                adapter=adapter,
                run_index=1,
                conn=conn,
            )
            res_icm = execute_run_with_lifecycle(
                manifest=manifest,
                arm="icm",
                workspace=ws_icm,
                evaluator=evaluator,
                adapter=adapter,
                run_index=1,
                conn=conn,
            )
            adapter.assert_zero_provider_calls()

            assert res_base["execution_status"] == "completed"
            assert res_base["verification_status"] == "passed"
            assert res_icm["execution_status"] == "completed"
            assert res_icm["verification_status"] == "passed"

            # 6. Verify Ledger State
            summary = ledger.task_summary(task_id, conn=conn)
            assert summary["total_runs"] == 2
            assert summary["fixture_runs_count"] == 2

            return {
                "status": "success",
                "task_id": task_id,
                "manifest_id": manifest.manifest_id,
                "verified_arms": ["baseline", "icm"],
                "zero_provider_calls_verified": True,
                "workspaces_isolated": True,
            }
        finally:
            ws_base.cleanup()
            ws_icm.cleanup()
            conn.close()

    finally:
        if created_tmp:
            shutil.rmtree(tmp_root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Live Benchmark Adapter (LiveAgyAdapter / run_benchmark_live)
# ---------------------------------------------------------------------------

def _build_live_prompt(instructions_text: str, arm: str, workspace: Optional[Path] = None) -> str:
    """Build baseline, ICM v2/v3/lite, or 4-stage ICM contract prompt with exact INSTRUCTIONS.md appended."""
    arm_lower = arm.lower()
    if arm_lower == "baseline":
        return instructions_text
    if arm_lower in (ICM_V2, ICM_V3, ICM_LITE):
        return build_mode_prompt(instructions_text, arm_lower, workspace=workspace)
    return (
        "Execute this task strictly following the 4-stage ICM contract:\n"
        "1. INTAKE & SCOPE: Read only the target files named in the instructions; stay strictly within scope and do not alter unrelated or prohibited files.\n"
        "2. PLAN: Design minimal, surgical changes before editing.\n"
        "3. DIFF-ONLY EXEC: Apply minimal targeted edits only to the required files.\n"
        "4. VERIFY: Run existing tests to verify all requirements pass before finishing.\n\n"
        f"{instructions_text}"
    )


def _extract_partial_step_usage(lines: List[str]) -> Optional[Dict[str, Optional[int]]]:
    """Sum per-step agent_response usages when a live stream lacks a final result event."""
    steps: Dict[Any, Dict[str, Any]] = {}
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        try:
            ev = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(ev, dict) and ev.get("event") == "step_update":
            su = ev.get("step_update") if isinstance(ev.get("step_update"), dict) else ev
            idx = su.get("step_index")
            if idx is not None:
                steps[idx] = su

    ar_usages = [
        su["usage"]
        for _, su in sorted(steps.items(), key=lambda kv: str(kv[0]))
        if su.get("step_type") == "agent_response" and isinstance(su.get("usage"), dict)
    ]
    if not ar_usages:
        return None
    inp = sum(int(u["input_tokens"]) for u in ar_usages if u.get("input_tokens") is not None)
    out = sum(int(u["output_tokens"]) for u in ar_usages if u.get("output_tokens") is not None)
    think = sum(int(u.get("thinking_tokens") or 0) for u in ar_usages)
    cache = sum(int(u.get("cache_read_tokens") or 0) for u in ar_usages)
    return {
        "input_tokens": inp,
        "output_tokens": out,
        "thinking_tokens": think,
        "cache_read_tokens": cache,
        "total_tokens": inp + out + cache,
    }


MAX_PHASE1_PLAN_CHARS = 12000

_QUOTA_SIGNALS = ("quota", "resource_exhausted", "rate limit", "rate_limit", "429", "exhausted", "capacity")


def _resolve_cli_binary(cli_cmd: str) -> str:
    """Resolve the CLI executable path, checking default Windows agy install location."""
    if not shutil.which(cli_cmd) and cli_cmd == "agy":
        default_agy = os.path.expandvars(r"%LOCALAPPDATA%\agy\bin\agy.exe")
        if os.path.exists(default_agy):
            return default_agy
    return cli_cmd


def _resolve_evidence_ref(evidence_file: Path) -> str:
    """Return a workspace-relative POSIX path when inside WORKSPACE_ROOT, else str(path)."""
    try:
        return evidence_file.resolve().relative_to(WORKSPACE_ROOT.resolve()).as_posix()
    except ValueError:
        return str(evidence_file)


def _append_unique(items: List[str], additions: List[str]) -> None:
    for item in additions:
        if item not in items:
            items.append(item)


def _sum_optional(a: Optional[int], b: Optional[int]) -> Optional[int]:
    """Sum two optional integer metrics, returning None if either is None."""
    if a is None or b is None:
        return None
    return int(a) + int(b)


def _extract_content_text(value: Any) -> str:
    """Normalize string or content-block list into plain text."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        chunks = []
        for block in value:
            if isinstance(block, str):
                chunks.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                chunks.append(block["text"])
        return "".join(chunks)
    return ""


def _extract_phase1_plan_text(
    lines: List[str],
    max_chars: int = MAX_PHASE1_PLAN_CHARS,
) -> Tuple[str, bool]:
    """Extract compact plan text from Phase 1 NDJSON and cap at ``max_chars``."""
    result_response: Optional[str] = None
    text_deltas: List[str] = []
    direct_contents: List[str] = []
    dedup_steps: Dict[Any, Dict[str, Any]] = {}

    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        try:
            ev = json.loads(s)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict):
            continue

        ev_type = str(ev.get("event") or ev.get("type") or "").lower()
        if ev_type == "result" or "result" in ev:
            res_obj = ev.get("result") if isinstance(ev.get("result"), dict) else ev
            resp = res_obj.get("response")
            if isinstance(resp, str) and resp.strip():
                result_response = resp

        if ev_type == "step_update":
            su = ev.get("step_update") if isinstance(ev.get("step_update"), dict) else ev
            if su.get("step_type") == "agent_response":
                delta = su.get("text_delta")
                if isinstance(delta, str) and delta:
                    text_deltas.append(delta)
                idx = su.get("step_index")
                if idx is not None:
                    dedup_steps[idx] = su
                else:
                    c = _extract_content_text(su.get("content") if "content" in su else su.get("response"))
                    if c:
                        direct_contents.append(c)
        elif ev_type == "agent_response" or ev.get("step_type") == "agent_response":
            delta = ev.get("text_delta")
            if isinstance(delta, str) and delta:
                text_deltas.append(delta)
            else:
                c = _extract_content_text(ev.get("content") if "content" in ev else ev.get("response"))
                if c:
                    direct_contents.append(c)

    if result_response is not None:
        plan_text = result_response
    elif text_deltas:
        plan_text = "".join(text_deltas)
    else:
        step_texts = [
            _extract_content_text(su.get("content") if "content" in su else su.get("response"))
            for _, su in sorted(dedup_steps.items(), key=lambda kv: str(kv[0]))
        ]
        step_texts = [t for t in step_texts if t]
        plan_text = "".join(step_texts) if step_texts else "".join(direct_contents)

    plan_text = plan_text.strip()
    if len(plan_text) > max_chars:
        return plan_text[:max_chars], True
    return plan_text, False


def _extract_phase_context_metrics(lines: List[str]) -> Tuple[Optional[int], List[int]]:
    """Return ``(initial_context_tokens, turn2_plus_fresh_inputs)`` from agent_response steps."""
    raw_lines = ledger._iter_ndjson_lines(lines)
    ordered_steps = ledger._deduplicate_step_updates(raw_lines)
    calls = [
        step["usage"]
        for step in ordered_steps
        if step.get("step_type") == "agent_response" and isinstance(step.get("usage"), dict)
    ]
    context_totals: List[int] = []
    for u in calls:
        inp = u.get("input_tokens")
        cr = u.get("cache_read_tokens")
        if ledger._is_numeric_nonbool(inp) or ledger._is_numeric_nonbool(cr):
            context_totals.append(
                (int(inp) if ledger._is_numeric_nonbool(inp) else 0)
                + (int(cr) if ledger._is_numeric_nonbool(cr) else 0)
            )
    initial_context = context_totals[0] if context_totals else None

    valid_input_calls = [u for u in calls if ledger._is_numeric_nonbool(u.get("input_tokens"))]
    if len(valid_input_calls) >= 2:
        turn2_inputs = [
            int(u["input_tokens"])
            for u in calls[1:]
            if ledger._is_numeric_nonbool(u.get("input_tokens"))
        ]
    else:
        turn2_inputs = []
    return initial_context, turn2_inputs


def _invoke_cli_phase(
    cmd_bin: str,
    prompt: str,
    workspace_path: Path,
    model: str,
    timeout_seconds: int,
    evidence_file: Path,
    devin_session_id: Optional[str] = None,
    devin_org_id: Optional[str] = None,
    devin_api_key: Optional[str] = None,
    acus_consumed: Optional[float] = None,
) -> Dict[str, Any]:
    """Invoke a single CLI session, persist raw NDJSON, and extract parsed telemetry."""
    cmd = [
        cmd_bin,
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--model",
        model,
        "--dangerously-skip-permissions",
        "--print-timeout",
        f"{int(timeout_seconds)}s",
    ]
    phase_start = time.time()
    phase_exclusions: List[str] = []
    raw_stderr = b""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(workspace_path),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=float(timeout_seconds) + 30.0,
            check=False,
        )
        raw_stdout = proc.stdout or b""
        raw_stderr = proc.stderr or b""
        execution_status = "completed" if proc.returncode == 0 else "failed"
        if execution_status == "failed":
            phase_exclusions.append("execution_failed")
    except subprocess.TimeoutExpired as exc:
        raw_stdout = exc.stdout or b""
        raw_stderr = exc.stderr or b""
        if isinstance(raw_stdout, str):
            raw_stdout = raw_stdout.encode("utf-8", errors="replace")
        if isinstance(raw_stderr, str):
            raw_stderr = raw_stderr.encode("utf-8", errors="replace")
        execution_status = "timed_out"
        phase_exclusions.extend(["timeout", "partial_telemetry"])

    wall_duration = time.time() - phase_start
    if isinstance(raw_stdout, str):
        raw_stdout = raw_stdout.encode("utf-8", errors="replace")
    if isinstance(raw_stderr, str):
        raw_stderr = raw_stderr.encode("utf-8", errors="replace")
    clean_bytes = raw_stdout.replace(b"\r\n", b"\n")
    stderr_text = raw_stderr.decode("utf-8", errors="replace")
    combined_err = (stderr_text + "\n" + clean_bytes.decode("utf-8", errors="replace")).lower()
    quota_exhausted = bool(
        execution_status == "failed" and any(sig in combined_err for sig in _QUOTA_SIGNALS)
    )
    if quota_exhausted and "quota_exhausted" not in phase_exclusions:
        phase_exclusions.append("quota_exhausted")

    evidence_file.write_bytes(clean_bytes)
    evidence_hash = hashlib.sha256(clean_bytes).hexdigest()
    evidence_ref = _resolve_evidence_ref(evidence_file)

    stdout_lines = clean_bytes.decode("utf-8", errors="replace").splitlines()
    cost_status: Optional[str] = None
    try:
        parsed = ledger.validate_and_parse_telemetry(stdout_lines)
    except ledger.TelemetryValidationError:
        valid_lines = []
        for raw in stdout_lines:
            s = raw.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    valid_lines.append(s)
            except json.JSONDecodeError:
                continue
        parsed = ledger.validate_and_parse_telemetry(valid_lines)
        if "partial_telemetry" not in phase_exclusions:
            phase_exclusions.append("partial_telemetry")
        cost_status = "incomplete"

    usage = dict(parsed["usage"])
    if not parsed["has_usage"] and execution_status in ("timed_out", "failed"):
        partial_u = _extract_partial_step_usage(stdout_lines)
        if partial_u is not None:
            usage = partial_u
            cost_status = "incomplete"
            if "partial_telemetry" not in phase_exclusions:
                phase_exclusions.append("partial_telemetry")

    tool_metrics = ledger.extract_ndjson_tool_metrics(stdout_lines)
    cache_diagnostics = ledger.extract_ndjson_cache_diagnostics(
        stdout_lines,
        tool_calls_count=tool_metrics["tool_calls_count"],
    )
    initial_context_tokens, turn2_fresh_inputs = _extract_phase_context_metrics(stdout_lines)
    duration_seconds = parsed["duration_seconds"] if parsed["duration_seconds"] > 0 else wall_duration
    num_turns = parsed["num_turns"]

    resolved_acus = pricing.validate_acus_consumed(acus_consumed)
    if resolved_acus is None:
        resolved_acus = parsed.get("acus_consumed")
    if resolved_acus is None:
        resolved_devin_id = (
            devin_session_id
            or parsed.get("devin_session_id")
            or os.environ.get("DEVIN_SESSION_ID")
        )
        resolved_org = devin_org_id or os.environ.get("DEVIN_ORG_ID")
        resolved_key = devin_api_key or os.environ.get("DEVIN_API_KEY")
        if resolved_devin_id and resolved_org and resolved_key:
            try:
                resolved_acus = fetch_devin_session_acus(
                    devin_id=resolved_devin_id,
                    org_id=resolved_org,
                    api_key=resolved_key,
                )
            except (urllib.error.URLError, ValueError, json.JSONDecodeError, OSError) as exc:
                warnings.warn(
                    f"Failed to fetch Devin session ACU telemetry for {resolved_devin_id}: {exc}"
                )

    return {
        "execution_status": execution_status,
        "exclusion_reasons": phase_exclusions,
        "quota_exhausted": quota_exhausted,
        "stderr_text": stderr_text,
        "evidence_ref": evidence_ref,
        "evidence_hash": evidence_hash,
        "stdout_lines": stdout_lines,
        "cost_status": cost_status,
        "usage": usage,
        "tool_metrics": tool_metrics,
        "cache_diagnostics": cache_diagnostics,
        "initial_context_tokens": initial_context_tokens,
        "turn2_fresh_inputs": turn2_fresh_inputs,
        "duration_seconds": duration_seconds,
        "num_turns": num_turns,
        "acus_consumed": resolved_acus,
    }


def _combine_staged_telemetry(p1: Dict[str, Any], p2: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate Phase 1 and Phase 2 telemetry without double-counting or faking missing fields."""
    if p2 is None:
        p1_peak = p1["cache_diagnostics"]["peak_context_tokens"]
        return {
            "execution_status": p1["execution_status"],
            "quota_exhausted": p1["quota_exhausted"],
            "stderr_excerpt": p1["stderr_text"][:400],
            "cost_status": p1["cost_status"],
            "usage": dict(p1["usage"]),
            "tool_metrics": dict(p1["tool_metrics"]),
            "cache_diagnostics": dict(p1["cache_diagnostics"]),
            "duration_seconds": p1["duration_seconds"],
            "num_turns": p1["num_turns"],
            "acus_consumed": p1["acus_consumed"],
            "phase1_peak_context": p1_peak,
            "phase2_initial_context": None,
            "tokens_shed": None,
            "phase1_tool_count": len(p1["tool_metrics"]["events"]),
        }

    u1, u2 = p1["usage"], p2["usage"]
    combined_usage = {
        "input_tokens": _sum_optional(u1.get("input_tokens"), u2.get("input_tokens")),
        "output_tokens": _sum_optional(u1.get("output_tokens"), u2.get("output_tokens")),
        "thinking_tokens": _sum_optional(u1.get("thinking_tokens"), u2.get("thinking_tokens")),
        "cache_read_tokens": _sum_optional(u1.get("cache_read_tokens"), u2.get("cache_read_tokens")),
        "total_tokens": _sum_optional(u1.get("total_tokens"), u2.get("total_tokens")),
    }

    tm1, tm2 = p1["tool_metrics"], p2["tool_metrics"]
    tool_calls_count = _sum_optional(tm1.get("tool_calls_count"), tm2.get("tool_calls_count"))
    tool_errors_count = _sum_optional(tm1.get("tool_errors_count"), tm2.get("tool_errors_count"))
    max_streak = max(tm1["max_consecutive_tool_streak"], tm2["max_consecutive_tool_streak"])
    loop_detected = bool(
        max_streak >= 6
        or (tool_errors_count is not None and tool_errors_count >= 3)
        or tm1["loop_detected"]
        or tm2["loop_detected"]
    )
    p1_events = list(tm1["events"])
    p2_events = list(tm2["events"])
    combined_tool_metrics = {
        "tool_calls_count": tool_calls_count,
        "tool_errors_count": tool_errors_count,
        "max_consecutive_tool_streak": max_streak,
        "loop_detected": loop_detected,
        "events": p1_events + p2_events,
    }

    cd1, cd2 = p1["cache_diagnostics"], p2["cache_diagnostics"]
    llm_calls_count = _sum_optional(cd1.get("llm_calls_count"), cd2.get("llm_calls_count"))
    cache_bust_count = _sum_optional(cd1.get("cache_bust_count"), cd2.get("cache_bust_count"))
    p1_peak = cd1.get("peak_context_tokens")
    p2_peak = cd2.get("peak_context_tokens")
    peak_context_tokens = max(p1_peak, p2_peak) if (p1_peak is not None and p2_peak is not None) else None
    p2_initial = p2.get("initial_context_tokens")
    tokens_shed = (
        max(0, p1_peak - p2_initial)
        if (p1_peak is not None and p2_initial is not None)
        else None
    )

    if (
        llm_calls_count is not None
        and llm_calls_count > 0
        and tool_calls_count is not None
    ):
        tools_per_llm_call: Optional[float] = tool_calls_count / llm_calls_count
    else:
        tools_per_llm_call = None

    if cd1.get("llm_calls_count") is not None and cd2.get("llm_calls_count") is not None:
        pooled_fresh = p1["turn2_fresh_inputs"] + p2["turn2_fresh_inputs"]
        avg_fresh: Optional[float] = (sum(pooled_fresh) / len(pooled_fresh)) if pooled_fresh else None
    else:
        avg_fresh = None

    combined_cache_diag = {
        "llm_calls_count": llm_calls_count,
        "peak_context_tokens": peak_context_tokens,
        "avg_fresh_input_per_call": avg_fresh,
        "cache_bust_count": cache_bust_count,
        "tools_per_llm_call": tools_per_llm_call,
    }

    cost_status = "incomplete" if "incomplete" in (p1["cost_status"], p2["cost_status"]) else None
    acus1, acus2 = p1.get("acus_consumed"), p2.get("acus_consumed")
    combined_acus = (acus1 + acus2) if (acus1 is not None and acus2 is not None) else None
    combined_stderr = (p2["stderr_text"] or p1["stderr_text"])[:400]

    return {
        "execution_status": p2["execution_status"],
        "quota_exhausted": bool(p1["quota_exhausted"] or p2["quota_exhausted"]),
        "stderr_excerpt": combined_stderr,
        "cost_status": cost_status,
        "usage": combined_usage,
        "tool_metrics": combined_tool_metrics,
        "cache_diagnostics": combined_cache_diag,
        "duration_seconds": p1["duration_seconds"] + p2["duration_seconds"],
        "num_turns": (p1["num_turns"] or 0) + (p2["num_turns"] or 0),
        "acus_consumed": combined_acus,
        "phase1_peak_context": p1_peak,
        "phase2_initial_context": p2_initial,
        "tokens_shed": tokens_shed,
        "phase1_tool_count": len(p1_events),
    }


def _run_staged_two_phase(
    *,
    task_id: str,
    arm: str,
    run_index: int,
    model: str,
    cmd_bin: str,
    timeout_seconds: int,
    workspace: DisposableWorkspace,
    snapshot_dir: Path,
    pre_hash: str,
    instructions_text: str,
    evidence_dir: Path,
    safe_model: str,
    start_epoch: float,
    devin_session_id: Optional[str] = None,
    devin_org_id: Optional[str] = None,
    devin_api_key: Optional[str] = None,
    acus_consumed: Optional[float] = None,
) -> Dict[str, Any]:
    """Run two-session icm_staged (Phase 1 read-only plan -> fresh-context Phase 2 exec)."""
    ts = int(start_epoch)
    exclusion_reasons: List[str] = []

    phase1_prompt, _ = build_staged_prompts(instructions_text, workspace=snapshot_dir)
    phase1_file = evidence_dir / f"live_{task_id}_{safe_model}_{arm}_phase1_run{run_index}_{ts}.ndjson"
    p1 = _invoke_cli_phase(
        cmd_bin=cmd_bin,
        prompt=phase1_prompt,
        workspace_path=workspace.path,
        model=model,
        timeout_seconds=timeout_seconds,
        evidence_file=phase1_file,
        devin_session_id=devin_session_id,
        devin_org_id=devin_org_id,
        devin_api_key=devin_api_key,
        acus_consumed=acus_consumed,
    )
    _append_unique(exclusion_reasons, p1["exclusion_reasons"])

    if workspace.snapshot_tree_hash() != pre_hash:
        _append_unique(exclusion_reasons, ["phase1_mutation_violation"])
        workspace.rollback_to_backup()

    plan_text, plan_truncated = _extract_phase1_plan_text(p1["stdout_lines"])
    if plan_truncated:
        _append_unique(exclusion_reasons, ["phase1_plan_truncated"])

    p2: Optional[Dict[str, Any]] = None
    if p1["execution_status"] == "completed":
        phase2_prompt = build_staged_exec_prompt(
            instructions=instructions_text,
            plan_text=plan_text,
            workspace=snapshot_dir,
        )
        phase2_file = evidence_dir / f"live_{task_id}_{safe_model}_{arm}_phase2_run{run_index}_{ts}.ndjson"
        p2 = _invoke_cli_phase(
            cmd_bin=cmd_bin,
            prompt=phase2_prompt,
            workspace_path=workspace.path,
            model=model,
            timeout_seconds=timeout_seconds,
            evidence_file=phase2_file,
            devin_session_id=devin_session_id,
            devin_org_id=devin_org_id,
            devin_api_key=devin_api_key,
            acus_consumed=acus_consumed,
        )
        _append_unique(exclusion_reasons, p2["exclusion_reasons"])

    agg = _combine_staged_telemetry(p1, p2)
    if acus_consumed is not None:
        agg["acus_consumed"] = pricing.validate_acus_consumed(acus_consumed)

    manifest_payload = {
        "event": "staged_summary",
        "phase1_ref": p1["evidence_ref"],
        "phase1_hash": p1["evidence_hash"],
        "phase2_ref": p2["evidence_ref"] if p2 is not None else None,
        "phase2_hash": p2["evidence_hash"] if p2 is not None else None,
        "phase1_peak_context": agg["phase1_peak_context"],
        "phase2_initial_context": agg["phase2_initial_context"],
        "tokens_shed": agg["tokens_shed"],
    }
    manifest_bytes = (json.dumps(manifest_payload, sort_keys=True) + "\n").encode("utf-8")
    manifest_file = evidence_dir / f"live_{task_id}_{safe_model}_{arm}_run{run_index}_{ts}.ndjson"
    manifest_file.write_bytes(manifest_bytes)
    evidence_hash = hashlib.sha256(manifest_bytes).hexdigest()
    evidence_ref = _resolve_evidence_ref(manifest_file)

    context_reset_event: Optional[Dict[str, Any]] = None
    if p2 is not None:
        context_reset_event = {
            "phase": "context_reset",
            "tool_name": "context_reset",
            "status": "DONE",
            "diff_hash": p1["evidence_hash"],
            "rollback_ref": json.dumps(
                {
                    "phase1_peak_context": agg["phase1_peak_context"],
                    "phase2_initial_context": agg["phase2_initial_context"],
                    "tokens_shed": agg["tokens_shed"],
                }
            ),
        }

    return {
        **agg,
        "exclusion_reasons": exclusion_reasons,
        "evidence_ref": evidence_ref,
        "evidence_hash": evidence_hash,
        "phase1_ref": p1["evidence_ref"],
        "phase1_hash": p1["evidence_hash"],
        "phase2_ref": p2["evidence_ref"] if p2 is not None else None,
        "phase2_hash": p2["evidence_hash"] if p2 is not None else None,
        "context_reset_event": context_reset_event,
    }


def run_benchmark_live(
    task_id: str,
    arm: str,
    run_index: int,
    model: str = "gemini-4-hydrogen-low",
    cli_cmd: str = "agy",
    timeout_seconds: int = 180,
    db_path: Optional[Path] = None,
    workspace_root: Optional[Path] = None,
    mode: Optional[str] = None,
    devin_session_id: Optional[str] = None,
    devin_org_id: Optional[str] = None,
    devin_api_key: Optional[str] = None,
    acus_consumed: Optional[float] = None,
    canonical_workspace: bool = False,
) -> Dict[str, Any]:
    """
    Execute a live benchmark task using the agy CLI in an isolated DisposableWorkspace.
    Captures pre-run backup, raw NDJSON evidence + SHA-256, tool/loop metrics,
    grades via ProtectedEvaluator, rolls back on failure, and persists run + run_events.
    """
    _validate_identifier(task_id, "task_id")
    task_dir = WORKSPACE_ROOT / "benchmarks" / task_id
    snapshot_dir = task_dir / "workspace"
    metadata: Dict[str, Any] = {}
    metadata_path = task_dir / "task.json"
    if metadata_path.is_file():
        try:
            loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            warnings.warn(f"Malformed task.json at {metadata_path}: not valid JSON; treating scope metadata as empty.")
            loaded = {}
        if isinstance(loaded, dict):
            metadata = loaded
        else:
            warnings.warn(f"Malformed task.json at {metadata_path}: expected a JSON object; treating scope metadata as empty.")
    routing_decision: Optional[RoutingDecision] = None
    if mode is not None:
        routing_decision = classify_mode(mode, metadata, snapshot_dir)
        arm = routing_decision.arm
        print(
            f"[*] Routing mode '{mode}' selected arm '{arm}' "
            f"(loc_source={routing_decision.loc_source}, loc={routing_decision.loc}, "
            f"ast_symbol_count={routing_decision.ast_symbol_count}, "
            f"single_file={routing_decision.single_file}, target={routing_decision.target})."
        )
    _validate_identifier(arm, "arm")
    if routing_decision is not None:
        contract_version = routing_decision.contract_version
        contract_hash = routing_decision.contract_hash
    else:
        contract_version, contract_hash = resolve_contract_metadata(arm)

    evaluator_dir = task_dir / "evaluator"
    if not snapshot_dir.is_dir():
        raise FileNotFoundError(f"Benchmark workspace not found: {snapshot_dir}")
    if not evaluator_dir.exists():
        raise FileNotFoundError(f"Benchmark evaluator not found: {evaluator_dir}")

    instructions_path = snapshot_dir / "INSTRUCTIONS.md"
    if not instructions_path.is_file():
        raise FileNotFoundError(f"INSTRUCTIONS.md not found in {snapshot_dir}")
    instructions_text = instructions_path.read_text(encoding="utf-8")

    evaluator = ProtectedEvaluator(evaluator_dir)
    run_uid = f"live_{task_id}_{os.getpid()}_{int(time.time() * 1000)}"
    workspace = WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=snapshot_dir,
        arm=arm,
        workspace_root=workspace_root,
        run_id=run_uid,
        canonical_workspace=canonical_workspace,
        task_id=task_id,
    )

    try:
        workspace.capture_backup()
        pre_hash = workspace.snapshot_tree_hash()

        cmd_bin = _resolve_cli_binary(cli_cmd)
        evidence_dir = DEFAULT_EVIDENCE_DIR
        evidence_dir.mkdir(parents=True, exist_ok=True)
        safe_model = re.sub(r"[^A-Za-z0-9._-]+", "-", model)
        start_epoch = time.time()
        start_ts = datetime.now(timezone.utc).isoformat()

        context_reset_event: Optional[Dict[str, Any]] = None
        phase1_tool_count: Optional[int] = None
        staged_meta: Dict[str, Any] = {}

        if arm == ICM_STAGED:
            exec_bundle = _run_staged_two_phase(
                task_id=task_id,
                arm=arm,
                run_index=run_index,
                model=model,
                cmd_bin=cmd_bin,
                timeout_seconds=timeout_seconds,
                workspace=workspace,
                snapshot_dir=snapshot_dir,
                pre_hash=pre_hash,
                instructions_text=instructions_text,
                evidence_dir=evidence_dir,
                safe_model=safe_model,
                start_epoch=start_epoch,
                devin_session_id=devin_session_id,
                devin_org_id=devin_org_id,
                devin_api_key=devin_api_key,
                acus_consumed=acus_consumed,
            )
            context_reset_event = exec_bundle["context_reset_event"]
            phase1_tool_count = exec_bundle["phase1_tool_count"]
            staged_meta = {
                "phase1_ref": exec_bundle["phase1_ref"],
                "phase1_hash": exec_bundle["phase1_hash"],
                "phase2_ref": exec_bundle["phase2_ref"],
                "phase2_hash": exec_bundle["phase2_hash"],
                "phase1_peak_context": exec_bundle["phase1_peak_context"],
                "phase2_initial_context": exec_bundle["phase2_initial_context"],
                "tokens_shed": exec_bundle["tokens_shed"],
            }
            stderr_excerpt = exec_bundle["stderr_excerpt"]
        else:
            if mode is None:
                prompt = _build_live_prompt(instructions_text, arm, workspace=snapshot_dir)
            else:
                prompt = build_mode_prompt(instructions_text, arm, workspace=snapshot_dir)
            evidence_file = evidence_dir / f"live_{task_id}_{safe_model}_{arm}_run{run_index}_{int(start_epoch)}.ndjson"
            exec_bundle = _invoke_cli_phase(
                cmd_bin=cmd_bin,
                prompt=prompt,
                workspace_path=workspace.path,
                model=model,
                timeout_seconds=timeout_seconds,
                evidence_file=evidence_file,
                devin_session_id=devin_session_id,
                devin_org_id=devin_org_id,
                devin_api_key=devin_api_key,
                acus_consumed=acus_consumed,
            )
            stderr_excerpt = exec_bundle["stderr_text"][:400]

        execution_status = exec_bundle["execution_status"]
        exclusion_reasons: List[str] = list(exec_bundle["exclusion_reasons"])
        quota_exhausted = exec_bundle["quota_exhausted"]
        evidence_ref = exec_bundle["evidence_ref"]
        evidence_hash = exec_bundle["evidence_hash"]
        cost_status = exec_bundle["cost_status"]
        usage = exec_bundle["usage"]
        tool_metrics = exec_bundle["tool_metrics"]
        cache_diagnostics = exec_bundle["cache_diagnostics"]
        duration_seconds = exec_bundle["duration_seconds"]
        num_turns = exec_bundle["num_turns"]
        resolved_acus = exec_bundle["acus_consumed"]

        post_hash = workspace.snapshot_tree_hash()

        scope = scope_telemetry(workspace.path, snapshot_dir, metadata)
        if routing_decision is not None:
            scope["loc_source"] = routing_decision.loc_source
            scope["ast_symbol_count"] = routing_decision.ast_symbol_count
            scope["declared_scope"]["loc"] = routing_decision.loc
            scope["declared_scope"]["loc_source"] = routing_decision.loc_source
            scope["declared_scope"]["ast_symbol_count"] = routing_decision.ast_symbol_count
        print(
            f"[*] Scope telemetry: declared_scope={scope['declared_scope']} "
            f"actual_scope={scope['actual_scope']} "
            f"files_touched={list(scope['files_touched'])} "
            f"lines_touched={scope['lines_touched']} scope_mismatch={scope['scope_mismatch']}."
        )

        verif: Optional[VerificationResult] = None
        if execution_status == "completed":
            verif = evaluator.evaluate_workspace(workspace.path)
            verif_status = verif.verification_status
            ev_hash = verif.evaluator_hash
            for r in verif.reasons:
                if r not in exclusion_reasons:
                    exclusion_reasons.append(r)
        else:
            is_valid, ev_hash = evaluator.verify_hash()
            if not is_valid:
                verif_status = "evaluator_error"
                for r in ("evaluator_hash_mismatch", "evaluator_tampered", "evaluator_error"):
                    if r not in exclusion_reasons:
                        exclusion_reasons.append(r)
            else:
                verif_status = "not_run"

        rolled_back = False
        restored_hash: Optional[str] = None
        if verif_status in ("failed", "evaluator_error") or execution_status in ("failed", "timed_out"):
            restored_hash = workspace.rollback_to_backup()
            rolled_back = True

        conn = ledger.get_connection(db_path)
        try:
            run_id = ledger.record_run(
                task_id=task_id,
                arm=arm,
                model=model,
                run_index=run_index,
                timestamp=start_ts,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                thinking_tokens=usage.get("thinking_tokens"),
                cache_read_tokens=usage.get("cache_read_tokens"),
                total_tokens=usage["total_tokens"],
                num_turns=num_turns,
                duration_seconds=duration_seconds,
                source_kind="live",
                evidence_status="verified",
                exclusion_reasons=exclusion_reasons or None,
                evidence_ref=evidence_ref,
                evidence_hash=evidence_hash,
                cost_status=cost_status,
                acus_consumed=resolved_acus,
                execution_status=execution_status,
                verification_status=verif_status,
                evaluator_hash=ev_hash,
                tool_calls_count=tool_metrics["tool_calls_count"],
                tool_errors_count=tool_metrics["tool_errors_count"],
                max_consecutive_tool_streak=tool_metrics["max_consecutive_tool_streak"],
                loop_detected=tool_metrics["loop_detected"],
                llm_calls_count=cache_diagnostics["llm_calls_count"],
                peak_context_tokens=cache_diagnostics["peak_context_tokens"],
                avg_fresh_input_per_call=cache_diagnostics["avg_fresh_input_per_call"],
                cache_bust_count=cache_diagnostics["cache_bust_count"],
                tools_per_llm_call=cache_diagnostics["tools_per_llm_call"],
                contract_version=contract_version,
                contract_hash=contract_hash,
                conn=conn,
            )

            _persist_run_lifecycle_events(
                conn=conn,
                run_id=run_id,
                pre_hash=pre_hash,
                post_hash=post_hash,
                verif_status=verif_status,
                tool_events=tool_metrics["events"],
                rolled_back=rolled_back,
                restored_hash=restored_hash,
                start_ts=start_ts,
                scope=scope,
                context_reset=context_reset_event,
                phase1_tool_count=phase1_tool_count,
            )

            row = dict(
                conn.execute(
                    "SELECT cost_status, cost_usd, acus_consumed FROM runs WHERE id = ?",
                    (run_id,),
                ).fetchone()
            )
        finally:
            conn.close()

        return {
            "run_id": run_id,
            "task_id": task_id,
            "arm": arm,
            "run_index": run_index,
            "model": model,
            "execution_status": execution_status,
            "verification_status": verif_status,
            "verification": verif,
            "cost_status": row["cost_status"],
            "cost_usd": row["cost_usd"],
            "acus_consumed": row["acus_consumed"],
            "usage": usage,
            "tool_metrics": tool_metrics,
            "cache_diagnostics": cache_diagnostics,
            "contract_version": contract_version,
            "contract_hash": contract_hash,
            "evidence_ref": evidence_ref,
            "evidence_hash": evidence_hash,
            "pre_hash": pre_hash,
            "post_hash": post_hash,
            "restored_hash": restored_hash,
            "rolled_back": rolled_back,
            "quota_exhausted": quota_exhausted,
            "stderr_excerpt": stderr_excerpt,
            "exclusion_reasons": exclusion_reasons,
            "scope": scope,
            **staged_meta,
        }
    finally:
        workspace.cleanup()


def run_benchmark_staged(
    task_id: str,
    run_index: int = 1,
    model: str = "gemini-4-hydrogen-low",
    cli_cmd: str = "agy",
    timeout_seconds: int = 180,
    db_path: Optional[Path] = None,
    workspace_root: Optional[Path] = None,
    devin_session_id: Optional[str] = None,
    devin_org_id: Optional[str] = None,
    devin_api_key: Optional[str] = None,
    acus_consumed: Optional[float] = None,
) -> Dict[str, Any]:
    """Execute a live benchmark task using the two-session ``icm_staged`` contract."""
    return run_benchmark_live(
        task_id=task_id,
        arm=ICM_STAGED,
        run_index=run_index,
        model=model,
        cli_cmd=cli_cmd,
        timeout_seconds=timeout_seconds,
        db_path=db_path,
        workspace_root=workspace_root,
        mode=None,
        devin_session_id=devin_session_id,
        devin_org_id=devin_org_id,
        devin_api_key=devin_api_key,
        acus_consumed=acus_consumed,
    )


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ai-Lab Phase 2 Runner & Disposable Workspace Harness")
    parser.add_argument("--smoke", action="store_true", help="Run fixture-only end-to-end smoke workflow")
    parser.add_argument("--live-bench", nargs="?", const="BENCH-001", default=None, help="Run a live benchmark task (e.g., --live-bench --task BENCH-002)")
    parser.add_argument("--task", default=None, help="Benchmark task ID for --live-bench (default: BENCH-001)")
    routing = parser.add_mutually_exclusive_group()
    routing.add_argument("--arm", default="baseline", help="Experiment arm for --live-bench (default: baseline)")
    routing.add_argument("--mode", choices=MODES, help="Select a live benchmark contract (auto routes by task scope)")
    parser.add_argument("--run-index", type=int, default=1, help="Run index for --live-bench (default: 1)")
    parser.add_argument("--model", default="gemini-4-hydrogen-low", help="Model ID for --live-bench")
    parser.add_argument("--cli", default="agy", help="CLI executable for --live-bench (default: agy)")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout seconds for --live-bench (default: 180)")
    parser.add_argument("--db", default=None, help="Custom database path for smoke or runner execution")
    parser.add_argument("--canonical-workspace", action="store_true", help="Use a deterministic disposable workspace directory per (task_id, arm) for --live-bench")
    args = parser.parse_args()
    if args.mode is not None and (args.smoke or args.live_bench is None):
        parser.error("--mode requires --live-bench without --smoke")

    if args.smoke:
        print("[*] Running Phase 2 Fixture-Only Smoke Flow...")
        db_path = Path(args.db) if args.db else None
        res = run_fixture_smoke_flow(db_path=db_path)
        print(f"✓ Fixture smoke flow completed successfully: {res}")
        sys.exit(0)

    if args.live_bench is not None:
        target_task = args.task or args.live_bench
        db_path = Path(args.db) if args.db else None
        print(f"[*] Running live benchmark {target_task} ({args.mode or args.arm} #{args.run_index}, model={args.model})...")
        res = run_benchmark_live(
            task_id=target_task,
            arm=args.arm,
            run_index=args.run_index,
            model=args.model,
            cli_cmd=args.cli,
            timeout_seconds=args.timeout,
            db_path=db_path,
            mode=args.mode,
            canonical_workspace=args.canonical_workspace,
        )
        print(f"✓ Live benchmark finished: status={res['execution_status']} verify={res['verification_status']} cost_status={res['cost_status']} rolled_back={res['rolled_back']}")
        if res.get("quota_exhausted"):
            print("QUOTA_EXHAUSTED=1")
            sys.exit(42)
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
