# ICM v2: Zero-Ceremony Governed Contract

Execute this task in a tight **Repro -> Surgical Diff -> Verify** loop:

1. **Repro**: Use the pre-injected AST symbol map below to locate the exact target file and symbol without full-file dumps. Run the targeted failing test first to reproduce the defect.
2. **Surgical Diff**: Apply minimal, targeted search/replace edits strictly within the declared target scope.
3. **Verify**: Run the relevant automated checks until all tests pass.

## Zero-Ceremony Rules
- Do NOT create stage files (`01_intake.md`, `02_plan.md`, `03_exec.md`, `04_verify.md`).
- Do NOT write `05_retro` essays or retrospective summaries.

## Loop-Breaker Directive
- After 2 consecutive failing test or tool runs on the same target, STOP editing immediately.
- Inspect the failing line and its caller symbol.
- State a new 1-line root-cause hypothesis before applying your next edit.

## Sanitized Test Output
- Run test and build commands through `python3 scripts/filter_output.py -- <command>` (or equivalent sanitized wrapper) so only the minimal failing assertion, file, line number, and immediate stack trace enter context. Never dump verbose raw test logs.
