# Operational Rule: Deterministic Context Assembly & Byte Stability

## Core Mandate
Prompt context must be assembled deterministically in a strict, layered sequence to maximize LLM KV-cache prefix hits and prevent cache invalidation.

## Assembly Sequence
Context slices must be concatenated strictly in the following order:
1. **System Persona:** Fixed architectural directives, core identity, and operational guidelines.
2. **Tool Definitions:** Stable JSON-RPC / MCP tool schemas.
3. **OKF Concept Slice:** Static, immutable concept excerpts loaded from `docs/` relevant to the current task.
4. **Active Stage Contract:** The current stage document (e.g., `tasks/TSK-001/02_plan.md`) defining objectives and constraints.
5. **Volatile User Input:** Dynamic user prompts, immediate turn instructions, and interactive input.

## Byte-Stability Invariant
Sections 1 through 4 MUST NEVER contain:
- Dynamic timestamps (e.g., `Date: 2026-09-09T16:35:00Z` or current time values).
- Monotonically increasing build counters, process IDs, or ephemeral run IDs.
- Non-deterministic dictionary key iterations or unordered sets.
- Volatile environment metrics or temporary paths.

Any deviation that injects volatile data before Section 5 busts prompt prefix caching, multiplying inference latency and token expenditure across collaborative agent turns.
