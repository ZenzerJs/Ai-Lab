# ICM Staged — Phase 1: Explore & Plan (Read-Only)

You are in **Phase 1 (Explore & Plan)** of a two-session ICM Staged execution. Your sole job is to inspect the workspace and produce a compact, actionable edit plan for a fresh Phase 2 execution session.

## Strict Read-Only & Zero-Ceremony Rules
- **FORBIDDEN from modifying or creating any files** on disk (no source edits, no test edits, no temp files).
- Do NOT create stage files (`01_intake.md`..`05_retro.md`) or write any files under `tasks/`.
- Stay strictly inside the workspace: NEVER traverse parent directories (`..`) and NEVER invoke missing external scripts.

## Exploration Cadence
1. Start from the pre-injected static workspace file list, detected test command, and AST symbol map below.
2. Batch-read only the target files and relevant tests needed to resolve exact symbols, line ranges, and edge-case invariants in `INSTRUCTIONS.md`.
3. Do NOT run edits or destructive commands. Once you have the exact facts, emit the compact plan and stop immediately.

## Required Output Format
Output ONLY a compact, structured edit plan using these exact sections:

### Target Files
- Relative paths of files to modify (and any new files required by `INSTRUCTIONS.md`).

### Symbols & Line Ranges
- Exact functions, classes, and 1-based line ranges in each target file that must change.

### Invariants & Exact Changes
- Concise bullet list of every requirement, edge case, error message, and exact change per symbol.

### Verify Command
- Exact concise test command to run in Phase 2 (e.g., `pytest -q --tb=short` or `python -m unittest`).
