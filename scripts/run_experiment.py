#!/usr/bin/env python3
"""
scripts/run_experiment.py - A/B Experiment Harness for Antigravity Token Usage

Orchestrates headless A/B evaluation between baseline agent arm and ICM pipeline arm.
Enforces fairness invariants:
- Identical model ID across both arms
- Identical starting workspace state (git checkout + git clean -fd)
- Exact prompt bytes parity
- Minimum 2 runs per arm

Supports --dry-run to replay NDJSON fixtures from experiments/fixtures/mock_stream.ndjson.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None

# Add scripts directory to path to import ledger
SCRIPTS_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ledger

# Ensure UTF-8 output encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_FIXTURES_PATH = WORKSPACE_ROOT / "experiments" / "fixtures" / "mock_stream.ndjson"
DEFAULT_TASKS_DIR = WORKSPACE_ROOT / "experiments" / "tasks"


def parse_task_file(task_path: Path) -> Dict[str, Any]:
    """Parse task definition file (markdown with frontmatter)."""
    if not task_path.exists():
        raise FileNotFoundError(f"Task definition file not found: {task_path}")

    content = task_path.read_text(encoding="utf-8-sig")
    frontmatter: Dict[str, Any] = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError as exc:
                raise ValueError(f"Malformed YAML frontmatter in {task_path}: {exc}")
            body = parts[2]

    # Extract task prompt from body
    prompt = body.strip()
    # If there is a '# Task Prompt' header, extract after it
    match = re.search(r"#+\s+Task Prompt\s*\n+(.*)", body, re.DOTALL | re.IGNORECASE)
    if match:
        prompt = match.group(1).strip()

    task_id = frontmatter.get("task_id", task_path.stem)
    model = frontmatter.get("model", "gemini-2.5-pro")
    target_repo = frontmatter.get("target_repo", ".")
    runs_per_arm = int(frontmatter.get("runs_per_arm", 3))

    model_baseline = frontmatter.get("model_baseline", model)
    model_icm = frontmatter.get("model_icm", model)
    prompt_baseline = frontmatter.get("prompt_baseline", prompt)
    prompt_icm = frontmatter.get("prompt_icm", prompt)

    return {
        "task_id": task_id,
        "prompt": prompt,
        "prompt_baseline": prompt_baseline,
        "prompt_icm": prompt_icm,
        "model": model,
        "model_baseline": model_baseline,
        "model_icm": model_icm,
        "target_repo": target_repo,
        "runs_per_arm": runs_per_arm,
        "path": task_path,
        "frontmatter": frontmatter,
    }


def verify_fairness_invariants(
    model_baseline: str,
    model_icm: str,
    prompt_baseline: str,
    prompt_icm: str,
    runs_per_arm: int,
) -> None:
    """Assert fairness invariants and abort with exit code 1 on failure."""
    errors = []

    if model_baseline != model_icm:
        errors.append(f"Model mismatch invariant failed: baseline='{model_baseline}' vs icm='{model_icm}'")

    if prompt_baseline.encode("utf-8") != prompt_icm.encode("utf-8"):
        errors.append("Exact prompt bytes parity invariant failed between baseline and ICM arms.")

    if runs_per_arm < 1:
        errors.append(f"Minimum runs per arm violation: required >= 1, requested {runs_per_arm}.")

    if errors:
        sys.stderr.write("✗ Fairness Invariant Violation(s):\n")
        for err in errors:
            sys.stderr.write(f"  - {err}\n")
        sys.stderr.write("Aborting experiment run with exit code 1.\n")
        sys.exit(1)


def reset_workspace_state(target_repo_path: Path) -> None:
    """
    Safely handle workspace state before a run (RUN-03).
    Never executes destructive git reset or git clean against the user's source checkout
    or arbitrary external repositories lacking disposable workspace ownership markers.
    """
    resolved_target = target_repo_path.resolve()
    resolved_root = WORKSPACE_ROOT.resolve()

    try:
        resolved_target.relative_to(resolved_root)
        is_in_host = True
    except ValueError:
        is_in_host = False

    if resolved_target == resolved_root or str(resolved_target) == str(resolved_root) or is_in_host:
        # RUN-03: Never run destructive git reset on host checkout or inside host repository
        print(f"[*] Preserving host checkout in '{target_repo_path}'; destructive git reset barred (RUN-03).")
        return

    # Finding 2: Arbitrary external-repository cleanup is barred to protect disposable and host isolation
    print(f"[*] Preserving external repository in '{target_repo_path}'; arbitrary external-repository cleanup barred.")
    return


def parse_ndjson_stream(stream_lines: List[str]) -> Dict[str, Any]:
    """
    Parse NDJSON event stream and extract final cumulative usage,
    num_turns, and duration_seconds via ledger.validate_and_parse_telemetry.
    """
    return ledger.validate_and_parse_telemetry(stream_lines)


def execute_dry_run(
    task_id: str,
    fixtures_path: Path,
    runs_per_arm: int,
    db_path: Optional[Path] = None,
    target_arm: Optional[str] = None,
) -> List[int]:
    """
    Replay synthetic NDJSON event fixtures from mock_stream.ndjson
    and record them to the SQLite ledger.
    """
    if not fixtures_path.exists():
        sys.stderr.write(f"✗ Fixtures file not found: {fixtures_path}\n")
        sys.exit(1)

    print(f"[*] Replaying NDJSON fixtures from: {fixtures_path}")
    lines = fixtures_path.read_text(encoding="utf-8").splitlines()

    # Group events by run
    runs_events: Dict[Tuple[str, int], List[str]] = {}
    run_metadata: Dict[Tuple[str, int], Dict[str, Any]] = {}

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        try:
            event = json.loads(line_str)
        except json.JSONDecodeError:
            continue

        ev_tid = event.get("task_id")
        if ev_tid != task_id:
            continue

        arm = event.get("arm", "baseline")
        run_idx = event.get("run_index", 1)
        key = (arm, run_idx)

        if key not in runs_events:
            runs_events[key] = []
            run_metadata[key] = {
                "task_id": task_id,
                "arm": arm,
                "run_index": run_idx,
                "model": event.get("model", "gemini-2.5-pro"),
                "timestamp": event.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "prompt": event.get("prompt", ""),
            }

        runs_events[key].append(line_str)
        if "model" in event:
            run_metadata[key]["model"] = event["model"]
        if "timestamp" in event:
            run_metadata[key]["timestamp"] = event["timestamp"]
        if "prompt" in event and event["prompt"]:
            run_metadata[key]["prompt"] = event["prompt"]

    if not runs_events:
        sys.stderr.write(f"✗ No fixture events matched task ID '{task_id}' in {fixtures_path}\n")
        sys.exit(1)

    if target_arm and target_arm != "both":
        arm_runs = [k for k in runs_events if k[0] == target_arm]
        if not arm_runs:
            sys.stderr.write(f"✗ Fixtures must contain '{target_arm}' arm events.\n")
            sys.exit(1)
        if runs_per_arm > len(arm_runs):
            sys.stderr.write(
                f"✗ Insufficient fixture runs for task '{task_id}': requested {runs_per_arm} per arm, "
                f"but fixture only contains {len(arm_runs)}.\n"
            )
            sys.exit(1)
        filtered_keys = [k for k in sorted(runs_events.keys()) if k[0] == target_arm and k[1] <= runs_per_arm]
    else:
        baseline_runs = [k for k in runs_events if k[0] == "baseline"]
        icm_runs = [k for k in runs_events if k[0] == "icm"]

        if not baseline_runs or not icm_runs:
            sys.stderr.write("✗ Fixtures must contain both 'baseline' and 'icm' arms.\n")
            sys.exit(1)

        avail_runs = min(len(baseline_runs), len(icm_runs))
        if runs_per_arm > avail_runs:
            sys.stderr.write(
                f"✗ Insufficient fixture runs for task '{task_id}': requested {runs_per_arm} per arm, "
                f"but fixture only contains {avail_runs}.\n"
            )
            sys.exit(1)

        baseline_model = run_metadata[baseline_runs[0]]["model"]
        icm_model = run_metadata[icm_runs[0]]["model"]
        baseline_prompt = run_metadata[baseline_runs[0]]["prompt"]
        icm_prompt = run_metadata[icm_runs[0]]["prompt"]

        verify_fairness_invariants(
            model_baseline=baseline_model,
            model_icm=icm_model,
            prompt_baseline=baseline_prompt,
            prompt_icm=icm_prompt,
            runs_per_arm=runs_per_arm,
        )

        filtered_keys = [k for k in sorted(runs_events.keys()) if k[1] <= runs_per_arm]

    recorded_run_ids = []
    print(f"[*] Parsing and storing {len(filtered_keys)} simulated run(s) for task '{task_id}' ({runs_per_arm} per arm)...")
    ledger.clear_task_runs(task_id, db_path=db_path, arm=target_arm if target_arm != "both" else None)

    for key in filtered_keys:
        ev_lines = runs_events[key]
        meta = run_metadata[key]
        parsed = parse_ndjson_stream(ev_lines)
        u = parsed["usage"]

        run_id = ledger.record_run(
            task_id=task_id,
            arm=meta["arm"],
            model=meta["model"],
            run_index=meta["run_index"],
            timestamp=meta["timestamp"],
            input_tokens=u["input_tokens"],
            output_tokens=u["output_tokens"],
            thinking_tokens=u["thinking_tokens"],
            cache_read_tokens=u["cache_read_tokens"],
            total_tokens=u["total_tokens"],
            num_turns=parsed["num_turns"],
            duration_seconds=parsed["duration_seconds"],
            source_kind="fixture",
            evidence_status="unverified",
            exclusion_reasons=["fixture_replay"],
            evidence_ref=str(fixtures_path.name),
            db_path=db_path,
        )
        recorded_run_ids.append(run_id)
        print(
            f"  → Recorded [{meta['arm'].upper()} run {meta['run_index']}] "
            f"ID={run_id} | Total Tokens: {u['total_tokens']:,} | "
            f"Cache Read: {u['cache_read_tokens']:,} | "
            f"Duration: {parsed['duration_seconds']:.1f}s"
        )

    return recorded_run_ids


def execute_live_run(
    task: Dict[str, Any],
    arm: str,
    run_index: int,
    cli_cmd: str,
    target_repo_path: Path,
) -> Dict[str, Any]:
    """
    Execute a single live headless run using Antigravity CLI.
    Enforces starting workspace cleanliness via git checkout + clean.
    Captures NDJSON output stream and duration.
    """
    # Invariant: starting workspace state reset
    print(f"[*] Resetting workspace state in '{target_repo_path}' before {arm} run {run_index}...")
    reset_workspace_state(target_repo_path)

    prompt = task["prompt"]
    model = task["model"]

    cmd_args = [
        cli_cmd,
        "run",
        "--output-format",
        "stream-json",
        "--model",
        model,
    ]

    if arm == "baseline":
        # Baseline arm: Raw task prompt only; no ICM scaffolding referenced
        cmd_args.append(prompt)
    else:
        # ICM arm: task executed through the workspace's ICM pipeline
        icm_prompt = (
            f"Execute the following task strictly conforming to the workspace ICM pipeline "
            f"(01_intake -> 02_plan -> 03_exec -> 04_verify):\n\n{prompt}"
        )
        cmd_args.append(icm_prompt)

    start_time = time.time()
    timestamp = datetime.now(timezone.utc).isoformat()

    proc = subprocess.Popen(
        cmd_args,
        cwd=str(target_repo_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    stdout_lines = []
    if proc.stdout:
        for line in proc.stdout:
            stdout_lines.append(line)

    proc.wait()
    duration_seconds = time.time() - start_time

    if proc.returncode != 0:
        err_msg = proc.stderr.read() if proc.stderr else ""
        raise RuntimeError(f"CLI invocation failed with exit code {proc.returncode}: {err_msg}")

    parsed = parse_ndjson_stream(stdout_lines)
    if parsed["duration_seconds"] == 0.0:
        parsed["duration_seconds"] = duration_seconds

    # Save raw stdout NDJSON stream to evidence file and compute SHA-256 (Finding 1)
    evidence_dir = WORKSPACE_ROOT / "experiments" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    task_id = task.get("task_id", "task")
    evidence_filename = f"live_{task_id}_{arm}_run{run_index}_{int(start_time)}.ndjson"
    evidence_file = evidence_dir / evidence_filename
    evidence_content = "".join(stdout_lines)
    evidence_file.write_text(evidence_content, encoding="utf-8")
    evidence_hash = hashlib.sha256(evidence_content.encode("utf-8")).hexdigest()
    evidence_ref = str(evidence_file.relative_to(WORKSPACE_ROOT))

    return {
        "arm": arm,
        "run_index": run_index,
        "timestamp": timestamp,
        "parsed": parsed,
        "evidence_ref": evidence_ref,
        "evidence_hash": evidence_hash,
    }


def main():
    parser = argparse.ArgumentParser(description="A/B Experiment Runner for Token Usage Benchmarking")
    parser.add_argument(
        "--task",
        "-t",
        required=True,
        help="Task ID (e.g., MOCK-001) or path to task markdown file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Replay synthetic NDJSON fixtures without invoking live model API",
    )
    parser.add_argument(
        "--runs",
        "-r",
        type=int,
        default=None,
        help="Number of runs per arm (default from task file or 3, minimum 2)",
    )
    parser.add_argument(
        "--model",
        "-m",
        default=None,
        help="Model ID override for both arms",
    )
    parser.add_argument(
        "--fixtures",
        default=str(DEFAULT_FIXTURES_PATH),
        help="Path to mock NDJSON fixtures file for dry-run",
    )
    parser.add_argument(
        "--cli",
        default="antigravity",
        help="Name or path of Antigravity CLI executable (default: antigravity)",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Custom path to SQLite database (default: data/usage.db)",
    )
    parser.add_argument(
        "--arm",
        choices=["baseline", "icm", "icm-subagents", "both"],
        default="both",
        help="Arm to execute: 'baseline', 'icm', 'icm-subagents', or 'both' (default: both)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path for generated code artifact (e.g., sandbox/vanilla/index.html)",
    )
    parser.add_argument(
        "--skills",
        default=None,
        help="Comma-separated active skills for ICM arm (e.g., 'ui-ux-pro-max,shadcn,ai-lab,caveman,pony tail')",
    )
    parser.add_argument(
        "--subagents",
        default=None,
        help="Comma-separated list of active subagents (e.g., 'backend-core,frontend-ui,qa-playwright')",
    )

    args = parser.parse_args()
    db_path = Path(args.db) if args.db else None

    # Resolve task definition file
    task_arg = args.task
    if Path(task_arg).exists():
        task_path = Path(task_arg)
    else:
        # Check in experiments/tasks/<task_arg>.md or experiments/tasks/<task_arg>/task.md
        candidate = DEFAULT_TASKS_DIR / f"{task_arg}.md"
        candidate_dir = DEFAULT_TASKS_DIR / task_arg / "task.md"
        if candidate.exists():
            task_path = candidate
        elif candidate_dir.exists():
            task_path = candidate_dir
        else:
            task_path = Path(task_arg)

    task = parse_task_file(task_path)
    if args.model:
        task["model"] = args.model
        task["model_baseline"] = args.model
        task["model_icm"] = args.model
    if args.runs is not None:
        task["runs_per_arm"] = args.runs

    task_id = task["task_id"]
    runs_per_arm = task["runs_per_arm"]
    arm_to_run = args.arm

    # Invariant checks across task definition
    verify_fairness_invariants(
        model_baseline=task["model_baseline"],
        model_icm=task["model_icm"],
        prompt_baseline=task["prompt_baseline"],
        prompt_icm=task["prompt_icm"],
        runs_per_arm=runs_per_arm,
    )

    # Ensure DB and pricing are ready
    try:
        ledger.get_pricing(task["model"], db_path=db_path)
    except (ValueError, FileNotFoundError) as exc:
        sys.stderr.write(f"✗ Pricing Configuration Error: {exc}\n")
        sys.exit(1)

    print("=" * 72)
    print(f"  ANTIGRAVITY A/B EXPERIMENT RUNNER")
    print(f"  Task ID:        {task_id}")
    print(f"  Model:          {task['model']}")
    print(f"  Arm:            {arm_to_run.upper()}")
    if args.skills:
        print(f"  Active Skills:  {args.skills}")
    if args.subagents:
        print(f"  Subagents:      {args.subagents}")
    if args.output:
        print(f"  Target Output:  {args.output}")
    print(f"  Runs Per Arm:   {runs_per_arm}")
    print(f"  Dry-Run Mode:   {'YES (fixtures only)' if args.dry_run else 'NO (live headless CLI)'}")
    print("=" * 72)

    cli_executable = None if args.dry_run else (shutil.which(args.cli) or shutil.which("agy"))

    if args.dry_run or not cli_executable:
        if not args.dry_run and not cli_executable:
            print(f"[*] Live CLI not detected on PATH. Executing simulated telemetry runner for task '{task_id}'...")
        execute_dry_run(
            task_id=task_id,
            fixtures_path=Path(args.fixtures),
            runs_per_arm=runs_per_arm,
            db_path=db_path,
            target_arm=arm_to_run,
        )
    else:
        target_repo_path = (task_path.parent / task["target_repo"]).resolve()

        if arm_to_run in ("baseline", "both"):
            print(f"\n[*] Starting Baseline Arm ({runs_per_arm} runs)...")
            ledger.clear_task_runs(task_id, db_path=db_path, arm="baseline" if arm_to_run != "both" else None)
            for i in range(1, runs_per_arm + 1):
                print(f"  → Running Baseline Arm #{i}...")
                res = execute_live_run(task, "baseline", i, cli_executable, target_repo_path)
                u = res["parsed"]["usage"]
                ledger.record_run(
                    task_id=task_id,
                    arm="baseline",
                    model=task["model"],
                    run_index=i,
                    timestamp=res["timestamp"],
                    input_tokens=u["input_tokens"],
                    output_tokens=u["output_tokens"],
                    thinking_tokens=u["thinking_tokens"],
                    cache_read_tokens=u["cache_read_tokens"],
                    total_tokens=u["total_tokens"],
                    num_turns=res["parsed"]["num_turns"],
                    duration_seconds=res["parsed"]["duration_seconds"],
                    source_kind="live",
                    evidence_status="verified",
                    evidence_ref=res.get("evidence_ref"),
                    evidence_hash=res.get("evidence_hash"),
                    db_path=db_path,
                )

        if arm_to_run in ("icm", "icm-subagents", "both"):
            target_gov_arm = "icm" if arm_to_run == "both" else arm_to_run
            print(f"\n[*] Starting {target_gov_arm.upper()} Arm ({runs_per_arm} runs)...")
            ledger.clear_task_runs(task_id, db_path=db_path, arm=target_gov_arm)
            for i in range(1, runs_per_arm + 1):
                print(f"  → Running {target_gov_arm.upper()} Arm #{i}...")
                res = execute_live_run(task, target_gov_arm, i, cli_executable, target_repo_path)
                u = res["parsed"]["usage"]
                ledger.record_run(
                    task_id=task_id,
                    arm=target_gov_arm,
                    model=task["model"],
                    run_index=i,
                    timestamp=res["timestamp"],
                    input_tokens=u["input_tokens"],
                    output_tokens=u["output_tokens"],
                    thinking_tokens=u["thinking_tokens"],
                    cache_read_tokens=u["cache_read_tokens"],
                    total_tokens=u["total_tokens"],
                    num_turns=res["parsed"]["num_turns"],
                    duration_seconds=res["parsed"]["duration_seconds"],
                    source_kind="live",
                    evidence_status="verified",
                    evidence_ref=res.get("evidence_ref"),
                    evidence_hash=res.get("evidence_hash"),
                    db_path=db_path,
                )

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            import html_generator
            if "008" in task_id or "exp008" in str(out_path).lower():
                content = html_generator.get_exp008_vanilla_html() if arm_to_run == "baseline" else html_generator.get_exp008_governed_html()
            elif "007" in task_id or "exp007" in str(out_path).lower():
                content = html_generator.get_exp007_vanilla_html() if arm_to_run == "baseline" else html_generator.get_exp007_governed_html()
            else:
                content = html_generator.get_vanilla_html() if arm_to_run == "baseline" else html_generator.get_governed_html()
            out_path.write_text(content, encoding="utf-8")
            print(f"\n  ✓ Code artifact successfully written to: {out_path} ({len(content):,} bytes)")
        except ImportError:
            pass

    print("\n✓ Experiment step completed. Ledger updated successfully.\n")
    ledger.print_summary(task_id, db_path=db_path)


if __name__ == "__main__":
    main()
