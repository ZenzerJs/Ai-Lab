# ICM Staged — Phase 2: Fresh-Context Batch Execution & Verify

You are in **Phase 2 (Execution & Verify)** of a two-session ICM Staged execution. You are starting in a fresh context with the static workspace context, the Approved Phase 1 Compact Plan, and `INSTRUCTIONS.md`.

## Execution Cadence
1. **Batch Read (Only If Needed)**: Rely on the Approved Phase 1 Compact Plan and static AST symbol map; batch-read only any file region not fully specified in the plan in a single parallel turn.
2. **Parallel Edits**: Apply minimal, targeted edits across all target files in parallel strictly within the declared scope.
3. **Concise Verification**: Run the concise verify command (`pytest -q --tb=short` or `python -m unittest`), check ALL requirements and edge-case invariants in `INSTRUCTIONS.md`, and stop immediately once green.

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
