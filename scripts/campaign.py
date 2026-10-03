#!/usr/bin/env python3
"""
scripts/campaign.py - Controlled Repeated Comparisons: Campaign Matrix Planner & Report Generator

Implements Phase 4 specifications:
- REP-01: Controlled evaluation matrices: Tasks × Arms × Repetitions with predeclared, randomized arm order.
- REP-02: Retention of all scheduled attempts (completed, failed, timed-out, unexecuted) with execution coverage.
- REP-03: Exact per-arm sample counts without masquerading as balanced.
- REP-04: Honest empty state when no eligible measured runs exist.
- REP-05: Undefined savings percentage when baseline estimated cost is zero, with absolute numbers reported.
- REP-06: Undefined cost-per-success when all verified outcomes fail (never fake $0.00).
- REP-07: Decoupled correctness and telemetry (correct run lacking telemetry counted in correctness, excluded from cost with reason).
- REP-08: Paired cost difference excludes pairs where either member lacks complete cost; reports missing-pair count.
- REP-09: Cold and warm cache conditions stratified separately rather than blended silently.
- REP-10: Task-level results retained alongside pooled summaries, with explicit pooling methodology.
"""

import argparse
import copy
import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import sqlite3
import sys
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

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

import ledger
import runner

# ---------------------------------------------------------------------------
# Constants & Arm Configurations
# ---------------------------------------------------------------------------

SUPPORTED_ARMS = ("baseline", "icm", "delegation")

DEFAULT_ARM_CONFIGS: Dict[str, Dict[str, Any]] = {
    "baseline": {
        "arm": "baseline",
        "model": "gemini-2.5-pro",
        "description": "Arm A: Unconstrained single-session baseline",
        "governance_instructions": None,
        "skills": [],
        "subagents": [],
    },
    "icm": {
        "arm": "icm",
        "model": "gemini-2.5-pro",
        "description": "Arm B: Interpretable Context Methodology (staged governance)",
        "governance_instructions": "Enforce ICM 5-stage pipeline: 01_intake -> 02_plan -> 03_exec -> 04_verify -> 05_retro.",
        "skills": ["ai-lab"],
        "subagents": [],
    },
    "delegation": {
        "arm": "delegation",
        "model": "gemini-2.5-pro",
        "description": "Arm C: Subagent delegation / multi-agent orchestration",
        "governance_instructions": "ICM staged governance with specialized worker delegation.",
        "skills": ["ai-lab", "build-agents"],
        "subagents": ["planner", "coder", "evaluator"],
    },
}

CACHE_CONDITIONS = ("cold", "warm")


# ---------------------------------------------------------------------------
# Campaign Data Models (REP-01, REP-02)
# ---------------------------------------------------------------------------

@dataclass
class CampaignSlot:
    """Represents a single scheduled evaluation attempt in the campaign matrix."""
    slot_id: str
    campaign_id: str
    task_id: str
    task_version: str
    repetition_index: int
    arm: str
    planned_order: int
    cache_condition: str = "cold"
    intended_cache_condition: str = "cold"
    observed_cache_condition: str = "unknown"
    model: str = "gemini-2.5-pro"
    model_settings: Dict[str, Any] = field(default_factory=lambda: {"temperature": 0.0, "top_p": 1.0})
    resource_budget: Dict[str, Any] = field(default_factory=lambda: {
        "timeout_seconds": 600.0,
        "max_cost_usd": 10.0,
        "max_turns": 10,
    })
    status: str = "scheduled"  # scheduled, completed, failed, timed_out, unexecuted, interrupted
    execution_status: Optional[str] = None
    verification_status: Optional[str] = None
    run_id: Optional[int] = None
    cost_usd: Optional[float] = None
    cost_status: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    thinking_tokens: Optional[int] = None
    cache_read_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    duration_seconds: Optional[float] = None
    num_turns: Optional[int] = None
    exclusion_reasons: List[str] = field(default_factory=list)
    source_kind: str = "fixture"
    evidence_status: str = "unverified"
    is_simulation: int = 0
    evidence_ref: Optional[str] = None
    evidence_hash: Optional[str] = None
    error_message: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self):
        if self.cache_condition and (not self.intended_cache_condition or self.intended_cache_condition == "cold"):
            self.intended_cache_condition = self.cache_condition
        elif self.intended_cache_condition:
            self.cache_condition = self.intended_cache_condition

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignSlot":
        allowed = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in allowed}
        return cls(**filtered)

    def to_ledger_run(self, timestamp: Optional[str] = None) -> Dict[str, Any]:
        """Convert slot outcome to ledger run dictionary."""
        notes_dict: Dict[str, Any] = {
            "slot_id": self.slot_id,
            "campaign_id": self.campaign_id,
            "planned_order": self.planned_order,
            "cache_condition": self.cache_condition,
            "intended_cache_condition": self.intended_cache_condition,
            "observed_cache_condition": self.observed_cache_condition,
        }
        if self.notes:
            notes_dict["user_notes"] = self.notes

        return {
            "task_id": self.task_id,
            "arm": self.arm,
            "model": self.model,
            "run_index": self.repetition_index,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "thinking_tokens": self.thinking_tokens or 0,
            "cache_read_tokens": self.cache_read_tokens or 0,
            "total_tokens": self.total_tokens,
            "num_turns": self.num_turns or 1,
            "duration_seconds": self.duration_seconds or 0.0,
            "source_kind": self.source_kind or "fixture",
            "evidence_status": self.evidence_status or ("verified" if self.status == "completed" else "unverified"),
            "exclusion_reasons": self.exclusion_reasons,
            "cost_status": self.cost_status or ("usage_estimate" if self.cost_usd is not None else "unknown"),
            "cost_usd": self.cost_usd,
            "is_simulation": self.is_simulation,
            "evidence_ref": self.evidence_ref,
            "evidence_hash": self.evidence_hash,
            "notes": json.dumps(notes_dict),
            "execution_status": self.execution_status or self.status,
            "verification_status": self.verification_status or "not_run",
            "manifest_id": self.campaign_id,
        }


