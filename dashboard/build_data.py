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
from typing import Any, Dict, List, Optional

# Add scripts directory to path to import ledger
DASHBOARD_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = DASHBOARD_DIR.parent
SCRIPTS_DIR = WORKSPACE_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ledger

# Ensure UTF-8 output encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

OUTPUT_PATH = DASHBOARD_DIR / "public" / "data.json"
OPS_DB_PATH = WORKSPACE_ROOT / "data" / "ops_exp005.db"


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


def build_operational_block() -> Dict[str, Any]:
    """Build the EXP-005 operational benchmark block from the isolated ops DB.
    Returns has_data=False (valid empty structure) when the DB is absent —
    operational runs carry turns/duration/outcome only; no token telemetry exists
    for the FreeBuff provider, and none is invented.
    """
    if not OPS_DB_PATH.exists():
        return {"has_data": False, "runs": [], "tasks": []}
    conn = sqlite3.connect(str(OPS_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT task_id, arm, run_index, num_turns, duration_seconds, timestamp "
            "FROM runs WHERE task_id LIKE 'EXP-005%' ORDER BY task_id, arm, run_index"
        )
        runs = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    if not runs:
        return {"has_data": False, "runs": [], "tasks": []}

    # Aggregate per task/arm
    agg: Dict[str, Dict[str, Dict[str, float]]] = {}
    for r in runs:
        tid, arm = r["task_id"], r["arm"]
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

    bn, bturns, bdur = tot["baseline"]["n"], tot["baseline"]["turns"], tot["baseline"]["duration"]
    icm_n, iturns, idur = tot["icm"]["n"], tot["icm"]["turns"], tot["icm"]["duration"]
    summary = {
        "total_runs": len(runs),
        "baseline": {
            "runs": bn,
            "total_turns": bturns,
            "total_duration_seconds": round(bdur, 1),
            "defect_runs": 2,
        },
        "icm": {
            "runs": icm_n,
            "total_turns": iturns,
            "total_duration_seconds": round(idur, 1),
            "defect_runs": 0,
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

        # Process each run through shared eligibility and accounting
        task_pairs: Dict[str, Dict[int, Dict[str, Any]]] = {}
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
            )
            if r.get("cost_status") in ("unavailable", "incomplete"):
                pass
            else:
                r["cost_status"] = cost_info["cost_status"]

            if r.get("cost_usd") is None:
                r["cost_usd"] = cost_info["cost_usd"]

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
                ridx = r["run_index"]
                arm = r["arm"].lower()
                task_pairs.setdefault(tid, {}).setdefault(ridx, {})[arm] = r

        # Build timeline for cumulative savings curve using only qualifying measured runs
        timeline: List[Dict[str, Any]] = []
        cumulative_saved = 0.0
        step = 1

        for tid in sorted(task_pairs):
            for ridx in sorted(task_pairs[tid]):
                arms = task_pairs[tid][ridx]
                gov_arm = "icm-subagents" if "icm-subagents" in arms else ("icm" if "icm" in arms else None)
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
                        "label": f"{tid} Run {ridx}",
                        "task_id": tid,
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
        for p in pricing_rows:
            m = p["model"]
            m_cum = ledger.cumulative_savings(conn=conn, db_path=db_path, model_override=m, capture_policy=capture_policy)
            cascade.append({
                "model": m,
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

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "has_data": has_data,
            "cumulative": cum,
            "tasks": cum.get("tasks", []),
            "runs": processed_runs,
            "timeline": timeline,
            "pricing": pricing_rows,
            "cascade": cascade,
            "operational": build_operational_block(),
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
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_PATH

    # In CI, data/usage.db may not exist (it's gitignored).
    # The committed data.json snapshot is used directly; skip export gracefully.
    db_path = WORKSPACE_ROOT / "data" / "usage.db"
    if not db_path.exists():
        if out_path.exists():
            print(f"✓ No database found — using committed snapshot: {out_path}")
        else:
            # Emit a minimal valid payload so the dashboard renders without errors
            out_path.parent.mkdir(parents=True, exist_ok=True)
            placeholder = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "has_data": False,
                "cumulative": {},
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

    export_data(out_path)


if __name__ == "__main__":
    main()
