#!/usr/bin/env python3
"""
scripts/ledger.py - SQLite Storage Engine for A/B Token Usage & Cost Analytics

Manages tables for runs, tasks, and cache-aware model pricing.
Enforces auditable rate seeding from config/PRICING.json.
Provides analytical functions for per-task comparison and cumulative savings.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure UTF-8 output encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = DEFAULT_ROOT / "data" / "usage.db"
DEFAULT_PRICING_PATH = DEFAULT_ROOT / "config" / "PRICING.json"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Connect to SQLite database and ensure schema exists."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create schema tables if they do not already exist."""
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                arm TEXT NOT NULL,
                model TEXT NOT NULL,
                run_index INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                thinking_tokens INTEGER NOT NULL,
                cache_read_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                num_turns INTEGER NOT NULL,
                duration_seconds REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                prompt_path TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pricing (
                model TEXT PRIMARY KEY,
                input_usd_per_mtok REAL NOT NULL,
                cache_read_usd_per_mtok REAL NOT NULL,
                output_usd_per_mtok REAL NOT NULL,
                source_url TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            );
        """)


def seed_pricing(
    pricing_path: Optional[Path] = None,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Seed pricing table from config/PRICING.json. Never hardcodes rates in code."""
    path = Path(pricing_path) if pricing_path else DEFAULT_PRICING_PATH
    if not path.exists():
        raise FileNotFoundError(f"Pricing configuration file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    models = data.get("models", {})
    if not models:
        raise ValueError(f"No models declared in pricing config: {path}")

    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    count = 0
    with conn:
        for model_id, rates in models.items():
            conn.execute(
                """
                INSERT INTO pricing (
                    model, input_usd_per_mtok, cache_read_usd_per_mtok,
                    output_usd_per_mtok, source_url, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(model) DO UPDATE SET
                    input_usd_per_mtok = excluded.input_usd_per_mtok,
                    cache_read_usd_per_mtok = excluded.cache_read_usd_per_mtok,
                    output_usd_per_mtok = excluded.output_usd_per_mtok,
                    source_url = excluded.source_url,
                    fetched_at = excluded.fetched_at
                """,
                (
                    model_id,
                    float(rates["input_usd_per_mtok"]),
                    float(rates["cache_read_usd_per_mtok"]),
                    float(rates["output_usd_per_mtok"]),
                    str(rates["source_url"]),
                    str(rates.get("fetched_at", datetime.now(timezone.utc).isoformat())),
                ),
            )
            count += 1

    if should_close:
        conn.close()

    return count


def get_pricing(model: str, conn: Optional[sqlite3.Connection] = None, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Retrieve pricing rates for a given model from DB, auto-seeding if needed."""
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pricing WHERE model = ?", (model,))
    row = cursor.fetchone()

    if not row:
        # Attempt auto-seed from config/PRICING.json
        seed_pricing(conn=conn)
        cursor.execute("SELECT * FROM pricing WHERE model = ?", (model,))
        row = cursor.fetchone()

    if not row:
        if should_close:
            conn.close()
        raise ValueError(
            f"Pricing not found for model '{model}'. "
            f"Add rates to config/PRICING.json and re-run seed."
        )

    result = dict(row)
    if should_close:
        conn.close()
    return result


def calculate_cost(
    input_tokens: int,
    cache_read_tokens: int,
    output_tokens: int,
    model: str,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
) -> float:
    """
    Compute cache-aware USD cost for a token count profile.
    Formula: ((input_tokens * input_rate) + (cache_read_tokens * cache_read_rate) + (output_tokens * output_rate)) / 1_000_000
    Rates are in USD per million tokens.
    """
    rates = get_pricing(model, conn=conn, db_path=db_path)
    cost = (
        (input_tokens * rates["input_usd_per_mtok"])
        + (cache_read_tokens * rates["cache_read_usd_per_mtok"])
        + (output_tokens * rates["output_usd_per_mtok"])
    ) / 1_000_000.0
    return cost


def record_task(
    task_id: str,
    prompt_path: Optional[str] = None,
    notes: Optional[str] = None,
    created_at: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Record or update a task entry."""
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    timestamp = created_at or datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute(
            """
            INSERT INTO tasks (id, prompt_path, notes, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                prompt_path = COALESCE(excluded.prompt_path, tasks.prompt_path),
                notes = COALESCE(excluded.notes, tasks.notes)
            """,
            (task_id, prompt_path, notes, timestamp),
        )

    if should_close:
        conn.close()


def clear_task_runs(task_id: str, conn: Optional[sqlite3.Connection] = None, db_path: Optional[Path] = None) -> int:
    """Clear previous experimental runs for a task to allow clean idempotent re-runs."""
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    with conn:
        cursor = conn.execute("DELETE FROM runs WHERE task_id = ?", (task_id,))
        count = cursor.rowcount

    if should_close:
        conn.close()

    return count


def record_run(
    task_id: str,
    arm: str,
    model: str,
    run_index: int,
    timestamp: str,
    input_tokens: int,
    output_tokens: int,
    thinking_tokens: int,
    cache_read_tokens: int,
    total_tokens: int,
    num_turns: int,
    duration_seconds: float,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Record an experimental run into the SQLite ledger."""
    # Ensure pricing is seeded
    get_pricing(model, conn=conn, db_path=db_path)

    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    record_task(task_id, conn=conn)

    with conn:
        cursor = conn.execute(
            """
            INSERT INTO runs (
                task_id, arm, model, run_index, timestamp,
                input_tokens, output_tokens, thinking_tokens, cache_read_tokens,
                total_tokens, num_turns, duration_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                arm,
                model,
                run_index,
                timestamp,
                int(input_tokens),
                int(output_tokens),
                int(thinking_tokens),
                int(cache_read_tokens),
                int(total_tokens),
                int(num_turns),
                float(duration_seconds),
            ),
        )
        run_id = cursor.lastrowid

    if should_close:
        conn.close()

    return run_id


def task_summary(task_id: str, conn: Optional[sqlite3.Connection] = None, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Calculate per-arm means, error bands, and savings metrics for a task."""
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE task_id = ? ORDER BY arm, run_index", (task_id,))
    rows = [dict(r) for r in cursor.fetchall()]

    if not rows:
        if should_close:
            conn.close()
        return {"task_id": task_id, "runs_count": 0, "arms": {}}

    arms_data: Dict[str, List[Dict[str, Any]]] = {"baseline": [], "icm": []}
    for r in rows:
        arm = r["arm"].lower()
        if arm not in arms_data:
            arms_data[arm] = []
        cost = calculate_cost(
            r["input_tokens"],
            r["cache_read_tokens"],
            r["output_tokens"],
            r["model"],
            conn=conn,
        )
        r["cost_usd"] = cost
        arms_data[arm].append(r)

    summary: Dict[str, Any] = {"task_id": task_id, "total_runs": len(rows), "arms": {}}

    for arm_name, runs_list in arms_data.items():
        n = len(runs_list)
        if n == 0:
            continue
        costs = [r["cost_usd"] for r in runs_list]
        inputs = [r["input_tokens"] for r in runs_list]
        caches = [r["cache_read_tokens"] for r in runs_list]
        outputs = [r["output_tokens"] for r in runs_list]
        totals = [r["total_tokens"] for r in runs_list]
        turns = [r["num_turns"] for r in runs_list]
        durations = [r["duration_seconds"] for r in runs_list]

        mean_input = sum(inputs) / n
        mean_cache = sum(caches) / n
        cache_hit_ratio = (mean_cache / mean_input) if mean_input > 0 else 0.0

        summary["arms"][arm_name] = {
            "n": n,
            "model": runs_list[0]["model"],
            "mean_cost_usd": sum(costs) / n,
            "min_cost_usd": min(costs),
            "max_cost_usd": max(costs),
            "mean_input_tokens": mean_input,
            "mean_cache_read_tokens": mean_cache,
            "mean_output_tokens": sum(outputs) / n,
            "mean_total_tokens": sum(totals) / n,
            "mean_num_turns": sum(turns) / n,
            "mean_duration_seconds": sum(durations) / n,
            "cache_hit_ratio": cache_hit_ratio,
            "runs": runs_list,
        }

    # Compare baseline vs icm if both exist
    if "baseline" in summary["arms"] and "icm" in summary["arms"]:
        b = summary["arms"]["baseline"]
        i = summary["arms"]["icm"]
        cost_diff = b["mean_cost_usd"] - i["mean_cost_usd"]
        cost_pct = (cost_diff / b["mean_cost_usd"] * 100.0) if b["mean_cost_usd"] > 0 else 0.0
        tokens_diff = b["mean_total_tokens"] - i["mean_total_tokens"]
        turns_diff = b["mean_num_turns"] - i["mean_num_turns"]
        duration_diff = b["mean_duration_seconds"] - i["mean_duration_seconds"]

        # Calculate 1M token normalized metrics
        base_tokens = b["mean_total_tokens"]
        icm_tokens = i["mean_total_tokens"]
        cost_per_mtok_base = (b["mean_cost_usd"] / base_tokens * 1_000_000) if base_tokens > 0 else 0.0
        cost_per_mtok_icm = (i["mean_cost_usd"] / icm_tokens * 1_000_000) if icm_tokens > 0 else 0.0
        savings_per_mtok = cost_per_mtok_base - cost_per_mtok_icm

        summary["savings"] = {
            "mean_savings_usd": cost_diff,
            "mean_savings_percent": cost_pct,
            "mean_total_tokens_saved": tokens_diff,
            "mean_turns_saved": turns_diff,
            "mean_duration_seconds_saved": duration_diff,
            "cache_hit_ratio_baseline": b["cache_hit_ratio"],
            "cache_hit_ratio_icm": i["cache_hit_ratio"],
            "cost_per_mtok_baseline": cost_per_mtok_base,
            "cost_per_mtok_icm": cost_per_mtok_icm,
            "savings_usd_per_mtok": savings_per_mtok,
            "projected_savings_10m": savings_per_mtok * 10,
            "projected_savings_100m": savings_per_mtok * 100,
        }

    if should_close:
        conn.close()

    return summary


def cumulative_savings(conn: Optional[sqlite3.Connection] = None, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Compute total measured savings across all tasks with baseline and icm arms."""
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT task_id FROM runs ORDER BY task_id")
    task_ids = [row["task_id"] for row in cursor.fetchall()]

    total_baseline_cost = 0.0
    total_icm_cost = 0.0
    total_baseline_tokens = 0
    total_icm_tokens = 0
    total_runs = 0
    task_summaries = []

    for tid in task_ids:
        s = task_summary(tid, conn=conn)
        task_summaries.append(s)
        if "baseline" in s.get("arms", {}) and "icm" in s.get("arms", {}):
            b_n = s["arms"]["baseline"]["n"]
            i_n = s["arms"]["icm"]["n"]
            total_runs += b_n + i_n

            b_runs = {r["run_index"]: r for r in s["arms"]["baseline"]["runs"]}
            i_runs = {r["run_index"]: r for r in s["arms"]["icm"]["runs"]}
            common_indexes = sorted(set(b_runs.keys()) & set(i_runs.keys()))
            for ridx in common_indexes:
                total_baseline_cost += b_runs[ridx]["cost_usd"]
                total_icm_cost += i_runs[ridx]["cost_usd"]
                total_baseline_tokens += b_runs[ridx]["total_tokens"]
                total_icm_tokens += i_runs[ridx]["total_tokens"]

    measured_savings_usd = total_baseline_cost - total_icm_cost
    savings_pct = (
        (measured_savings_usd / total_baseline_cost * 100.0)
        if total_baseline_cost > 0
        else 0.0
    )

    cost_per_mtok_base = (total_baseline_cost / total_baseline_tokens * 1_000_000) if total_baseline_tokens > 0 else 0.0
    cost_per_mtok_icm = (total_icm_cost / total_icm_tokens * 1_000_000) if total_icm_tokens > 0 else 0.0
    savings_usd_per_mtok = cost_per_mtok_base - cost_per_mtok_icm

    result = {
        "tasks_evaluated": len(task_summaries),
        "total_runs": total_runs,
        "total_baseline_cost_usd": total_baseline_cost,
        "total_icm_cost_usd": total_icm_cost,
        "total_baseline_tokens": total_baseline_tokens,
        "total_icm_tokens": total_icm_tokens,
        "cumulative_savings_usd": measured_savings_usd,
        "cumulative_savings_percent": savings_pct,
        "cost_per_mtok_baseline": cost_per_mtok_base,
        "cost_per_mtok_icm": cost_per_mtok_icm,
        "savings_usd_per_mtok": savings_usd_per_mtok,
        "projected_savings_10m": savings_usd_per_mtok * 10,
        "projected_savings_100m": savings_usd_per_mtok * 100,
        "tasks": task_summaries,
    }

    if should_close:
        conn.close()

    return result


def print_summary(task_id: Optional[str] = None) -> None:
    """Pretty-print summary to terminal."""
    conn = get_connection()
    try:
        if task_id:
            s = task_summary(task_id, conn=conn)
            if s.get("total_runs", 0) == 0:
                print(f"No runs found for task: {task_id}")
                return

            print("=" * 72)
            print(f"  USAGE LEDGER SUMMARY: Task {task_id}")
            print("=" * 72)
            for arm_name in ["baseline", "icm"]:
                if arm_name in s.get("arms", {}):
                    a = s["arms"][arm_name]
                    print(f"\n[{arm_name.upper()} ARM] (n={a['n']}, Model: {a['model']})")
                    print(f"  Mean Cost:           ${a['mean_cost_usd']:.5f} (min: ${a['min_cost_usd']:.5f}, max: ${a['max_cost_usd']:.5f})")
                    print(f"  Mean Input Tokens:   {a['mean_input_tokens']:,.0f}")
                    print(f"  Mean Cache Read:     {a['mean_cache_read_tokens']:,.0f}")
                    print(f"  Mean Output Tokens:  {a['mean_output_tokens']:,.0f}")
                    print(f"  Mean Total Tokens:   {a['mean_total_tokens']:,.0f}")
                    print(f"  Cache Hit Ratio:     {a['cache_hit_ratio'] * 100:.2f}%")
                    print(f"  Mean Turns:          {a['mean_num_turns']:.1f}")
                    print(f"  Mean Duration:       {a['mean_duration_seconds']:.2f}s")

            if "savings" in s:
                sv = s["savings"]
                print("-" * 72)
                print("[MEASURED SAVINGS: BASELINE vs. ICM]")
                print(f"  Cost Reduction:      ${sv['mean_savings_usd']:.5f} ({sv['mean_savings_percent']:.2f}%)")
                print(f"  Total Tokens Saved:  {sv['mean_total_tokens_saved']:,.0f}")
                print(f"  Turns Saved:         {sv['mean_turns_saved']:.1f}")
                print(f"  Duration Saved:      {sv['mean_duration_seconds_saved']:.2f}s")
                print(f"  Cache Hit Ratio:     Baseline {sv['cache_hit_ratio_baseline']*100:.1f}% -> ICM {sv['cache_hit_ratio_icm']*100:.1f}%")
                print("-" * 72)
                print("[1M TOKEN SCALE MULTIPLIER & PROJECTIONS]")
                print(f"  Baseline / 1M Tokens:   ${sv['cost_per_mtok_baseline']:.4f}")
                print(f"  ICM / 1M Tokens:        ${sv['cost_per_mtok_icm']:.4f}")
                print(f"  Net Savings / 1M Tokens: +${sv['savings_usd_per_mtok']:.4f} ({sv['mean_savings_percent']:.1f}%)")
                print(f"  Projected Savings @ 10M:  +${sv['projected_savings_10m']:.3f}")
                print(f"  Projected Savings @ 100M: +${sv['projected_savings_100m']:.2f}")
            print("=" * 72)

        else:
            cum = cumulative_savings(conn=conn)
            print("=" * 72)
            print("  USAGE LEDGER CUMULATIVE SUMMARY (ALL TASKS)")
            print("=" * 72)
            print(f"Tasks Evaluated:       {cum['tasks_evaluated']}")
            print(f"Total Runs Recorded:   {cum['total_runs']}")
            print(f"Total Baseline Cost:   ${cum['total_baseline_cost_usd']:.5f}")
            print(f"Total ICM Cost:        ${cum['total_icm_cost_usd']:.5f}")
            print(f"Cumulative Savings:    ${cum['cumulative_savings_usd']:.5f} ({cum['cumulative_savings_percent']:.2f}%)")
            print("-" * 72)
            print("[1M TOKEN SCALE MULTIPLIER & VOLUME PROJECTIONS]")
            print(f"  Baseline / 1M Tokens:   ${cum['cost_per_mtok_baseline']:.4f}")
            print(f"  ICM / 1M Tokens:        ${cum['cost_per_mtok_icm']:.4f}")
            print(f"  Net Savings / 1M Tokens: +${cum['savings_usd_per_mtok']:.4f} ({cum['cumulative_savings_percent']:.1f}%)")
            print(f"  Projected Savings @ 10M:  +${cum['projected_savings_10m']:.3f}")
            print(f"  Projected Savings @ 100M: +${cum['projected_savings_100m']:.2f}")
            print("=" * 72)
            for t in cum["tasks"]:
                tid = t["task_id"]
                if "savings" in t:
                    sv = t["savings"]
                    print(f"  • {tid:10s} | Saved: ${sv['mean_savings_usd']:.5f} ({sv['mean_savings_percent']:4.1f}%) | 1M Rate: Base ${sv['cost_per_mtok_baseline']:.3f} vs ICM ${sv['cost_per_mtok_icm']:.3f} (Save +${sv['savings_usd_per_mtok']:.3f}/M)")
                elif t.get("total_runs", 0) > 0:
                    arms = list(t.get("arms", {}).keys())
                    print(f"  • {tid:10s} | Runs: {t['total_runs']} | Arms: {arms} (partial)")
            print("=" * 72)
    finally:
        conn.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="A/B Usage Ledger SQLite Engine")
    subparsers = parser.add_subparsers(dest="command")

    # init
    subparsers.add_parser("init", help="Initialize the database schema")

    # seed-pricing
    seed_p = subparsers.add_parser("seed-pricing", help="Seed pricing table from config/PRICING.json")
    seed_p.add_argument("--config", help="Custom path to PRICING.json")

    # summary
    sum_p = subparsers.add_parser("summary", help="Print summary of tasks and savings")
    sum_p.add_argument("task_id", nargs="?", default=None, help="Task ID to summarize")

    # cumulative
    subparsers.add_parser("cumulative", help="Print cumulative measured savings across all tasks")

    args = parser.parse_args()

    if args.command == "init":
        conn = get_connection()
        conn.close()
        print("✓ Ledger database initialized.")
    elif args.command == "seed-pricing":
        p = Path(args.config) if args.config else None
        count = seed_pricing(pricing_path=p)
        print(f"✓ Seeded pricing for {count} model(s) from config/PRICING.json.")
    elif args.command == "cumulative":
        print_summary(None)
    elif args.command == "summary":
        print_summary(args.task_id)
    else:
        # Default behavior: if a task_id is passed as first arg without subcommand
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            print_summary(sys.argv[1])
        else:
            print_summary(None)


if __name__ == "__main__":
    main()