@dataclass
class CampaignManifest:
    """Immutable campaign manifest defining tasks, arms, repetitions, randomized order, and execution slots."""
    campaign_id: str
    created_at: str
    tasks: List[Dict[str, Any]]
    arms: List[str]
    arm_configs: Dict[str, Dict[str, Any]]
    repetitions: int
    random_seed: Optional[int]
    cache_conditions: List[str]
    slots: List[CampaignSlot]
    manifest_hash: str = ""

    def __post_init__(self):
        # Finding 4: Do NOT auto-compute a hash if missing when loading a manifest
        pass

    def compute_manifest_hash(self) -> str:
        """Compute SHA-256 integrity hash of the scheduled matrix plan."""
        canonical_plan = {
            "campaign_id": self.campaign_id,
            "tasks": self.tasks,
            "arms": self.arms,
            "arm_configs": self.arm_configs,
            "repetitions": self.repetitions,
            "random_seed": self.random_seed,
            "cache_conditions": self.cache_conditions,
            "slots": [
                {
                    "slot_id": s.slot_id,
                    "task_id": s.task_id,
                    "task_version": s.task_version,
                    "repetition_index": s.repetition_index,
                    "arm": s.arm,
                    "planned_order": s.planned_order,
                    "cache_condition": s.cache_condition,
                    "model": s.model,
                    "model_settings": s.model_settings,
                    "resource_budget": s.resource_budget,
                }
                for s in self.slots
            ],
        }
        raw = json.dumps(canonical_plan, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify that the manifest plan has not been tampered with."""
        if not self.manifest_hash:
            return False
        return self.compute_manifest_hash() == self.manifest_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "created_at": self.created_at,
            "tasks": self.tasks,
            "arms": self.arms,
            "arm_configs": self.arm_configs,
            "repetitions": self.repetitions,
            "random_seed": self.random_seed,
            "cache_conditions": self.cache_conditions,
            "manifest_hash": self.manifest_hash,
            "slots": [s.to_dict() for s in self.slots],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignManifest":
        slots = [CampaignSlot.from_dict(s) for s in data.get("slots", [])]
        return cls(
            campaign_id=data["campaign_id"],
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            tasks=data.get("tasks", []),
            arms=data.get("arms", []),
            arm_configs=data.get("arm_configs", {}),
            repetitions=data.get("repetitions", 1),
            random_seed=data.get("random_seed"),
            cache_conditions=data.get("cache_conditions", ["cold"]),
            slots=slots,
            manifest_hash=data.get("manifest_hash", ""),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "CampaignManifest":
        return cls.from_dict(json.loads(json_str))

    def save(self, path: Path) -> Path:
        """Save manifest to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json(), encoding="utf-8")
        return p

    @classmethod
    def load(cls, path: Path) -> "CampaignManifest":
        """Load manifest from a JSON file."""
        p = Path(path)
        return cls.from_json(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Campaign Matrix Planner (REP-01)
# ---------------------------------------------------------------------------

def plan_campaign(
    tasks: List[Union[str, Dict[str, Any]]],
    arms: Optional[List[str]] = None,
    repetitions: int = 1,
    random_seed: Optional[int] = None,
    cache_conditions: Optional[List[str]] = None,
    model: str = "gemini-2.5-pro",
    model_settings: Optional[Dict[str, Any]] = None,
    resource_budget: Optional[Dict[str, Any]] = None,
    arm_configs: Optional[Dict[str, Dict[str, Any]]] = None,
    campaign_id: Optional[str] = None,
) -> CampaignManifest:
    """
    Schedule controlled evaluation matrices: Tasks × Arms × Repetitions with predeclared, randomized arm order (REP-01).

    Args:
        tasks: List of task IDs or task specification dictionaries.
        arms: List of arms to evaluate (e.g., ["baseline", "icm"] or ["baseline", "icm", "delegation"]).
        repetitions: Number of repetitions per task × arm combination.
        random_seed: Seed for reproducible arm order randomization. If None, a deterministic seed is generated and recorded.
        cache_conditions: List of cache conditions to stratify (default ["cold"], or ["cold", "warm"]).
        model: Target model identifier.
        model_settings: Model sampling parameters (temperature, top_p, etc.).
        resource_budget: Resource budgets (timeout_seconds, max_cost_usd, max_turns).
        arm_configs: Custom arm configurations mapping arm name to settings.
        campaign_id: Unique campaign identifier.
    """
    if not tasks:
        raise ValueError("Campaign must include at least one task.")
    if repetitions < 1:
        raise ValueError("Campaign repetitions must be >= 1.")

    selected_arms = list(arms or ["baseline", "icm"])
    for a in selected_arms:
        if a not in SUPPORTED_ARMS and (arm_configs is None or a not in arm_configs):
            raise ValueError(f"Unsupported arm '{a}'. Supported arms: {SUPPORTED_ARMS}")

    normalized_tasks: List[Dict[str, Any]] = []
    for t in tasks:
        if isinstance(t, str):
            normalized_tasks.append({"task_id": t, "task_version": "1.0.0"})
        elif isinstance(t, dict):
            if "task_id" not in t:
                raise ValueError("Task dict must contain 'task_id'.")
            normalized_tasks.append({
                "task_id": t["task_id"],
                "task_version": t.get("task_version", "1.0.0"),
                "description": t.get("description", ""),
            })

    active_cache_conds = list(cache_conditions or ["cold"])
    for c in active_cache_conds:
        if c not in CACHE_CONDITIONS:
            raise ValueError(f"Unsupported cache condition '{c}'. Supported: {CACHE_CONDITIONS}")

    final_arm_configs: Dict[str, Dict[str, Any]] = {}
    for a in selected_arms:
        cfg = dict(DEFAULT_ARM_CONFIGS.get(a, {"arm": a, "model": model}))
        if arm_configs and a in arm_configs:
            cfg.update(arm_configs[a])
        final_arm_configs[a] = cfg

    effective_seed = random_seed if random_seed is not None else 42
    rng = random.Random(effective_seed)

    cid = campaign_id or f"cmp_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{effective_seed}"

    slots: List[CampaignSlot] = []
    planned_order_seq = 1

    default_settings = model_settings or {"temperature": 0.0, "top_p": 1.0}
    default_budget = resource_budget or {"timeout_seconds": 600.0, "max_cost_usd": 10.0, "max_turns": 10}

    # Generate matrix: Tasks × Repetitions × Cache Conditions × Randomized Arms
    for task_info in normalized_tasks:
        tid = task_info["task_id"]
        tver = task_info["task_version"]

        for rep_idx in range(1, repetitions + 1):
            for cond in active_cache_conds:
                # Predeclared randomized arm order within this block (REP-01)
                shuffled_arms = list(selected_arms)
                rng.shuffle(shuffled_arms)

                for arm_name in shuffled_arms:
                    slot_id = f"{cid}_{tid}_rep{rep_idx}_{arm_name}_{cond}"
                    slot = CampaignSlot(
                        slot_id=slot_id,
                        campaign_id=cid,
                        task_id=tid,
                        task_version=tver,
                        repetition_index=rep_idx,
                        arm=arm_name,
                        planned_order=planned_order_seq,
                        cache_condition=cond,
                        intended_cache_condition=cond,
                        observed_cache_condition="unknown",
                        model=model,
                        model_settings=copy.deepcopy(default_settings),
                        resource_budget=copy.deepcopy(default_budget),
                        status="scheduled",
                    )
                    slots.append(slot)
                    planned_order_seq += 1

    manifest = CampaignManifest(
        campaign_id=cid,
        created_at=datetime.now(timezone.utc).isoformat(),
        tasks=normalized_tasks,
        arms=selected_arms,
        arm_configs=final_arm_configs,
        repetitions=repetitions,
        random_seed=effective_seed,
        cache_conditions=active_cache_conds,
        slots=slots,
    )
    manifest.manifest_hash = manifest.compute_manifest_hash()
    return manifest


# ---------------------------------------------------------------------------
# Offline & Fixture Campaign Execution (REP-01, REP-02)
# ---------------------------------------------------------------------------

def simulate_slot_execution(
    slot: CampaignSlot,
    outcome: str = "completed",
    passed: bool = True,
    input_tokens: Optional[int] = 25000,
    output_tokens: Optional[int] = 1200,
    cache_read_tokens: Optional[int] = 5000,
    thinking_tokens: Optional[int] = 100,
    cost_usd: Optional[float] = None,
    cost_status: Optional[str] = None,
    duration_seconds: float = 12.0,
    num_turns: int = 3,
    error_message: Optional[str] = None,
    exclusion_reasons: Optional[List[str]] = None,
    observed_cache_condition: Optional[str] = None,
) -> CampaignSlot:
    """
    Update a slot with simulated execution outcome without live network calls (REP-02).
    Retains all scheduled attempts (completed, failed, timed-out, unexecuted, interrupted).
    """
    slot.status = outcome
    slot.execution_status = outcome
    slot.duration_seconds = duration_seconds
    slot.num_turns = num_turns
    slot.error_message = error_message
    slot.exclusion_reasons = list(exclusion_reasons or [])
    if observed_cache_condition is not None:
        slot.observed_cache_condition = observed_cache_condition

    if outcome == "unexecuted":
        slot.verification_status = "not_run"
        slot.cost_status = "unknown"
        slot.cost_usd = None
        slot.input_tokens = None
        slot.output_tokens = None
        slot.total_tokens = None
        return slot

    if outcome == "completed":
        slot.verification_status = "passed" if passed else "failed"
    elif outcome in ("timed_out", "failed", "interrupted"):
        slot.verification_status = "failed"
    else:
        slot.verification_status = "not_run"

    slot.input_tokens = input_tokens
    slot.output_tokens = output_tokens
    slot.cache_read_tokens = cache_read_tokens
    slot.thinking_tokens = thinking_tokens

    if input_tokens is not None and output_tokens is not None:
        slot.total_tokens = input_tokens + output_tokens + (thinking_tokens or 0)
    else:
        slot.total_tokens = None

    slot.cost_usd = cost_usd
    slot.cost_status = cost_status or ("usage_estimate" if cost_usd is not None else "unknown")

    return slot


def execute_campaign_mock(
    manifest: CampaignManifest,
    slot_outcomes: Optional[Dict[str, Dict[str, Any]]] = None,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
) -> CampaignManifest:
    """
    Execute campaign offline by updating all slots and optionally recording them into a ledger.
    Every scheduled attempt is retained (REP-02).
    """
    manifest_copy = copy.deepcopy(manifest)
    outcomes = slot_outcomes or {}

    db_conn = None
    should_close = False
    if conn is not None:
        db_conn = conn
    elif db_path is not None:
        db_conn = ledger.get_connection(db_path)
        should_close = True

    try:
        for slot in manifest_copy.slots:
            if slot.slot_id in outcomes:
                cfg = outcomes[slot.slot_id]
                simulate_slot_execution(slot, **cfg)
            else:
                # Default completed passing execution
                simulate_slot_execution(
                    slot,
                    outcome="completed",
                    passed=True,
                    input_tokens=25000 if slot.arm == "baseline" else 15000,
                    output_tokens=1200 if slot.arm == "baseline" else 800,
                    cache_read_tokens=5000 if slot.arm == "baseline" else 8000,
                    cost_usd=0.08 if slot.arm == "baseline" else 0.04,
                )

            if db_conn is not None:
                run_dict = slot.to_ledger_run()
                run_id = ledger.record_run(
                    task_id=run_dict["task_id"],
                    arm=run_dict["arm"],
                    model=run_dict["model"],
                    run_index=run_dict["run_index"],
                    timestamp=run_dict["timestamp"],
                    input_tokens=run_dict["input_tokens"],
                    output_tokens=run_dict["output_tokens"],
                    thinking_tokens=run_dict["thinking_tokens"],
                    cache_read_tokens=run_dict["cache_read_tokens"],
                    total_tokens=run_dict["total_tokens"],
                    num_turns=run_dict["num_turns"],
                    duration_seconds=run_dict["duration_seconds"],
                    source_kind=run_dict["source_kind"],
                    evidence_status=run_dict["evidence_status"],
                    exclusion_reasons=run_dict["exclusion_reasons"],
                    cost_status=run_dict["cost_status"],
                    cost_usd=run_dict["cost_usd"],
                    is_simulation=run_dict["is_simulation"],
                    notes=run_dict["notes"],
                    execution_status=run_dict["execution_status"],
                    verification_status=run_dict["verification_status"],
                    manifest_id=run_dict["manifest_id"],
                    conn=db_conn,
                )
                slot.run_id = run_id
    finally:
        if should_close and db_conn is not None:
            db_conn.close()

    return manifest_copy


# ---------------------------------------------------------------------------
# Campaign Report Generator (REP-02 to REP-10)
# ---------------------------------------------------------------------------

def _slot_has_valid_cost(slot: CampaignSlot) -> bool:
    """Determine if an executed slot has complete, usable token and cost data (Finding 3)."""
    if slot.status not in ("completed", "failed", "timed_out", "interrupted"):
        return False
    if slot.input_tokens is None or slot.output_tokens is None:
        return False
    if slot.cost_status in ("unavailable", "incomplete", "unknown"):
        return False
    if slot.cost_usd is None:
        return False
    disqualifying = {"missing_usage_telemetry", "partial_telemetry", "cost_incomplete", "cost_unavailable", "cost_unknown"}
    if any(r in disqualifying for r in slot.exclusion_reasons):
        return False
    return True


def _evaluate_slot_eligibility(slot: CampaignSlot, capture_policy: str = "approved") -> Dict[str, Any]:
    """Evaluate slot through shared ledger eligibility rules (Finding 1)."""
    run_dict = slot.to_ledger_run()
    return ledger.evaluate_run_eligibility(run_dict, capture_policy=capture_policy)


def _is_slot_empirical_measured(slot: CampaignSlot, capture_policy: str = "approved") -> bool:
    """Determine if a slot qualifies as an empirical measured run under shared ledger rules (Finding 1)."""
    if slot.is_simulation or slot.source_kind != "live":
        return False
    elig = _evaluate_slot_eligibility(slot, capture_policy=capture_policy)
    return bool(elig.get("is_measurement_eligible") and elig.get("category") == "measured")


def _is_slot_cost_eligible(slot: CampaignSlot) -> bool:
    """Determine if a completed slot qualifies for cost and token measurement."""
    if slot.status != "completed":
        return False
    return _slot_has_valid_cost(slot)


def _compute_arm_metrics(
    arm_slots: List[CampaignSlot],
    empirical_only: bool = False,
    capture_policy: str = "approved",
) -> Dict[str, Any]:
    """Compute decoupled correctness and cost metrics for a single arm (REP-03, REP-06, REP-07, Findings 1, 2 & 3)."""
    n_scheduled = len(arm_slots)
    if n_scheduled == 0:
        return {
            "n_scheduled": 0,
            "n_executed": 0,
            "executed_attempts_count": 0,
            "sample_count": 0,
            "passed_count": 0,
            "failed_count": 0,
            "evaluator_error_count": 0,
            "attempt_success_rate": None,
            "verified_success_rate": None,
            "evaluated_success_rate": None,
            "evaluation_coverage": 0.0,
            "cost_eligible_sample_count": 0,
            "cost_excluded_sample_count": 0,
            "cost_exclusion_reasons": [],
            "mean_cost_usd": None,
            "min_cost_usd": None,
            "max_cost_usd": None,
            "mean_input_tokens": None,
            "mean_output_tokens": None,
            "mean_cache_read_tokens": None,
            "mean_total_tokens": None,
            "mean_duration_seconds": None,
            "mean_num_turns": None,
            "cost_per_success": None,
            "cost_per_success_type": "undefined",
            "cost_per_success_reason": "no_attempts",
            "has_missing_spend": False,
            "missing_cost_sample_count": 0,
        }

    executed_slots = [s for s in arm_slots if s.status in ("completed", "failed", "timed_out", "interrupted")]
    n_executed = len(executed_slots)

    # 1. Correctness evaluation (decoupled from cost telemetry - REP-07, Finding 2)
    evaluated_slots = [s for s in arm_slots if s.verification_status in ("passed", "failed", "evaluator_error")]
    passed_slots = [s for s in evaluated_slots if s.verification_status == "passed"]
    failed_slots = [s for s in evaluated_slots if s.verification_status in ("failed", "evaluator_error")]
    evaluator_error_slots = [s for s in evaluated_slots if s.verification_status == "evaluator_error"]

    attempt_success_rate = (len(passed_slots) / n_executed) if n_executed > 0 else None
    # Verified success rate divides by executed attempts per REP-02/Finding 2
    verified_success_rate = attempt_success_rate
    evaluated_success_rate = (len(passed_slots) / len(evaluated_slots)) if evaluated_slots else None
    evaluation_coverage = (len(evaluated_slots) / n_executed) if n_executed > 0 else 0.0

    # 2. Cost completeness & eligibility (REP-07, Finding 1)
    if empirical_only:
        cost_eligible_slots = [
            s for s in arm_slots
            if _is_slot_cost_eligible(s) and _is_slot_empirical_measured(s, capture_policy=capture_policy)
        ]
        cost_excluded_slots = [
            s for s in arm_slots
            if not (_is_slot_cost_eligible(s) and _is_slot_empirical_measured(s, capture_policy=capture_policy))
        ]
    else:
        cost_eligible_slots = [s for s in arm_slots if _is_slot_cost_eligible(s)]
        cost_excluded_slots = [s for s in arm_slots if not _is_slot_cost_eligible(s)]

    cost_exclusion_reasons = []
    for s in cost_excluded_slots:
        if s.status != "completed":
            cost_exclusion_reasons.append(f"status_{s.status}")
        elif empirical_only and not _is_slot_empirical_measured(s, capture_policy=capture_policy):
            cost_exclusion_reasons.append("mixed_population_fixture_excluded")
        elif s.input_tokens is None or s.output_tokens is None:
            cost_exclusion_reasons.append("missing_usage_telemetry")
        elif s.cost_status in ("unavailable", "incomplete", "unknown"):
            cost_exclusion_reasons.append(f"cost_{s.cost_status}")
        elif s.cost_usd is None:
            cost_exclusion_reasons.append("missing_cost_calculation")
        for r in s.exclusion_reasons:
            if r not in cost_exclusion_reasons:
                cost_exclusion_reasons.append(r)

    # Token & cost aggregations on eligible completed runs
    valid_costs = [s.cost_usd for s in cost_eligible_slots if s.cost_usd is not None]
    valid_inputs = [s.input_tokens for s in cost_eligible_slots if s.input_tokens is not None]
    valid_outputs = [s.output_tokens for s in cost_eligible_slots if s.output_tokens is not None]
    valid_caches = [s.cache_read_tokens for s in cost_eligible_slots if s.cache_read_tokens is not None]
    valid_totals = [s.total_tokens for s in cost_eligible_slots if s.total_tokens is not None]
    valid_durations = [s.duration_seconds for s in cost_eligible_slots if s.duration_seconds is not None]
    valid_turns = [s.num_turns for s in cost_eligible_slots if s.num_turns is not None]

    mean_cost = (sum(valid_costs) / len(valid_costs)) if valid_costs else None
    min_cost = min(valid_costs) if valid_costs else None
    max_cost = max(valid_costs) if valid_costs else None

    # 3. Cost per success (Findings 2 & 3):
    # Include all known failure/timeout spend across executed attempts, and disclose missing spend
    if empirical_only:
        executed_with_cost = [
            s for s in executed_slots
            if _slot_has_valid_cost(s) and _is_slot_empirical_measured(s, capture_policy=capture_policy)
        ]
        executed_missing_cost = [
            s for s in executed_slots
            if not (_slot_has_valid_cost(s) and _is_slot_empirical_measured(s, capture_policy=capture_policy))
        ]
        cost_eligible_passed = [
            s for s in passed_slots
            if _is_slot_cost_eligible(s) and _is_slot_empirical_measured(s, capture_policy=capture_policy)
        ]
    else:
        executed_with_cost = [s for s in executed_slots if _slot_has_valid_cost(s)]
        executed_missing_cost = [s for s in executed_slots if not _slot_has_valid_cost(s)]
        cost_eligible_passed = [s for s in passed_slots if _is_slot_cost_eligible(s)]
    has_missing_spend = len(executed_missing_cost) > 0
    missing_cost_sample_count = len(executed_missing_cost)

    total_arm_spend = sum(s.cost_usd for s in executed_with_cost if s.cost_usd is not None)

    if len(passed_slots) == 0:
        cost_per_success = None
        cost_per_success_type = "undefined"
        cost_per_success_reason = "no_successful_runs"
    elif len(cost_eligible_passed) == 0:
        cost_per_success = None
        cost_per_success_type = "undefined"
        cost_per_success_reason = "missing_cost_data"
    else:
        cost_per_success = total_arm_spend / len(cost_eligible_passed)
        if has_missing_spend:
            cost_per_success_type = "partial_observed"
            cost_per_success_reason = "partial_cost_coverage"
        else:
            cost_per_success_type = "complete"
            cost_per_success_reason = None

    return {
        "n_scheduled": n_scheduled,
        "n_executed": n_executed,
        "executed_attempts_count": n_executed,
        "sample_count": n_executed,
        "passed_count": len(passed_slots),
        "failed_count": len(failed_slots),
        "evaluator_error_count": len(evaluator_error_slots),
        "attempt_success_rate": attempt_success_rate,
        "verified_success_rate": verified_success_rate,
        "evaluated_success_rate": evaluated_success_rate,
        "evaluation_coverage": evaluation_coverage,
        "cost_eligible_sample_count": len(cost_eligible_slots),
        "cost_excluded_sample_count": len(cost_excluded_slots),
        "cost_exclusion_reasons": sorted(list(set(cost_exclusion_reasons))),
        "mean_cost_usd": mean_cost,
        "min_cost_usd": min_cost,
        "max_cost_usd": max_cost,
        "mean_input_tokens": (sum(valid_inputs) / len(valid_inputs)) if valid_inputs else None,
        "mean_output_tokens": (sum(valid_outputs) / len(valid_outputs)) if valid_outputs else None,
        "mean_cache_read_tokens": (sum(valid_caches) / len(valid_caches)) if valid_caches else None,
        "mean_total_tokens": (sum(valid_totals) / len(valid_totals)) if valid_totals else None,
        "mean_duration_seconds": (sum(valid_durations) / len(valid_durations)) if valid_durations else None,
        "mean_num_turns": (sum(valid_turns) / len(valid_turns)) if valid_turns else None,
        "cost_per_success": cost_per_success,
        "cost_per_success_type": cost_per_success_type,
        "cost_per_success_reason": cost_per_success_reason,
        "has_missing_spend": has_missing_spend,
        "missing_cost_sample_count": missing_cost_sample_count,
    }


def _compute_savings_and_pairs(
    slots: List[CampaignSlot],
    arms_summary: Dict[str, Any],
    empirical_only: bool = False,
    capture_policy: str = "approved",
) -> Dict[str, Any]:
    """
    Compute savings, paired differences, and handle edge cases across all evaluated arms:
    - REP-05: Zero baseline cost -> savings percentage undefined (None), absolute numbers reported.
    - REP-08: Missing member in pair -> excluded from paired differences; missing-pair count reported.
    - Supports multi-arm comparisons (Arm A vs Arm B, Arm A vs Arm C).
    - Finding 1: When empirical_only is True, fixtures/simulations in mixed populations cannot enter empirical paired differences.
    """
    comparison_arms = [k for k in arms_summary.keys() if k != "baseline"]
    primary_gov_arm = "icm" if "icm" in comparison_arms else ("delegation" if "delegation" in comparison_arms else (comparison_arms[0] if comparison_arms else None))

    savings_by_arm: Dict[str, Any] = {}
    paired_by_arm: Dict[str, Any] = {}

    if "baseline" in arms_summary and comparison_arms:
        b_summary = arms_summary["baseline"]
        base_mean = b_summary.get("mean_cost_usd")

        for gov_arm in comparison_arms:
            g_summary = arms_summary[gov_arm]
            gov_mean = g_summary.get("mean_cost_usd")
            s_out = None

            if base_mean is not None and gov_mean is not None:
                abs_diff = base_mean - gov_mean

                # REP-05: Zero baseline cost
                if base_mean == 0.0:
                    pct_savings = None
                    pct_reason = "zero_baseline_cost"
                elif base_mean > 0.0:
                    pct_savings = (abs_diff / base_mean) * 100.0
                    pct_reason = None
                else:
                    pct_savings = None
                    pct_reason = "negative_baseline_cost"

                token_diff = (
                    (b_summary["mean_total_tokens"] - g_summary["mean_total_tokens"])
                    if (b_summary.get("mean_total_tokens") is not None and g_summary.get("mean_total_tokens") is not None)
                    else None
                )

                s_out = {
                    "governed_arm": gov_arm,
                    "absolute_savings_usd": abs_diff,
                    "savings_percentage": pct_savings,
                    "savings_percentage_reason": pct_reason,
                    "total_tokens_saved": token_diff,
                    "baseline_mean_cost_usd": base_mean,
                    "governed_mean_cost_usd": gov_mean,
                }
            savings_by_arm[gov_arm] = s_out

            # Paired differences analysis (REP-08)
            pair_groups: Dict[Tuple[str, int, str], Dict[str, CampaignSlot]] = {}
            for s in slots:
                if s.arm in ("baseline", gov_arm):
                    pkey = (s.task_id, s.repetition_index, s.cache_condition)
                    if pkey not in pair_groups:
                        pair_groups[pkey] = {}
                    pair_groups[pkey][s.arm] = s

            total_pairs = len(pair_groups)
            complete_pairs = []
            incomplete_count = 0

            for pkey, arm_map in pair_groups.items():
                b_s = arm_map.get("baseline")
                g_s = arm_map.get(gov_arm)

                b_cost_ok = (
                    b_s is not None
                    and _is_slot_cost_eligible(b_s)
                    and (not empirical_only or _is_slot_empirical_measured(b_s, capture_policy=capture_policy))
                )
                g_cost_ok = (
                    g_s is not None
                    and _is_slot_cost_eligible(g_s)
                    and (not empirical_only or _is_slot_empirical_measured(g_s, capture_policy=capture_policy))
                )

                if (
                    b_cost_ok
                    and g_cost_ok
                    and b_s is not None
                    and g_s is not None
                    and b_s.cost_usd is not None
                    and g_s.cost_usd is not None
                ):
                    diff = b_s.cost_usd - g_s.cost_usd
                    complete_pairs.append({
                        "task_id": pkey[0],
                        "repetition_index": pkey[1],
                        "cache_condition": pkey[2],
                        "baseline_cost_usd": b_s.cost_usd,
                        "governed_cost_usd": g_s.cost_usd,
                        "cost_difference_usd": diff,
                    })
                else:
                    incomplete_count += 1

            mean_paired = (
                (sum(p["cost_difference_usd"] for p in complete_pairs) / len(complete_pairs))
                if complete_pairs
                else None
            )

            paired_by_arm[gov_arm] = {
                "governed_arm": gov_arm,
                "total_planned_pairs": total_pairs,
                "complete_pairs_count": len(complete_pairs),
                "missing_or_incomplete_pairs_count": incomplete_count,
                "mean_paired_cost_difference_usd": mean_paired,
                "paired_cost_differences": complete_pairs,
            }

    primary_savings = copy.deepcopy(savings_by_arm.get(primary_gov_arm)) if primary_gov_arm and savings_by_arm.get(primary_gov_arm) else None
    if primary_savings:
        primary_savings["by_arm"] = savings_by_arm

    primary_paired = copy.deepcopy(paired_by_arm.get(primary_gov_arm)) if primary_gov_arm and paired_by_arm.get(primary_gov_arm) else {
        "total_planned_pairs": 0,
        "complete_pairs_count": 0,
        "missing_or_incomplete_pairs_count": 0,
        "mean_paired_cost_difference_usd": None,
        "paired_cost_differences": [],
    }
    primary_paired["by_arm"] = paired_by_arm

    return {"savings": primary_savings, "paired_differences": primary_paired}


def _compute_single_stratum_summary(
    stratum_slots: List[CampaignSlot],
    arms: List[str],
    capture_policy: str = "approved",
) -> Dict[str, Any]:
    """Compute metrics for a homogenous stratum of slots."""
    total_scheduled = len(stratum_slots)
    completed_slots = [s for s in stratum_slots if s.status == "completed"]
    failed_slots = [s for s in stratum_slots if s.status == "failed"]
    timed_out_slots = [s for s in stratum_slots if s.status == "timed_out"]
    unexecuted_slots = [s for s in stratum_slots if s.status == "unexecuted"]
    interrupted_slots = [s for s in stratum_slots if s.status == "interrupted"]

    total_executed = len(completed_slots) + len(failed_slots) + len(timed_out_slots) + len(interrupted_slots)

    # Finding 1: Empirical measurement eligibility via shared ledger rules
    empirical_measured_slots = [s for s in stratum_slots if _is_slot_empirical_measured(s, capture_policy=capture_policy)]
    has_measured_data = len(empirical_measured_slots) > 0
    is_demo_report = (not has_measured_data) and (total_executed > 0 or any(s.cost_usd is not None for s in stratum_slots))

    measured_totals = None
    if has_measured_data:
        measured_totals = {
            "total_cost_usd": sum(s.cost_usd for s in empirical_measured_slots if s.cost_usd is not None),
            "total_tokens": sum(s.total_tokens for s in empirical_measured_slots if s.total_tokens is not None),
            "measured_runs_count": len(empirical_measured_slots),
        }

    # Per-arm calculations
    arms_summary: Dict[str, Any] = {}
    sample_counts: Dict[str, int] = {}
    scheduled_counts: Dict[str, int] = {}
    for arm in arms:
        arm_slots = [s for s in stratum_slots if s.arm == arm]
        arm_res = _compute_arm_metrics(arm_slots, empirical_only=has_measured_data, capture_policy=capture_policy)
        arms_summary[arm] = arm_res
        sample_counts[arm] = arm_res["sample_count"]
        scheduled_counts[arm] = arm_res["n_scheduled"]

    # REP-03: Uneven sample counts (check both scheduled and executed)
    sample_values = list(sample_counts.values())
    scheduled_values = list(scheduled_counts.values())
    is_balanced = (
        (len(set(sample_values)) <= 1) and (len(set(scheduled_values)) <= 1)
        if sample_values and scheduled_values
        else True
    )
    balance_status = "balanced" if is_balanced else "uneven"

    # Savings & paired differences
    sp_res = _compute_savings_and_pairs(stratum_slots, arms_summary, empirical_only=has_measured_data, capture_policy=capture_policy)

    status = "completed" if has_measured_data else ("demo_report" if is_demo_report else "no_eligible_measured_runs")
    if total_scheduled == 0:
        status = "empty"

    return {
        "status": status,
        "has_measured_data": has_measured_data,
        "is_demo_report": is_demo_report,
        "measured_runs_count": len(empirical_measured_slots),
        "measured_totals": measured_totals,
        "total_scheduled": total_scheduled,
        "total_executed": total_executed,
        "execution_coverage_pct": (total_executed / total_scheduled * 100.0) if total_scheduled > 0 else 0.0,
        "status_counts": {
            "completed": len(completed_slots),
            "failed": len(failed_slots),
            "timed_out": len(timed_out_slots),
            "unexecuted": len(unexecuted_slots),
            "interrupted": len(interrupted_slots),
        },
        "sample_counts": sample_counts,
        "scheduled_counts": scheduled_counts,
        "is_balanced": is_balanced,
        "balance_status": balance_status,
        "arms": arms_summary,
        "savings": sp_res["savings"],
        "paired_differences": sp_res["paired_differences"],
    }


def generate_campaign_report(
    manifest: Optional[CampaignManifest] = None,
    slots: Optional[List[CampaignSlot]] = None,
    runs: Optional[List[Dict[str, Any]]] = None,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
    campaign_id: Optional[str] = None,
    pooling_method: str = "macro_average",  # "macro_average" or "micro_sum"
    strict_manifest: bool = True,
    capture_policy: str = "approved",
) -> Dict[str, Any]:
    """
    Generate comprehensive campaign report covering REP-02 through REP-10.
    Enforces manifest integrity, schedule reconciliation, and shared ledger eligibility rules (Findings 1, 2, 3, 4).

    Args:
        manifest: Pre-planned campaign manifest with slots.
        slots: Direct list of CampaignSlot objects.
        runs: Direct list of run dictionaries (e.g. from ledger).
        conn: Optional SQLite connection to read runs.
        db_path: Optional SQLite database path.
        campaign_id: Optional campaign ID filter for database runs.
        pooling_method: 'macro_average' (unweighted average of per-task means) or 'micro_sum' (aggregate pooled sum).
        strict_manifest: If True, enforce non-empty valid manifest_hash when manifest is supplied.
        capture_policy: Policy for evidence validation ('approved', 'permissive', etc.).
    """
    # Finding 4: Enforce manifest integrity validation before reporting
    if manifest is not None:
        if not manifest.manifest_hash:
            if strict_manifest:
                raise ValueError("Campaign manifest lacks a manifest_hash. Manifest integrity cannot be verified in strict mode.")
        elif not manifest.verify_integrity():
            raise ValueError(f"Campaign manifest integrity verification failed: manifest_hash {manifest.manifest_hash} does not match computed plan hash.")

    active_slots: List[CampaignSlot] = []

    # 1. Harvest slots
    if slots:
        active_slots = [CampaignSlot.from_dict(s.to_dict()) if isinstance(s, CampaignSlot) else CampaignSlot.from_dict(s) for s in slots]
    elif manifest:
        active_slots = [CampaignSlot.from_dict(s.to_dict()) for s in manifest.slots]

    effective_cid = campaign_id or (manifest.campaign_id if manifest else None)

    # 2. Enrich or import from runs/ledger if supplied
    all_runs: List[Dict[str, Any]] = []
    if runs:
        all_runs = list(runs)
    elif conn is not None or db_path is not None:
        db_conn = conn or ledger.get_connection(db_path)
        should_close = (conn is None)
        try:
            cursor = db_conn.cursor()
            if effective_cid:
                cursor.execute("SELECT * FROM runs WHERE manifest_id = ? ORDER BY id", (effective_cid,))
            else:
                cursor.execute("SELECT * FROM runs ORDER BY id")
            all_runs = [dict(r) for r in cursor.fetchall()]
        finally:
            if should_close:
                db_conn.close()

    def _run_to_slot(r: Dict[str, Any]) -> CampaignSlot:
        notes_raw = r.get("notes")
        parsed_notes: Dict[str, Any] = {}
        if isinstance(notes_raw, str):
            try:
                parsed_notes = json.loads(notes_raw)
            except Exception:
                pass

        slot_id = str(parsed_notes.get("slot_id") or "")
        if not slot_id and r.get("id"):
            slot_id = f"run_{r.get('id')}_{r.get('task_id')}_{r.get('arm')}"
        intended_cond = str(parsed_notes.get("intended_cache_condition") or parsed_notes.get("cache_condition") or "cold")
        observed_cond = str(parsed_notes.get("observed_cache_condition") or "unknown")
        order = int(parsed_notes.get("planned_order") or r.get("id") or 1)

        raw_exc = r.get("exclusion_reasons")
        parsed_exc: List[str] = []
        if isinstance(raw_exc, str):
            try:
                p_exc = json.loads(raw_exc)
                if isinstance(p_exc, list):
                    parsed_exc = [str(x) for x in p_exc]
            except Exception:
                pass
        elif isinstance(raw_exc, list):
            parsed_exc = [str(x) for x in raw_exc]

        exec_st = str(r.get("execution_status") or "completed")
        verif_st = str(r.get("verification_status") or "not_run")

        return CampaignSlot(
            slot_id=slot_id,
            campaign_id=str(r.get("manifest_id") or effective_cid or "legacy_campaign"),
            task_id=str(r.get("task_id", "")),
            task_version="1.0.0",
            repetition_index=int(r.get("run_index", 1)),
            arm=str(r.get("arm", "baseline")).lower(),
            planned_order=order,
            cache_condition=intended_cond,
            intended_cache_condition=intended_cond,
            observed_cache_condition=observed_cond,
            model=str(r.get("model", "gemini-2.5-pro")),
            status=exec_st,
            execution_status=exec_st,
            verification_status=verif_st,
            run_id=r.get("id"),
            cost_usd=r.get("cost_usd"),
            cost_status=r.get("cost_status"),
            input_tokens=r.get("input_tokens"),
            output_tokens=r.get("output_tokens"),
            thinking_tokens=r.get("thinking_tokens"),
            cache_read_tokens=r.get("cache_read_tokens"),
            total_tokens=r.get("total_tokens"),
            duration_seconds=r.get("duration_seconds"),
            num_turns=r.get("num_turns"),
            exclusion_reasons=parsed_exc,
            source_kind=str(r.get("source_kind") or "fixture"),
            evidence_status=str(r.get("evidence_status") or "unverified"),
            is_simulation=int(r.get("is_simulation") or 0),
            evidence_ref=r.get("evidence_ref"),
            evidence_hash=r.get("evidence_hash"),
            notes=r.get("notes"),
        )

    # 3. Reconcile database runs into active_slots (Finding 4: require explicit slot IDs, flag duplicates/unscheduled)
    reconciliation_issues: Dict[str, Any] = {
        "duplicate_runs": [],
        "unscheduled_runs": [],
        "mismatched_runs": [],
        "has_schedule_violations": False,
    }

    if active_slots and all_runs:
        slots_by_id = {s.slot_id: s for s in active_slots}
        reconciled_slot_ids: Set[str] = set()

        for r in all_runs:
            s_candidate = _run_to_slot(r)
            cand_id = s_candidate.slot_id

            if cand_id in slots_by_id:
                target_slot = slots_by_id[cand_id]
                # Validate configuration match (task, arm, repetition, model, cache condition)
                cand_task = r.get("task_id")
                cand_arm = str(r.get("arm", "")).lower()
                cand_rep = int(r.get("run_index", 1))
                cand_model = str(r.get("model", "")).lower() if r.get("model") else None
                cand_cache = s_candidate.intended_cache_condition

                is_mismatch = (
                    cand_task != target_slot.task_id
                    or cand_arm != target_slot.arm.lower()
                    or cand_rep != target_slot.repetition_index
                    or (cand_model is not None and target_slot.model and cand_model != target_slot.model.lower())
                    or (cand_cache and target_slot.cache_condition and cand_cache != target_slot.cache_condition)
                )

                if is_mismatch:
                    reconciliation_issues["mismatched_runs"].append({
                        "run_id": r.get("id"),
                        "slot_id": cand_id,
                        "task_id": r.get("task_id"),
                        "expected_task_id": target_slot.task_id,
                        "model": r.get("model"),
                        "expected_model": target_slot.model,
                        "reason": "configuration_mismatch",
                    })
                    continue

                if cand_id in reconciled_slot_ids:
                    # Finding 4: Flag duplicate execution of scheduled slot
                    reconciliation_issues["duplicate_runs"].append({
                        "run_id": r.get("id"),
                        "slot_id": cand_id,
                        "reason": "duplicate_slot_execution",
                    })
                    continue

                reconciled_slot_ids.add(cand_id)
                target_slot.status = s_candidate.status
                target_slot.execution_status = s_candidate.execution_status
                target_slot.verification_status = s_candidate.verification_status
                target_slot.run_id = s_candidate.run_id
                target_slot.cost_usd = s_candidate.cost_usd
                target_slot.cost_status = s_candidate.cost_status
                target_slot.input_tokens = s_candidate.input_tokens
                target_slot.output_tokens = s_candidate.output_tokens
                target_slot.thinking_tokens = s_candidate.thinking_tokens
                target_slot.cache_read_tokens = s_candidate.cache_read_tokens
                target_slot.total_tokens = s_candidate.total_tokens
                target_slot.duration_seconds = s_candidate.duration_seconds
                target_slot.num_turns = s_candidate.num_turns
                target_slot.exclusion_reasons = s_candidate.exclusion_reasons
                target_slot.source_kind = s_candidate.source_kind
                target_slot.evidence_status = s_candidate.evidence_status
                target_slot.is_simulation = s_candidate.is_simulation
                target_slot.evidence_ref = s_candidate.evidence_ref
                target_slot.evidence_hash = s_candidate.evidence_hash
                target_slot.notes = s_candidate.notes
                target_slot.observed_cache_condition = s_candidate.observed_cache_condition
            else:
                # Finding 4: Unscheduled run; do NOT silently append to scheduled active_slots!
                reconciliation_issues["unscheduled_runs"].append({
                    "run_id": r.get("id"),
                    "slot_id": cand_id,
                    "task_id": r.get("task_id"),
                    "arm": r.get("arm"),
                    "reason": "unscheduled_run",
                })

        reconciliation_issues["has_schedule_violations"] = bool(
            reconciliation_issues["duplicate_runs"]
            or reconciliation_issues["unscheduled_runs"]
            or reconciliation_issues["mismatched_runs"]
        )
    elif not active_slots and all_runs:
        for r in all_runs:
            active_slots.append(_run_to_slot(r))

    # REP-04: Honest empty state if no slots exist
    if not active_slots:
        return {
            "campaign_id": (manifest.campaign_id if manifest else (effective_cid or "empty_campaign")),
            "status": "empty",
            "has_measured_data": False,
            "is_demo_report": False,
            "measured_runs_count": 0,
            "measured_totals": None,
            "total_scheduled": 0,
            "total_executed": 0,
            "execution_coverage_pct": 0.0,
            "status_counts": {
                "completed": 0,
                "failed": 0,
                "timed_out": 0,
                "unexecuted": 0,
                "interrupted": 0,
            },
            "sample_counts": {},
            "scheduled_counts": {},
            "is_balanced": True,
            "balance_status": "balanced",
            "has_multiple_strata": False,
            "cache_conditions_present": [],
            "stratification_warning": None,
            "pooling_method": pooling_method,
            "pooling_method_description": "None (no attempts scheduled)",
            "pooled_summary": {
                "arms": {},
                "savings": None,
                "paired_differences": None,
                "is_blended_strata": False,
                "strata_present": None,
            },
            "arms": {},
            "savings": None,
            "paired_differences": None,
            "strata": {},
            "by_task": {},
            "all_attempts": [],
            "reconciliation_issues": reconciliation_issues,
            "message": "No scheduled evaluation attempts or measured runs exist.",
        }

    # Identify all arms and tasks present
    arms = sorted(list(set(s.arm for s in active_slots)))
    tasks = sorted(list(set(s.task_id for s in active_slots)))

    # Identify cache conditions (REP-09)
    cache_conditions_present = sorted(list(set(s.cache_condition for s in active_slots)))
    has_multiple_strata = (len(cache_conditions_present) > 1)

    # 3. Stratified reporting (REP-09: Cold and warm conditions reported separately)
    strata_reports: Dict[str, Any] = {}
    for cond in cache_conditions_present:
        c_slots = [s for s in active_slots if s.cache_condition == cond]
        strata_reports[cond] = _compute_single_stratum_summary(c_slots, arms, capture_policy=capture_policy)

    # 4. Task-level breakdown (REP-10: Large and small tasks coexist)
    by_task: Dict[str, Any] = {}
    for tid in tasks:
        t_slots = [s for s in active_slots if s.task_id == tid]
        by_task[tid] = _compute_single_stratum_summary(t_slots, arms, capture_policy=capture_policy)

    # 5. Pooled summary with explicit pooling method (REP-10)
    overall_summary = _compute_single_stratum_summary(active_slots, arms, capture_policy=capture_policy)

    # If macro_average requested, average per-task means for pooled summary
    if pooling_method == "macro_average" and len(tasks) > 1:
        macro_arms: Dict[str, Any] = {}
        for arm in arms:
            arm_task_means = [by_task[t]["arms"][arm]["mean_cost_usd"] for t in tasks if by_task[t]["arms"][arm]["mean_cost_usd"] is not None]
            arm_task_inputs = [by_task[t]["arms"][arm]["mean_input_tokens"] for t in tasks if by_task[t]["arms"][arm]["mean_input_tokens"] is not None]
            arm_task_outputs = [by_task[t]["arms"][arm]["mean_output_tokens"] for t in tasks if by_task[t]["arms"][arm]["mean_output_tokens"] is not None]
            arm_task_totals = [by_task[t]["arms"][arm]["mean_total_tokens"] for t in tasks if by_task[t]["arms"][arm]["mean_total_tokens"] is not None]
            arm_task_successes = [by_task[t]["arms"][arm]["verified_success_rate"] for t in tasks if by_task[t]["arms"][arm]["verified_success_rate"] is not None]
            arm_task_attempts = [by_task[t]["arms"][arm]["attempt_success_rate"] for t in tasks if by_task[t]["arms"][arm]["attempt_success_rate"] is not None]
            arm_task_evals = [by_task[t]["arms"][arm]["evaluated_success_rate"] for t in tasks if by_task[t]["arms"][arm]["evaluated_success_rate"] is not None]
            arm_task_covs = [by_task[t]["arms"][arm]["evaluation_coverage"] for t in tasks if by_task[t]["arms"][arm]["evaluation_coverage"] is not None]

            macro_arms[arm] = dict(overall_summary["arms"][arm])
            macro_arms[arm]["mean_cost_usd"] = (sum(arm_task_means) / len(arm_task_means)) if arm_task_means else None
            macro_arms[arm]["mean_input_tokens"] = (sum(arm_task_inputs) / len(arm_task_inputs)) if arm_task_inputs else None
            macro_arms[arm]["mean_output_tokens"] = (sum(arm_task_outputs) / len(arm_task_outputs)) if arm_task_outputs else None
            macro_arms[arm]["mean_total_tokens"] = (sum(arm_task_totals) / len(arm_task_totals)) if arm_task_totals else None
            macro_arms[arm]["verified_success_rate"] = (sum(arm_task_successes) / len(arm_task_successes)) if arm_task_successes else None
            macro_arms[arm]["attempt_success_rate"] = (sum(arm_task_attempts) / len(arm_task_attempts)) if arm_task_attempts else None
            macro_arms[arm]["evaluated_success_rate"] = (sum(arm_task_evals) / len(arm_task_evals)) if arm_task_evals else None
            macro_arms[arm]["evaluation_coverage"] = (sum(arm_task_covs) / len(arm_task_covs)) if arm_task_covs else None

        overall_summary["arms"] = macro_arms
        # Recalculate savings under macro averages
        sp_macro = _compute_savings_and_pairs(
            active_slots,
            macro_arms,
            empirical_only=overall_summary["has_measured_data"],
            capture_policy=capture_policy,
        )
        overall_summary["savings"] = sp_macro["savings"]

        # Macro-average paired differences across tasks
        task_paired_diffs = [
            by_task[t]["paired_differences"]["mean_paired_cost_difference_usd"]
            for t in tasks
            if by_task[t].get("paired_differences") and by_task[t]["paired_differences"].get("mean_paired_cost_difference_usd") is not None
        ]
        if task_paired_diffs and overall_summary.get("paired_differences"):
            macro_paired_mean = sum(task_paired_diffs) / len(task_paired_diffs)
            overall_summary["paired_differences"]["mean_paired_cost_difference_usd"] = macro_paired_mean
            overall_summary["paired_differences"]["pooling_method"] = "macro_average"

    pooling_desc = (
        "Macro-average (unweighted arithmetic mean of per-task metrics, preventing token-heavy tasks from dominating pooled statistics)"
        if pooling_method == "macro_average"
        else "Micro-sum (raw aggregation across all attempts regardless of task size)"
    )

    # Attach stratification disclosure (REP-09)
    stratification_warning = None
    if has_multiple_strata:
        stratification_warning = (
            f"Multiple cache conditions detected: {cache_conditions_present}. "
            "Strata are computed separately under 'strata' and must NOT be blended into a homogenous headline."
        )

    return {
        "campaign_id": manifest.campaign_id if manifest else (effective_cid or "ad_hoc_campaign"),
        "has_measured_data": overall_summary["has_measured_data"],
        "is_demo_report": overall_summary.get("is_demo_report", False),
        "measured_runs_count": overall_summary.get("measured_runs_count", 0),
        "measured_totals": overall_summary.get("measured_totals"),
        "status": overall_summary["status"],
        "total_scheduled": overall_summary["total_scheduled"],
        "total_executed": overall_summary["total_executed"],
        "execution_coverage_pct": overall_summary["execution_coverage_pct"],
        "status_counts": overall_summary["status_counts"],
        "sample_counts": overall_summary["sample_counts"],
        "scheduled_counts": overall_summary.get("scheduled_counts", {}),
        "is_balanced": overall_summary["is_balanced"],
        "balance_status": overall_summary["balance_status"],
        "has_multiple_strata": has_multiple_strata,
        "cache_conditions_present": cache_conditions_present,
        "stratification_warning": stratification_warning,
        "pooling_method": pooling_method,
        "pooling_method_description": pooling_desc,
        "pooled_summary": {
            "arms": overall_summary["arms"],
            "savings": overall_summary["savings"],
            "paired_differences": overall_summary["paired_differences"],
            "is_blended_strata": has_multiple_strata,
            "strata_present": cache_conditions_present if has_multiple_strata else None,
        },
        "arms": overall_summary["arms"],
        "savings": overall_summary["savings"],
        "paired_differences": overall_summary["paired_differences"],
        "strata": strata_reports,
        "by_task": by_task,
        "all_attempts": [s.to_dict() for s in active_slots],
        "reconciliation_issues": reconciliation_issues,
    }


# ---------------------------------------------------------------------------
# CLI Command Interface
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Campaign Matrix Planner & Report Generator (Phase 4)")
    subparsers = parser.add_subparsers(dest="command", help="Campaign command to execute")

    # Command: plan
    plan_parser = subparsers.add_parser("plan", help="Generate immutable campaign evaluation matrix (REP-01)")
    plan_parser.add_argument("--tasks", required=True, help="Comma-separated task IDs (e.g. BENCH-001,BENCH-002)")
    plan_parser.add_argument("--arms", default="baseline,icm", help="Comma-separated arms (default: baseline,icm)")
    plan_parser.add_argument("--repetitions", type=int, default=1, help="Repetitions per task-arm slot")
    plan_parser.add_argument("--seed", type=int, default=42, help="Seed for randomized arm ordering")
    plan_parser.add_argument("--cache-conditions", default="cold", help="Comma-separated cache conditions (cold,warm)")
    plan_parser.add_argument("--model", default="gemini-2.5-pro", help="Target model identifier")
    plan_parser.add_argument("--output", default="campaign_manifest.json", help="Path to write manifest JSON")

    # Command: report
    report_parser = subparsers.add_parser("report", help="Generate campaign report from manifest or database")
    report_parser.add_argument("--manifest", help="Path to campaign manifest JSON")
    report_parser.add_argument("--db", help="Path to SQLite database")
    report_parser.add_argument("--campaign-id", help="Filter runs in database to a specific campaign ID")
    report_parser.add_argument("--pooling", choices=["macro_average", "micro_sum"], default="macro_average", help="Task pooling methodology")
    report_parser.add_argument("--output", help="Optional path to write report JSON")

    args = parser.parse_args()

    if args.command == "plan":
        task_list = [t.strip() for t in args.tasks.split(",") if t.strip()]
        arm_list = [a.strip() for a in args.arms.split(",") if a.strip()]
        cond_list = [c.strip() for c in args.cache_conditions.split(",") if c.strip()]

        manifest = plan_campaign(
            tasks=task_list,
            arms=arm_list,
            repetitions=args.repetitions,
            random_seed=args.seed,
            cache_conditions=cond_list,
            model=args.model,
        )
        out_p = Path(args.output)
        manifest.save(out_p)
        print(f"✓ Campaign manifest created with {len(manifest.slots)} scheduled slots: {out_p.resolve()}")
        print(f"  Manifest SHA-256: {manifest.manifest_hash}")

    elif args.command == "report":
        manifest = None
        if args.manifest:
            manifest = CampaignManifest.load(Path(args.manifest))

        report = generate_campaign_report(
            manifest=manifest,
            db_path=Path(args.db) if args.db else None,
            campaign_id=args.campaign_id,
            pooling_method=args.pooling,
        )
        report_json = json.dumps(report, indent=2)
        if args.output:
            Path(args.output).write_text(report_json, encoding="utf-8")
            print(f"✓ Campaign report written to: {Path(args.output).resolve()}")
        else:
            print(report_json)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
