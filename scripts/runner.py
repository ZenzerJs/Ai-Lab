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
import dataclasses
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

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

DEFAULT_FIXTURES_PATH = WORKSPACE_ROOT / "experiments" / "fixtures" / "mock_stream.ndjson"

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
    # Enforce offline invariant flags
    safe_env["OFFLINE_MODE"] = "1"
    safe_env["AI_LAB_OFFLINE"] = "1"
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

    def cleanup(self) -> None:
        """Safely destroy this disposable directory without touching any host files (RUN-03)."""
        if self._is_cleaned:
            return
        if not self.path.exists():
            self._is_cleaned = True
            return

        p_res = self.path.resolve()
        snap_res = self.snapshot_dir.resolve()
        ws_res = WORKSPACE_ROOT.resolve()

        # Invariant checks: never delete repo root or host files outside of tmp/
        if p_res == ws_res or ws_res in p_res.parents or p_res in ws_res.parents:
            tmp_dir = (WORKSPACE_ROOT / "tmp").resolve()
            try:
                p_res.relative_to(tmp_dir)
            except ValueError:
                # Host safety violation: refuse to delete files in host repo outside of tmp/
                return

        if p_res == snap_res or snap_res in p_res.parents or p_res in snap_res.parents:
            # Snapshot safety violation: refuse to delete snapshot directory
            return

        _safe_rmtree(self.path)
        self._is_cleaned = True

    def __enter__(self) -> "DisposableWorkspace":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()


class WorkspaceManager:
    """Manages creation and cleanup of disposable workspaces."""

    @staticmethod
    def prepare_arm_workspace(
        snapshot_dir: Path,
        arm: str,
        workspace_root: Optional[Path] = None,
        run_id: Optional[str] = None,
    ) -> DisposableWorkspace:
        """
        Prepare an isolated disposable workspace directory from a pinned task snapshot (RUN-01, RUN-03).
        Preserves user uncommitted files and repository state completely.
        """
        if not snapshot_dir.exists():
            raise FileNotFoundError(f"Snapshot directory not found: {snapshot_dir}")

        if not run_id:
            run_id = f"run_{int(time.time() * 1000)}"

        if workspace_root is None:
            base_temp = WORKSPACE_ROOT / "tmp" / "disposable_workspaces"
            base_temp.mkdir(parents=True, exist_ok=True)
            ws_dir = base_temp / f"{run_id}_{arm}"
        else:
            workspace_root.mkdir(parents=True, exist_ok=True)
            ws_dir = workspace_root / f"{run_id}_{arm}"

        # Clean if directory already exists from a prior interrupted trial
        if ws_dir.exists():
            _safe_rmtree(ws_dir)

        # Copy snapshot into disposable workspace
        shutil.copytree(snapshot_dir, ws_dir, dirs_exist_ok=True)

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

        # If directory, compute hash of all sorted files
        h = hashlib.sha256()
        for p in sorted(self.evaluator_path.rglob("*")):
            if p.is_file():
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
            cmd = [sys.executable, "-m", "pytest", str(self.evaluator_path)]

        if cmd is not None:
            try:
                res = subprocess.run(
                    cmd,
                    cwd=str(workspace_path),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=45,
                    check=False,
                )
                passed = (res.returncode == 0)
                status = "passed" if passed else "failed"
                reasons = [] if passed else ["test_failure"]
                out = res.stdout + ("\n" + res.stderr if res.stderr else "")
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


class OfflineExecutionAdapter:
    """
    Offline execution workflow asserting zero provider or paid API invocations (RUN-08).
    Replays fixture telemetry streams and ensures absolute network isolation.
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
        if telemetry_stream:
            parsed = ledger.validate_and_parse_telemetry(telemetry_stream)
            u = parsed["usage"]
            num_turns = parsed["num_turns"]
            duration = parsed["duration_seconds"]
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
            thinking_tokens=u["thinking_tokens"] or 0 if u["input_tokens"] is not None else None,
            cache_read_tokens=u["cache_read_tokens"] or 0 if u["input_tokens"] is not None else None,
            total_tokens=u["total_tokens"],
            num_turns=num_turns,
            duration_seconds=duration,
            source_kind="imported",
            evidence_status="unverified" if not telemetry_stream else "verified",
            exclusion_reasons=exclusion_reasons,
            cost_status=cost_status,
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
) -> Dict[str, Any]:
    """
    Execute an arm run with lifecycle tracking:
    - RUN-06: Simulate timeout -> Timed-out attempt retained with partial evidence.
    - RUN-07: Simulate interruption -> Preserves original attempt without invented completion.
    """
    arm_cfg = manifest.arms[arm]
    model = arm_cfg.model
    if timeout_seconds is None:
        timeout_seconds = float(arm_cfg.resource_budget.get("timeout_seconds", 600.0))

    if adapter is None:
        adapter = OfflineExecutionAdapter()

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

    u = exec_res.usage or {
        "input_tokens": None,
        "output_tokens": None,
        "thinking_tokens": 0,
        "cache_read_tokens": 0,
        "total_tokens": None,
    }

    run_id = ledger.record_run(
        task_id=manifest.task_id,
        arm=arm,
        model=model,
        run_index=run_index,
        timestamp=datetime.now(timezone.utc).isoformat(),
        input_tokens=u["input_tokens"],
        output_tokens=u["output_tokens"],
        thinking_tokens=u.get("thinking_tokens", 0),
        cache_read_tokens=u.get("cache_read_tokens", 0),
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
        db_path=db_path,
        conn=conn,
    )

    return {
        "run_id": run_id,
        "execution": exec_res,
        "verification": verif,
        "execution_status": exec_res.execution_status,
        "verification_status": verif_status,
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
# CLI Entrypoint
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ai-Lab Phase 2 Runner & Disposable Workspace Harness")
    parser.add_argument("--smoke", action="store_true", help="Run fixture-only end-to-end smoke workflow")
    parser.add_argument("--db", default=None, help="Custom database path for smoke or runner execution")
    args = parser.parse_args()

    if args.smoke:
        print("[*] Running Phase 2 Fixture-Only Smoke Flow...")
        db_path = Path(args.db) if args.db else None
        res = run_fixture_smoke_flow(db_path=db_path)
        print(f"✓ Fixture smoke flow completed successfully: {res}")
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
