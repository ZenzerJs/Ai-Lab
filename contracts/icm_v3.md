# ICM v3: Batch-First Governed Contract

Execute this task in a tight **Parallel Batch-First 3-Turn Cadence** using the pre-injected static workspace context below:

1. **Turn 1 — Batch Read**: Use the pre-injected static workspace AST symbol map, file list, and detected test command below; batch-read only the target files not fully clear from the map in a single parallel turn.
2. **Turn 2 — Inline Plan & Parallel Edits**: Write a concise <=8-line inline plan and batch-apply minimal edits across all target files in parallel within declared scope.
3. **Turn 3 — Verify & Stop**: Run the detected concise test command (`pytest -q --tb=short` or `python -m unittest`), inspect and verify ALL requirements and edge-case invariants in `INSTRUCTIONS.md`, and stop immediately once green.

## Zero-Ceremony Rules
- Do NOT create stage files (`01_intake.md`..`05_retro.md`) or write any files under `tasks/`.
- Do NOT write retrospective essays or redundant post-verification summaries.

## Pragmatic Edit Fallback
- Use targeted search/replace edits on files >120 LOC.
- If an edit tool fails once (e.g., CRLF or whitespace mismatch), fall back immediately to a single clean full-file write instead of retrying the failed diff.

## Loop-Breaker & Strict Containment
- After 2 consecutive failures on the same target, STOP editing immediately, inspect the failing line and its caller symbol, and state a new 1-line root-cause hypothesis before the next edit.
- Stay strictly inside the workspace: NEVER traverse parent directories (`..`) and NEVER invoke missing external scripts.
- Use concise test flags (`pytest -q --tb=short` or `python -m unittest`) so only minimal failure assertions and tracebacks enter context.
