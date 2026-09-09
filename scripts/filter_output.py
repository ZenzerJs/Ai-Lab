#!/usr/bin/env python3
"""
scripts/filter_output.py - Test and Build Command Output Sanitizer

Wraps test, build, and linter commands to prevent terminal output floods
from blowing context limits and busting prompt prefix caching.

Behavior:
- On success (exit code 0): Emits a single line: "✓ Command succeeded: <cmd>"
- On failure (non-zero): Strips verbose noise and isolates failing assertion,
  file, line number, and immediate stack trace.
- Always preserves and returns the native exit code of the wrapped process.
"""

import os
import re
import shlex
import subprocess
import sys

# Ensure UTF-8 output encoding on all platforms including Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

NOISE_PATTERNS = [
    re.compile(r"^\[notice\]", re.IGNORECASE),
    re.compile(r"^WARNING:.*pip", re.IGNORECASE),
    re.compile(r"^\s*cached:\s*", re.IGNORECASE),
    re.compile(r"^\s*\.+\s*$"),  # Dots from test progress
    re.compile(r"^Platform\s+", re.IGNORECASE),
    re.compile(r"^rootdir:\s+", re.IGNORECASE),
    re.compile(r"^plugins:\s+", re.IGNORECASE),
    re.compile(r"^\s*collected \d+ items?", re.IGNORECASE),
    re.compile(r"^\s*-+\s*$"),  # Plain separator lines
]


def is_noise(line: str) -> bool:
    """Determine if a line is superfluous runner noise."""
    stripped = line.strip()
    if not stripped:
        return True
    for pat in NOISE_PATTERNS:
        if pat.search(stripped):
            return True
    return False


def extract_failure_context(stdout: str, stderr: str) -> str:
    """Extract failing assertion, file, line number, and immediate stack trace."""
    combined = []
    if stderr:
        combined.extend(stderr.splitlines())
    if stdout:
        combined.extend(stdout.splitlines())

    if not combined:
        return "Command failed with non-zero exit code (no output recorded)."

    traceback_lines = []
    in_traceback = False
    in_failures_section = False
    failure_blocks = []

    for line in combined:
        # Python traceback detection
        if "Traceback (most recent call last):" in line:
            in_traceback = True
            traceback_lines = [line]
            continue
        if in_traceback:
            traceback_lines.append(line)
            # If line is non-indented error name after File lines, traceback ends
            if re.match(r"^[A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Exit|Interrupt):", line) or (
                line and not line.startswith(" ") and not line.startswith("\t")
            ):
                in_traceback = False
                failure_blocks.append("\n".join(traceback_lines))
                traceback_lines = []
            continue

        # Pytest failure section detection
        if re.search(r"={3,}\s+FAILURES\s+={3,}", line):
            in_failures_section = True
            continue
        if in_failures_section:
            if re.search(r"={3,}\s+short test summary info\s+={3,}", line):
                in_failures_section = False
            else:
                if not is_noise(line):
                    failure_blocks.append(line)
            continue

        # Direct assertions, errors, and file/line references
        if re.search(r"(?:AssertionError|Error|Exception|FAILED|FAILURE|fatal):", line, re.IGNORECASE):
            failure_blocks.append(line)
        elif re.search(r'File ".*", line \d+', line):
            failure_blocks.append(line)
        elif line.strip().startswith("E   ") or line.strip().startswith(">   "):
            failure_blocks.append(line)
        elif "fatal error" in line.lower() or "error:" in line.lower():
            failure_blocks.append(line)

    if traceback_lines:
        failure_blocks.append("\n".join(traceback_lines))

    if failure_blocks:
        return "\n".join(failure_blocks)

    # Fallback: Filter out known noise, return remaining lines
    filtered = [l for l in combined if not is_noise(l)]
    if filtered:
        return "\n".join(filtered)

    return "\n".join(combined[:30])


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python filter_output.py [--] <command> [args...]\n")
        sys.exit(2)

    raw_args = sys.argv[1:]
    if raw_args[0] == "--":
        cmd_args = raw_args[1:]
    elif "--" in raw_args:
        dash_idx = raw_args.index("--")
        cmd_args = raw_args[dash_idx + 1:]
    else:
        cmd_args = raw_args

    if not cmd_args:
        sys.stderr.write("Error: No command specified to execute.\n")
        sys.exit(2)

    cmd_display = " ".join(cmd_args)

    try:
        proc = subprocess.run(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as fnf:
        sys.stderr.write(f"Command not found: {cmd_args[0]}\n")
        sys.exit(127)
    except Exception as exc:
        sys.stderr.write(f"Execution error: {exc}\n")
        sys.exit(1)

    if proc.returncode == 0:
        print(f"✓ Command succeeded: {cmd_display}")
        sys.exit(0)
    else:
        failure_summary = extract_failure_context(proc.stdout, proc.stderr)
        sys.stderr.write(f"✗ Command failed with exit code {proc.returncode}: {cmd_display}\n")
        sys.stderr.write(failure_summary + "\n")
        sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
