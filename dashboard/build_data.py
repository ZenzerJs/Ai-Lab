#!/usr/bin/env python3
"""
dashboard/build_data.py - Static Data Exporter for Antigravity Savings Dashboard

Extracts normalized runs, per-task metrics, error bands, and cumulative savings
from data/usage.db and writes dashboard/public/data.json.
Gracefully handles empty databases by generating valid schema structures.
"""

import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Add scripts directory to path to import ledger
DASHBOARD_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = DASHBOARD_DIR.parent
SCRIPTS_DIR = WORKSPACE_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ledger
import campaign
from complexity_router import ICM_LITE

# Ensure UTF-8 output encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

OUTPUT_PATH = DASHBOARD_DIR / "public" / "data.json"
OPS_DB_PATH = WORKSPACE_ROOT / "data" / "ops_exp005.db"
GOVERNED_ARMS = ("icm-subagents", "icm", "delegation", "governed", ICM_LITE)


def _governed_key(arms: Dict[str, Any], preferred: Optional[str] = None) -> Optional[str]:
    if preferred and preferred in arms:
        return preferred
    return next((arm for arm in GOVERNED_ARMS if arm in arms), None)


def _arm_bucket(arm: Optional[str]) -> Optional[str]:
    arm = (arm or "").lower()
    if arm == "baseline":
        return arm
    if arm in GOVERNED_ARMS:
        return "icm"
    return None


def get_build_identity() -> str:
    """Return short Git commit SHA or environment build identifier."""
    env_sha = os.environ.get("GITHUB_SHA") or os.environ.get("BUILD_ID")
    if env_sha:
        return env_sha[:8]
    try:
        import subprocess
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "dev-local"


