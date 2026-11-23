# ICM v2: Zero-Ceremony Governed Contract

Execute this task in a tight **Repro -> Surgical Diff -> Verify** loop:

1. **Repro**: Use the pre-injected AST symbol map below to locate the exact target file and symbol without full-file dumps. Run the targeted failing test first to reproduce the defect.
2. **Surgical Diff**: Apply minimal, targeted search/replace edits strictly within the declared target scope.
3. **Verify**: Workspace smoke tests are minimal and do not cover every requirement. Before finishing, inspect and verify ALL requirements and invariants in `INSTRUCTIONS.md` with targeted edge-case checks, and re-run the test suite until everything passes.

## Zero-Ceremony Rules
- Do NOT create stage files (`01_intake.md`, `02_plan.md`, `03_exec.md`, `04_verify.md`).
- Do NOT write `05_retro` essays or retrospective summaries.

## Loop-Breaker Directive
- After 2 consecutive failing test or tool runs on the same target, STOP editing immediately.
- Inspect the failing line and its caller symbol.
- State a new 1-line root-cause hypothesis before applying your next edit.

## Concise Test Output
- Run tests with concise flags (e.g., `pytest -q --tb=short` or `python3 -m unittest`) so only minimal failure assertions, file paths, line numbers, and immediate tracebacks enter context. Never dump verbose raw test logs.
