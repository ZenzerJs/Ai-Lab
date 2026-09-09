#!/usr/bin/env python3
"""
dashboard/build_data.py - Static Data Exporter for Antigravity Savings Dashboard

Extracts normalized runs, per-task metrics, error bands, and cumulative savings
from data/usage.db and writes dashboard/public/data.json.
Gracefully handles empty databases by generating valid schema structures.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

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


def build_data_payload() -> Dict[str, Any]:
    """Extract and structure data for the local dashboard."""
    conn = ledger.get_connection()
    try:
        # Fetch pricing
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pricing")
        pricing_rows = [dict(r) for r in cursor.fetchall()]

        # Fetch all tasks and cumulative metrics
        cum = ledger.cumulative_savings(conn=conn)

        # Fetch all raw runs
        cursor.execute("SELECT * FROM runs ORDER BY id ASC")
        raw_runs = [dict(r) for r in cursor.fetchall()]

        for r in raw_runs:
            r["cost_usd"] = ledger.calculate_cost(
                r["input_tokens"],
                r["cache_read_tokens"],
                r["output_tokens"],
                r["model"],
                conn=conn,
            )

        # Build timeline for cumulative savings curve
        # Pair up matching baseline and icm runs per task
        timeline: List[Dict[str, Any]] = []
        cumulative_saved = 0.0

        # Group runs by task and run_index
        task_pairs: Dict[str, Dict[int, Dict[str, Any]]] = {}
        for r in raw_runs:
            tid = r["task_id"]
            ridx = r["run_index"]
            arm = r["arm"].lower()
            if tid not in task_pairs:
                task_pairs[tid] = {}
            if ridx not in task_pairs[tid]:
                task_pairs[tid][ridx] = {}
            task_pairs[tid][ridx][arm] = r

        step = 1
        for tid, indexes in sorted(task_pairs.items()):
            for ridx, arms in sorted(indexes.items()):
                if "baseline" in arms and "icm" in arms:
                    b_cost = arms["baseline"]["cost_usd"]
                    i_cost = arms["icm"]["cost_usd"]
                    delta = b_cost - i_cost
                    cumulative_saved += delta
                    timeline.append({
                        "step": step,
                        "label": f"{tid} Run {ridx}",
                        "task_id": tid,
                        "run_index": ridx,
                        "timestamp": arms["icm"]["timestamp"],
                        "baseline_cost_usd": b_cost,
                        "icm_cost_usd": i_cost,
                        "delta_saved_usd": delta,
                        "cumulative_savings_usd": cumulative_saved,
                    })
                    step += 1

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "has_data": len(raw_runs) > 0,
            "cumulative": cum,
            "tasks": cum.get("tasks", []),
            "runs": raw_runs,
            "timeline": timeline,
            "pricing": pricing_rows,
        }
        return payload
    finally:
        conn.close()


def export_data(output_file: Path = OUTPUT_PATH) -> Path:
    """Export the payload to static data.json."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    data = build_data_payload()
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"✓ Dashboard data exported to: {output_file} ({len(data['runs'])} runs, {len(data['tasks'])} tasks)")
    return output_file


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_PATH
    export_data(out_path)


if __name__ == "__main__":
    main()
