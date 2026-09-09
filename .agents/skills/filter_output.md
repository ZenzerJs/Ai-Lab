# Agent Skill: `filter_output`

## Overview
The `filter_output` skill executes test runners, linters, and build commands within a noise-canceling wrapper. It protects agent context windows from being blown by voluminous test outputs, compiler chatter, or dependency notices.

## Core Invariants
- Preserves and returns the native exit code of the wrapped process.
- **Success (exit code 0):** Collapses output into a single line: `✓ Command succeeded: <cmd>`.
- **Failure (non-zero):** Strips noise and emits only the failing assertion, file path, line number, and immediate stack trace.

## Usage

### Command Line
```bash
python scripts/filter_output.py -- <command> [args...]
```

### PowerShell Shim (Windows)
```powershell
.\scripts\filter_output.ps1 -- pytest tests\
```

### POSIX Shim (Linux / macOS)
```bash
./scripts/filter_output.sh -- pytest tests/
```

## When to Use
- Stage `04_verify` for running all automated tests, linters, and type-checkers.
- Any time a shell command could potentially emit >20 lines of output.
- Enforcing `.agents/rules/log-sanitation.md`.