def sanitize_export_text(text: Optional[str]) -> Optional[str]:
    """Redact private file paths and sentinel secrets from public export."""
    if not text:
        return text
    # Windows user paths (both backslash and forward slash)
    cleaned = re.sub(r"[A-Za-z]:[\\/][Uu]sers[\\/][^\\/]+[\\/]", lambda _: r".../...", text)
    # Unix user paths
    cleaned = re.sub(r"/(?:home|Users)/[^/]+/", lambda _: ".../", cleaned)
    # Generic key-value secret patterns: api_key=..., key: ..., token: ..., secret=..., password=...
    cleaned = re.sub(
        r"(?:(?:api[_-]?)?key|secret|token|password|auth|bearer)\s*[:=]\s*[^\s,;\"'}{]+",
        lambda _: "[REDACTED_SECRET]",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Provider-specific key tokens:
    # Google AI Studio / Gemini: AIzaSy...
    cleaned = re.sub(r"AIzaSy[a-zA-Z0-9_-]{30,}", "[REDACTED_SECRET]", cleaned)
    # Anthropic API Key: sk-ant-...
    cleaned = re.sub(r"sk-ant-[a-zA-Z0-9_-]{20,}", "[REDACTED_SECRET]", cleaned)
    # OpenAI API Key: sk-... (including sk-proj-...)
    cleaned = re.sub(r"sk-(?:proj-)?[a-zA-Z0-9_-]{20,}", "[REDACTED_SECRET]", cleaned)
    # GitHub Token: ghp_..., gho_..., github_pat_...
    cleaned = re.sub(r"(?:gh[pours]_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{50,})", "[REDACTED_SECRET]", cleaned)
    return cleaned


def sanitize_export_payload(obj: Any) -> Any:
    """Recursively sanitize string values across nested dictionary and list structures."""
    if isinstance(obj, str):
        return sanitize_export_text(obj)
    elif isinstance(obj, dict):
        return {k: sanitize_export_payload(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_export_payload(item) for item in obj]
    return obj


def build_operational_block(ops_db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Build the EXP-005 operational benchmark block from the isolated ops DB.
    Returns has_data=False (valid empty structure) when the DB is absent —
    operational runs carry turns/duration/outcome only; no token telemetry exists
    for the FreeBuff provider, and none is invented.
    """
    db_file = Path(ops_db_path) if ops_db_path is not None else OPS_DB_PATH
    if not db_file.exists():
        return {"has_data": False, "runs": [], "tasks": []}
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(runs)")
        cols = {row[1] for row in cursor.fetchall()}
        defect_col = next(
            (c for c in ("is_defect", "defect", "has_defect", "defect_runs", "verification_status") if c in cols),
            None,
        )
        extra_select = f", {defect_col}" if defect_col else ""
        cursor.execute(
            f"SELECT task_id, arm, run_index, num_turns, duration_seconds, timestamp{extra_select} "
            "FROM runs WHERE task_id LIKE 'EXP-005%' ORDER BY task_id, arm, run_index"
        )
        raw_rows = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    if not raw_rows:
        return {"has_data": False, "runs": [], "tasks": []}

    runs = [
        {
            "task_id": r["task_id"],
            "arm": r["arm"],
            "run_index": r["run_index"],
            "num_turns": r["num_turns"],
            "duration_seconds": r["duration_seconds"],
            "timestamp": r["timestamp"],
        }
        for r in raw_rows
    ]

    # Aggregate per task/arm
    agg: Dict[str, Dict[str, Dict[str, float]]] = {}
    for r in runs:
        tid, arm = r["task_id"], _arm_bucket(r["arm"])
        if arm is None:
            continue
        agg.setdefault(tid, {}).setdefault(arm, {"n": 0, "turns": 0, "duration": 0.0})
        a = agg[tid][arm]
        a["n"] += 1
        a["turns"] += r["num_turns"]
        a["duration"] += r["duration_seconds"]

    tasks_out: List[Dict[str, Any]] = []
    tot = {"baseline": {"n": 0, "turns": 0, "duration": 0.0}, "icm": {"n": 0, "turns": 0, "duration": 0.0}}
    for tid in sorted(agg):
        entry: Dict[str, Any] = {"task_id": tid}
        for arm in ("baseline", "icm"):
            if arm in agg[tid]:
                a = agg[tid][arm]
                n = a["n"]
                entry[arm] = {
                    "n": n,
                    "mean_turns": round(a["turns"] / n, 1),
                    "mean_duration_seconds": round(a["duration"] / n, 1),
                }
                tot[arm]["n"] += n
                tot[arm]["turns"] += a["turns"]
                tot[arm]["duration"] += a["duration"]
        tasks_out.append(entry)

    def _arm_defect_count(arm_name: str) -> Optional[int]:
        if defect_col is None:
            return None
        arm_rows = [r for r in raw_rows if _arm_bucket(r.get("arm")) == arm_name]
        if not arm_rows:
            return None
        if defect_col == "verification_status":
            verdicts = [
                r.get("verification_status")
                for r in arm_rows
                if r.get("verification_status") in ("passed", "failed", "evaluator_error")
            ]
            if not verdicts:
                return None
            return sum(1 for v in verdicts if v in ("failed", "evaluator_error"))
        vals = [r.get(defect_col) for r in arm_rows if r.get(defect_col) is not None]
        if not vals:
            return None
        if defect_col == "defect_runs":
            return sum(int(v) for v in vals)
        return sum(1 for v in vals if bool(v))

    bn, bturns, bdur = tot["baseline"]["n"], tot["baseline"]["turns"], tot["baseline"]["duration"]
    icm_n, iturns, idur = tot["icm"]["n"], tot["icm"]["turns"], tot["icm"]["duration"]
    summary = {
        "total_runs": len(runs),
        "baseline": {
            "runs": bn,
            "total_turns": bturns,
            "total_duration_seconds": round(bdur, 1),
            "defect_runs": _arm_defect_count("baseline"),
        },
        "icm": {
            "runs": icm_n,
            "total_turns": iturns,
            "total_duration_seconds": round(idur, 1),
            "defect_runs": _arm_defect_count("icm"),
        },
    }
    if bdur > 0:
        summary["duration_overhead_percent"] = round((idur - bdur) / bdur * 100, 1)

    return {
        "has_data": True,
        "model": "glm-5.3-flash",
        "provider": "FreeBuff ($0 direct user cost)",
        "mode": "operational (turns/duration/outcome; no token telemetry exposed)",
        "summary": summary,
        "tasks": tasks_out,
        "runs": runs,
    }


def compute_bootstrap_ci(baseline_vals: List[float], icm_vals: List[float], num_resamples: int = 10000) -> Optional[List[float]]:
    """Compute 95% bootstrap confidence interval for percentage change."""
    if len(baseline_vals) < 3 or len(baseline_vals) != len(icm_vals):
        return None
    import random
    rng = random.Random(9)
    n = len(baseline_vals)
    deltas = []
    for _ in range(num_resamples):
        indices = [rng.randint(0, n - 1) for _ in range(n)]
        b_sum = sum(baseline_vals[i] for i in indices)
        i_sum = sum(icm_vals[i] for i in indices)
        if b_sum > 0:
            deltas.append((b_sum - i_sum) / b_sum * 100.0)
    if not deltas:
        return None
    deltas.sort()
    lo = deltas[int(0.025 * len(deltas))]
    hi = deltas[int(0.975 * len(deltas))]
    return [round(lo, 1), round(hi, 1)]


def build_declared_benchmarks(
    tasks: List[Dict[str, Any]],
    runs: Optional[List[Dict[str, Any]]] = None,
    benchmarks_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Cross-check declared benchmarks/BENCH-* directories against measured runs."""
    root = benchmarks_dir if benchmarks_dir is not None else (WORKSPACE_ROOT / "benchmarks")
    if not root.exists() or not root.is_dir():
        return []
    declared = sorted(
        p.name for p in root.iterdir() if p.is_dir() and p.name.startswith("BENCH-")
    )
    counts: Dict[str, int] = {}
    if runs is not None:
        for r in runs:
            tid = r.get("task_id")
            if (
                tid
                and r.get("source_kind") == "live"
                and not r.get("is_simulation")
                and r.get("evidence_status") not in ("unverified", "invalid", "missing")
            ):
                counts[tid] = counts.get(tid, 0) + 1
    else:
        for t in tasks:
            tid = t.get("task_id")
            if (
                tid
                and t.get("has_measured_data")
                and not t.get("is_simulation")
                and not t.get("is_demo_report")
            ):
                measured = t.get("measured_runs_count")
                counts[tid] = counts.get(tid, 0) + int(
                    measured if measured is not None else (t.get("total_runs") or 0)
                )
    return [
        {
            "task_id": tid,
            "measured_runs": counts.get(tid, 0),
            "status": "measured" if counts.get(tid, 0) > 0 else "suite present, unmeasured",
        }
        for tid in declared
    ]


def build_headline_block(
    tasks: List[Dict[str, Any]],
    cum: Dict[str, Any],
    operational: Optional[Dict[str, Any]] = None,
    total_runs: Optional[int] = None,
    priced_runs: Optional[int] = None,
    billed_direct_runs: Optional[int] = None,
    acu_derived_runs: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Construct high-impact headline metrics with strict honesty invariants.
    Zero fabricated numbers; returns None if qualifying empirical evidence is insufficient.
    """
    stats = []
    sentence = None
    scope = None

    # H1: Delta cost per passing task (%)
    # Requires >= 1 task with valid measured data
    valid_tasks = [t for t in tasks if t.get("has_measured_data") and t.get("savings")]
    counts = cum.get("per_arm_counts", {})
    b_pac = counts.get("baseline", {})
    task_arms = [(t, _governed_key(t["arms"], t.get("governed_arm"))) for t in valid_tasks]
    governed_keys = {key for _, key in task_arms if key}
    governed_counts = [counts.get(key, {}) for key in sorted(governed_keys)]
    n_governed = sum(row.get("cost_eligible") or row.get("completed", 0) for row in governed_counts)
    unique_task_count = len({t.get("task_id") for t in tasks if t.get("task_id")})
    total_run_count = int(total_runs) if total_runs is not None else int(cum.get("total_runs") or 0)
    priced_run_count = (
        int(priced_runs)
        if priced_runs is not None
        else int((b_pac.get("cost_eligible") or b_pac.get("completed", 0)) + n_governed)
    )
    if valid_tasks and cum.get("has_measured_data"):
        b_costs = []
        i_costs = []
        task_savings_pcts = []
        n_paired_tasks = 0
        for t, gov_key in task_arms:
            # Only tasks whose arms share run_index pairs feed the paired cost
            # totals in cumulative_savings; count and CI must match that set.
            b_runs = {r.get("run_index"): r for r in t["arms"].get("baseline", {}).get("runs", [])}
            g_runs = {r.get("run_index"): r for r in t["arms"].get(gov_key, {}).get("runs", [])}
            paired = [
                (b_runs[i].get("cost_usd"), g_runs[i].get("cost_usd"))
                for i in sorted(set(b_runs) & set(g_runs))
            ]
            paired = [(b, g) for b, g in paired if b is not None and g is not None]
            if not paired:
                continue
            n_paired_tasks += 1
            t_b = sum(b for b, _ in paired)
            t_g = sum(g for _, g in paired)
            if t_b > 0:
                task_savings_pcts.append((t_b - t_g) / t_b * 100.0)
            # Weight the bootstrap by pair, matching cumulative_savings'
            # totals: every matched run counts equally, not every task.
            for b, g in paired:
                b_costs.append(b)
                i_costs.append(g)

        tot_b = cum.get("total_baseline_cost_usd")
        tot_i = cum.get("total_icm_cost_usd")
        if tot_b is not None and tot_i is not None and tot_b > 0:
            def _signed_cost(savings_pct: float) -> str:
                if savings_pct < 0:
                    return f"+{abs(savings_pct):.1f}% cost"
                if savings_pct > 0:
                    return f"-{abs(savings_pct):.1f}% savings"
                return "0.0% cost"

            pct = round((tot_b - tot_i) / tot_b * 100.0, 1)
            cost_delta_pct = round((tot_i - tot_b) / tot_b * 100.0, 1)
            signed_cost_label = _signed_cost(pct)
            macro_avg_pct = (
                round(sum(task_savings_pcts) / len(task_savings_pcts), 1)
                if task_savings_pcts
                else None
            )
            macro_note = (
                f"macro_average across {len(task_savings_pcts)} tasks: {_signed_cost(macro_avg_pct)}"
                if macro_avg_pct is not None
                else "macro_average unavailable"
            )
            ci = compute_bootstrap_ci(b_costs, i_costs)
            direct_count = int(billed_direct_runs) if billed_direct_runs is not None else priced_run_count
            acu_count = int(acu_derived_runs) if acu_derived_runs is not None else 0
            unpriced_count = max(0, total_run_count - priced_run_count)
            if direct_count > 0 and acu_count > 0:
                cost_basis = "Direct Billed + ACU Derived"
            elif acu_count > 0:
                cost_basis = "ACU Derived"
            elif direct_count > 0:
                cost_basis = "Direct Billed"
            else:
                cost_basis = "Unpriced"
            scope = {
                "unique_task_count": unique_task_count,
                "paired_priced_task_count": n_paired_tasks,
                "total_run_count": total_run_count,
                "priced_run_count": priced_run_count,
                "billed_direct_run_count": direct_count,
                "estimated_acu_derived_run_count": acu_count,
                "unpriced_run_count": unpriced_count,
                "cost_basis": cost_basis,
                "pooling_method": "pooled_sum",
                "macro_average_savings_pct": macro_avg_pct,
                "pooling_note": f"pooled_sum across matched priced pairs ({macro_note})",
                "signed_cost_label": signed_cost_label,
                "cost_delta_pct": cost_delta_pct,
                "savings_pct": pct,
            }
            stats.append({
                "id": "cost_reduction",
                "label": "Cost Reduction per Task",
                "value": pct,
                "unit": "%",
                "baseline": f"${tot_b:.4f}",
                "icm": f"${tot_i:.4f}",
                "n_baseline": b_pac.get("cost_eligible") or b_pac.get("completed", 0),
                "n_icm": n_governed,
                "n_tasks": n_paired_tasks,
                "source": "live CLI",
                "cost_basis": cost_basis,
                "ci95": ci,
                "cost_delta_pct": cost_delta_pct,
                "signed_cost_label": signed_cost_label,
                "pooling_method": "pooled_sum",
                "macro_average_savings_pct": macro_avg_pct,
                "priced_run_count": priced_run_count,
                "total_run_count": total_run_count,
            })

    # H2: Pass / Defect rate (only emit when defect_runs is genuinely tracked)
    if operational and operational.get("has_data") and operational.get("summary"):
        summ = operational["summary"]
        b_defects = summ.get("baseline", {}).get("defect_runs")
        b_runs = summ.get("baseline", {}).get("runs", 0)
        i_defects = summ.get("icm", {}).get("defect_runs")
        i_runs = summ.get("icm", {}).get("runs", 0)
        if b_defects is not None and i_defects is not None and b_runs > 0 and i_runs > 0:
            stats.append({
                "id": "defect_rate",
                "label": "Defect Rate (Quality)",
                "value": f"{round(i_defects / i_runs * 100, 1)}%",
                "unit": "defects",
                "baseline": f"{b_defects}/{b_runs} defects",
                "icm": f"{i_defects}/{i_runs} defects",
                "n_baseline": b_runs,
                "n_icm": i_runs,
                "n_tasks": len(operational.get("tasks", [])),
                "source": "operational benchmark",
            })

    # H3: Cache Hit Ratio
    if valid_tasks and cum.get("has_measured_data"):
        b_cache = cum.get("baseline_cache_hit_pct")
        i_cache = cum.get("icm_cache_hit_pct")
        if b_cache is not None and i_cache is not None:
            stats.append({
                "id": "cache_efficiency",
                "label": "Prompt Cache Hit Ratio",
                "value": round(i_cache, 1),
                "unit": "%",
                "baseline": f"{round(b_cache, 1)}%",
                "icm": f"{round(i_cache, 1)}%",
                "n_baseline": b_pac.get("cost_eligible") or b_pac.get("completed", 0),
                "n_icm": n_governed,
                "n_tasks": len(valid_tasks),
                "source": "live CLI",
            })

    # H4: Cross-model Tokens per Passing Patch
    if valid_tasks and cum.get("has_measured_data"):
        b_tpp = b_pac.get("tokens_per_passing_patch")
        i_passes = sum(row.get("passed_count", 0) for row in governed_counts)
        i_tpp = None
        if i_passes and all(row.get("tokens_per_passing_patch") is not None for row in governed_counts):
            i_tpp = sum(row["tokens_per_passing_patch"] * row["passed_count"] for row in governed_counts) / i_passes
        if (
            isinstance(b_tpp, (int, float))
            and isinstance(i_tpp, (int, float))
            and not isinstance(b_tpp, bool)
            and not isinstance(i_tpp, bool)
            and b_tpp > 0
        ):
            pct = round((b_tpp - i_tpp) / b_tpp * 100.0, 1)
            n_models = len({t.get("model") for t in tasks if t.get("model")})
            stats.append({
                "id": "tokens_per_pass",
                "label": "Tokens per Passing Patch",
                "value": pct,
                "unit": "%",
                "baseline": f"{int(round(b_tpp)):,}",
                "icm": f"{int(round(i_tpp)):,}",
                "n_baseline": b_pac.get("passed_count", 0),
                "n_icm": i_passes,
                "n_tasks": len(tasks),
                "source": f"{n_models} models" if n_models else "live CLI",
            })

    if not stats:
        return None

    # Construct descriptive sentence
    if stats:
        first = stats[0]
        if first["id"] == "cost_reduction" and scope is not None:
            sentence = (
                f"Across {scope['unique_task_count']} tasks ({scope['total_run_count']} runs; "
                f"{scope['priced_run_count']} priced runs across {scope['paired_priced_task_count']} paired tasks; "
                f"{scope['pooling_note']}), the ICM harness resulted in "
                f"{scope['signed_cost_label']} ({first['baseline']} vs {first['icm']})."
            )
        elif first["id"] == "defect_rate":
            sentence = f"Across operational runs, the ICM harness delivered {first['icm']} compared to {first['baseline']} in baseline arm."

    return {
        "sentence": sentence,
        "scope": scope,
        "stats": stats,
    }


def _resolve_evidence_path(evidence_ref: Optional[str]) -> Optional[Path]:
    """Resolve a DB evidence_ref path cleanly if and only if the file exists on disk."""
    if not evidence_ref:
        return None
    raw = str(evidence_ref).strip()
    if not raw:
        return None
    norm = raw.replace("\\", "/")
    candidates = [Path(raw), Path(norm)]
    if not Path(norm).is_absolute():
        candidates.append(WORKSPACE_ROOT / norm)
    for cand in candidates:
        try:
            if cand.is_file():
                return cand
        except OSError:
            continue
    return None


def _count_ndjson_tool_errors(ndjson_path: Path) -> Optional[int]:
    """Count ERROR tool steps in a DB-linked NDJSON file, deduped by step_index."""
    try:
        lines = ndjson_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None

    tool_states: Dict[int, str] = {}
    fallback_errs = 0
    parsed_lines = 0
    for line in lines:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        parsed_lines += 1
        if obj.get("event") == "step_update":
            su = obj.get("step_update") or {}
            if su.get("step_type") == "tool":
                idx = su.get("step_index")
                state = su.get("state", "")
                if idx is not None:
                    tool_states[int(idx)] = state
                elif state == "ERROR":
                    fallback_errs += 1

    if parsed_lines == 0:
        return None
    return fallback_errs + sum(1 for st in tool_states.values() if st == "ERROR")


def _compute_db_tool_errors(raw_runs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Compute tool errors strictly from DB-linked runs (column or linked NDJSON)."""
    b_errors = 0
    i_errors = 0
    telemetry_runs = 0
    for r in raw_runs:
        if r.get("is_simulation") or (r.get("source_kind") or "").lower() == "imported":
            continue
        bucket = _arm_bucket(r.get("arm"))
        if bucket is None:
            continue

        err_count: Optional[int] = None
        if r.get("tool_errors_count") is not None:
            err_count = int(r["tool_errors_count"])
        else:
            ev_path = _resolve_evidence_path(r.get("evidence_ref"))
            if ev_path is not None:
                err_count = _count_ndjson_tool_errors(ev_path)

        if err_count is None:
            continue

        telemetry_runs += 1
        if bucket == "baseline":
            b_errors += err_count
        else:
            i_errors += err_count

    if telemetry_runs == 0:
        return None

    if b_errors > 0:
        reduction: Optional[float] = round((b_errors - i_errors) / b_errors * 100.0, 1)
    elif i_errors == 0:
        reduction = 0.0
    else:
        reduction = None

    return {
        "baseline": b_errors,
        "icm": i_errors,
        "reduction_percent": reduction,
    }


def _build_multi_file_outlines(cum_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build multi-file outline summaries strictly from DB-backed EXP-009..011 tasks."""
    outline_meta = {
        "EXP-009": ("Event-driven job queue & DAG", 7),
        "EXP-010": ("Knowledge graph & BM25 search", 8),
        "EXP-011": ("Policy-enforced API gateway", 6),
    }
    items: List[Dict[str, Any]] = []
    for t in cum_tasks:
        tid = t.get("task_id")
        if tid not in outline_meta:
            continue
        arms = t.get("arms") or {}
        b_arm = arms.get("baseline")
        gov_key = _governed_key(arms, t.get("governed_arm"))
        g_arm = arms.get(gov_key) if gov_key else None
        if not b_arm or not g_arm:
            continue
        b_cost = b_arm.get("mean_cost_usd")
        g_cost = g_arm.get("mean_cost_usd")
        if b_cost is None or g_cost is None:
            continue
        title, n_files = outline_meta[tid]
        raw_pct = round((b_cost - g_cost) / b_cost * 100.0, 1) if b_cost > 0 else 0.0
        items.append({
            "task_id": tid,
            "title": title,
            "files": n_files,
            "baseline_turns": b_arm.get("mean_num_turns", 0),
            "icm_turns": g_arm.get("mean_num_turns", 0),
            "baseline_cost_usd": b_cost,
            "icm_cost_raw_usd": g_cost,
            "icm_cost_normalized_usd": g_cost,
            "raw_savings_percent": raw_pct,
            "normalized_savings_percent": raw_pct,
        })
    return items


def _load_pricing_display_config() -> Tuple[List[str], Set[str], Set[str]]:
    """Return ordered model ids, simulator-hidden ids, and conditional show-if-recorded ids."""
    path = ledger.DEFAULT_PRICING_PATH
    if not path.exists():
        return [], set(), set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return [], set(), set()
    models = data.get("models") or {}
    if not isinstance(models, dict):
        return [], set(), set()
    ordered = list(models.keys())
    hidden = {
        k for k, v in models.items()
        if isinstance(v, dict) and v.get("simulator_hidden")
    }
    show_if_rec = {
        k for k, v in models.items()
        if isinstance(v, dict) and v.get("show_if_recorded")
    }
    return ordered, hidden, show_if_rec


def build_data_payload(
    db_path: Optional[Path] = None,
    capture_policy: str = "approved",
) -> Dict[str, Any]:
    """Extract and structure data for the local dashboard using shared ledger helpers."""
    conn = ledger.get_connection(db_path)
    try:
        # Fetch pricing
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pricing")
        pricing_rows = [dict(r) for r in cursor.fetchall()]

        # Fetch cumulative metrics via shared helper
        cum = ledger.cumulative_savings(conn=conn, db_path=db_path, capture_policy=capture_policy)

        # Fetch all runs without task-prefix bias
        cursor.execute("SELECT * FROM runs ORDER BY id ASC")
        raw_runs = [dict(r) for r in cursor.fetchall()]

        ordered_models, hidden_models, show_if_recorded = _load_pricing_display_config()
        order_index = {m: idx for idx, m in enumerate(ordered_models)}
        recorded_models = {r["model"] for r in raw_runs if r.get("model")}
        simulator_pricing_rows = [
            p for p in pricing_rows
            if p.get("model") not in hidden_models
            or (p.get("model") in show_if_recorded and p.get("model") in recorded_models)
        ]
        simulator_pricing_rows.sort(
            key=lambda p: (
                0 if p.get("model") in order_index else 1,
                order_index.get(p.get("model"), 0),
                p.get("model", ""),
            )
        )

        # Process each run through shared eligibility and accounting
        task_pairs: Dict[Tuple[str, str], Dict[int, Dict[str, Any]]] = {}
        processed_runs: List[Dict[str, Any]] = []

        for r in raw_runs:
            is_row_partial = (r.get("cost_status") == "incomplete") or (
                isinstance(r.get("exclusion_reasons"), str) and "partial_telemetry" in r["exclusion_reasons"]
            )
            cost_info = ledger.calculate_cost_detailed(
                r["input_tokens"],
                r["cache_read_tokens"],
                r["output_tokens"],
                r["model"],
                thinking_tokens=r.get("thinking_tokens"),
                conn=conn,
                db_path=db_path,
                is_simulation=bool(r.get("is_simulation", 0)),
                is_partial=is_row_partial,
                acus_consumed=r.get("acus_consumed"),
                acu_usd_rate=r.get("acu_usd_rate"),
            )
            if r.get("cost_status") in ("unavailable", "incomplete"):
                pass
            else:
                r["cost_status"] = cost_info["cost_status"]

            if r.get("cost_usd") is None:
                r["cost_usd"] = cost_info["cost_usd"]

            r["cost_source"] = r.get("cost_source") or cost_info.get("cost_source") or ledger.classify_cost_source(r)
            if r["cost_source"] == ledger.COST_SOURCE_ESTIMATED_ACU_DERIVED:
                if r.get("estimated_cost_usd") is None and r.get("cost_usd") is not None:
                    r["estimated_cost_usd"] = r["cost_usd"]
                if r.get("acu_usd_rate") is None and cost_info.get("acu_usd_rate") is not None:
                    r["acu_usd_rate"] = cost_info["acu_usd_rate"]

            r["source_kind"] = r.get("source_kind") or "unknown"
            r["evidence_status"] = r.get("evidence_status") or "unverified"

            elig = ledger.evaluate_run_eligibility(r, capture_policy=capture_policy)
            r["is_eligible"] = elig["is_eligible"]
            r["is_comparison_eligible"] = elig["is_comparison_eligible"]
            r["reporting_category"] = elig["category"]
            r["exclusion_reasons"] = elig["exclusion_reasons"]

            public_r = ledger.to_public_run(r)
            processed_runs.append(public_r)

            # Only pair eligible measured runs for timeline (requires comparison eligibility)
            if r.get("is_comparison_eligible") and not r.get("is_simulation") and r["cost_usd"] is not None:
                tid = r["task_id"]
                mdl = r["model"]
                ridx = r["run_index"]
                arm = r["arm"].lower()
                task_pairs.setdefault((tid, mdl), {}).setdefault(ridx, {})[arm] = r

        models_per_tid: Dict[str, set] = {}
        for tid, mdl in task_pairs:
            models_per_tid.setdefault(tid, set()).add(mdl)

        # Build timeline for cumulative savings curve using only qualifying measured runs
        timeline: List[Dict[str, Any]] = []
        cumulative_saved = 0.0
        step = 1

        for tid, mdl in sorted(task_pairs):
            multi_mdl = len(models_per_tid.get(tid, set())) > 1
            for ridx in sorted(task_pairs[(tid, mdl)]):
                arms = task_pairs[(tid, mdl)][ridx]
                gov_arm = _governed_key(arms)
                if not gov_arm:
                    for k in arms:
                        if k != "baseline":
                            gov_arm = k
                            break
                if "baseline" in arms and gov_arm and gov_arm in arms:
                    b_cost = arms["baseline"]["cost_usd"]
                    g_cost = arms[gov_arm]["cost_usd"]
                    delta = b_cost - g_cost
                    cumulative_saved += delta
                    timeline.append({
                        "step": step,
                        "label": f"{tid} ({mdl}) Run {ridx}" if multi_mdl else f"{tid} Run {ridx}",
                        "task_id": tid,
                        "model": mdl,
                        "run_index": ridx,
                        "governed_arm": gov_arm,
                        "timestamp": arms[gov_arm]["timestamp"],
                        "baseline_cost_usd": b_cost,
                        "icm_cost_usd": g_cost,
                        "delta_saved_usd": delta,
                        "cumulative_savings_usd": cumulative_saved,
                    })
                    step += 1

        # Multi-model cascade
        cascade: List[Dict[str, Any]] = []
        for p in simulator_pricing_rows:
            m = p["model"]
            m_cum = ledger.cumulative_savings(conn=conn, db_path=db_path, model_override=m, capture_policy=capture_policy)
            cascade.append({
                "model": m,
                "is_simulation": True,
                "counter_semantics_qualification": m_cum.get("counter_semantics_qualification"),
                "input_usd_per_mtok": p["input_usd_per_mtok"],
                "cache_read_usd_per_mtok": p["cache_read_usd_per_mtok"],
                "output_usd_per_mtok": p["output_usd_per_mtok"],
                "pricing_mode": p.get("pricing_mode"),
                "provider_note": p.get("provider_note"),
                "total_baseline_cost_usd": m_cum["total_baseline_cost_usd"],
                "total_icm_cost_usd": m_cum["total_icm_cost_usd"],
                "cumulative_savings_usd": m_cum["cumulative_savings_usd"],
                "cumulative_savings_percent": m_cum["cumulative_savings_percent"],
                "cost_per_mtok_baseline": m_cum["cost_per_mtok_baseline"],
                "cost_per_mtok_icm": m_cum["cost_per_mtok_icm"],
                "savings_usd_per_mtok": m_cum["savings_usd_per_mtok"],
                "projected_savings_10m": m_cum["projected_savings_10m"],
                "projected_savings_100m": m_cum["projected_savings_100m"],
                "projected_savings_1b": (m_cum["savings_usd_per_mtok"] * 1000.0) if m_cum["savings_usd_per_mtok"] is not None else None,
                "source_url": p.get("source_url", ""),
            })

        has_data = bool(cum.get("has_measured_data", False))
        is_demo_report = bool(cum.get("is_demo_report", False))
        if not is_demo_report and not has_data and len(processed_runs) > 0:
            is_demo_report = True

        # Generate shared campaign report if possible (EXP-01)
        campaign_rep = None
        try:
            campaign_rep = campaign.generate_campaign_report(
                conn=conn,
                db_path=db_path,
                strict_manifest=False,
                capture_policy=capture_policy,
            )
            if campaign_rep and campaign_rep.get("is_demo_report"):
                is_demo_report = True
        except Exception:
            campaign_rep = None

        ops_block = build_operational_block()
        priced_runs_total = sum(1 for r in processed_runs if r.get("cost_usd") is not None)
        billed_direct_runs_total = sum(
            1 for r in processed_runs if r.get("cost_source") == ledger.COST_SOURCE_BILLED_DIRECT
        )
        acu_derived_runs_total = sum(
            1 for r in processed_runs if r.get("cost_source") == ledger.COST_SOURCE_ESTIMATED_ACU_DERIVED
        )
        headline_block = build_headline_block(
            cum.get("tasks", []),
            cum,
            operational=ops_block,
            total_runs=len(processed_runs),
            priced_runs=priced_runs_total,
            billed_direct_runs=billed_direct_runs_total,
            acu_derived_runs=acu_derived_runs_total,
        )
        declared_benchmarks = build_declared_benchmarks(cum.get("tasks", []), processed_runs)

        quality_block = None
        try:
            from evaluate_all_quality import evaluate_all
            try:
                q_rep = evaluate_all(db_path=db_path) if db_path is not None else evaluate_all()
            except TypeError:
                q_rep = evaluate_all()
            outlines = _build_multi_file_outlines(cum.get("tasks", []))
            tool_errors = _compute_db_tool_errors(raw_runs)
            quality_block = {
                "has_data": bool(q_rep.get("tasks")),
                "tasks": q_rep["tasks"],
                "quality_ci": q_rep["quality_ci"],
                "multi_file_outlines": outlines,
                "tool_errors": tool_errors,
            }
        except Exception:
            quality_block = None

        payload = {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "build_identity": get_build_identity(),
            "has_data": has_data,
            "is_demo_report": is_demo_report,
            "is_simulation": False,
            "headline": headline_block,
            "declared_benchmarks": declared_benchmarks,
            "cumulative": cum,
            "tasks": cum.get("tasks", []),
            "runs": processed_runs,
            "timeline": timeline,
            "pricing": simulator_pricing_rows,
            "acu_pricing": {
                "devin_acu_usd_rate": ledger.get_devin_acu_usd_rate(),
                "default_rate": ledger.DEFAULT_DEVIN_ACU_USD_RATE,
                "currency": "USD",
            },
            "cascade": cascade,
            "operational": ops_block,
            "quality_rubric": quality_block,
            "campaign": campaign_rep,
        }
        return sanitize_export_payload(payload)
    finally:
        conn.close()


def export_data(
    output_file: Path = OUTPUT_PATH,
    db_path: Optional[Path] = None,
    capture_policy: str = "approved",
) -> Path:
    """Export the payload to static data.json."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    data = build_data_payload(db_path=db_path, capture_policy=capture_policy)
    raw_json = json.dumps(data, indent=2)
    sanitized_json = sanitize_export_text(raw_json) or raw_json
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(sanitized_json)
    print(f"✓ Dashboard data exported to: {output_file} ({len(data['runs'])} runs, {len(data['tasks'])} tasks)")
    return output_file


def main():
    # Allow env-var overrides for CI / test isolation
    env_out = os.environ.get("AI_LAB_OUTPUT_PATH")
    env_db = os.environ.get("AI_LAB_DB_PATH")

    out_path = Path(env_out) if env_out else (Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_PATH)
    db_path = Path(env_db) if env_db else (WORKSPACE_ROOT / "data" / "usage.db")

    # In CI, data/usage.db may not exist (it's gitignored).
    # The committed data.json snapshot is used directly; skip export gracefully.
    if not db_path.exists():
        if out_path.exists() and not env_out:
            # Real output path exists and no override: preserve committed snapshot
            print(f"✓ No database found — using committed snapshot: {out_path}")
        else:
            # Emit a minimal valid placeholder so the dashboard renders without errors
            out_path.parent.mkdir(parents=True, exist_ok=True)
            placeholder = {
                "schema_version": "1.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "build_identity": get_build_identity(),
                "has_data": False,
                "is_demo_report": True,
                "is_simulation": False,
                "cumulative": {
                    "tasks_evaluated": 0,
                    "total_runs": 0,
                    "has_measured_data": False,
                    "is_demo_report": True,
                    "tasks": [],
                },
                "tasks": [],
                "runs": [],
                "timeline": [],
                "pricing": [],
                "cascade": [],
                "operational": {"has_data": False, "runs": [], "tasks": []},
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(placeholder, f, indent=2)
            print(f"✓ No database — wrote empty placeholder: {out_path}")
        return

    export_data(out_path, db_path=db_path)



if __name__ == "__main__":
    main()
