# Ai-Lab Improvement Pack

Prepared: 2026-10-02
Status: proposed implementation specification; not a claim that features exist.
Target: the existing ZenzerJs/Ai-Lab repository, implemented locally with Antigravity.

## Objective

Turn the existing agent-governance and token-economics project into a trustworthy evaluation harness. Preserve the Python scripts, SQLite measurement layer, React/TypeScript dashboard, task-stage workflow, and historical records where practical. Build evidence integrity before expanding live experiments.

## Files and reading order

1. `01-IMPLEMENTATION-ROADMAP.md`: architecture boundaries, phases, review gates, and completion criteria.
2. `02-ACCEPTANCE-TEST-MATRIX.md`: offline regression cases and phase exit requirements.
3. `03-BENCHMARK-PACK.md`: six first-party coding tasks and a controlled comparison protocol.
4. `04-ANTIGRAVITY-HANDOFF.md`: copy-ready initial prompt and subsequent phase prompts.

Keep these files together. A proposed repository location is `docs/improvement-plan/`; this is a suggestion, not an assertion about the current layout.

## How to use this pack

1. Open the actual Ai-Lab checkout in Antigravity.
2. Supply all four specification files as context.
3. Paste the Initial planning prompt from `04-ANTIGRAVITY-HANDOFF.md`.
4. Let Antigravity complete Phase 0 only: inspect, establish the baseline, and produce a plan.
5. Review the plan before approving Phase 1.
6. Approve one phase at a time. Require command output and actual test results before advancing.
7. Approve live model usage separately, after the offline harness and benchmark checks pass.

These documents do not authorize external writes, automatic merges, destructive cleanup, or paid calls.

## Important distinctions

- Harness tests validate the software, not the capability of a model.
- Fixture replay validates pipeline mechanics, not measured performance.
- Live benchmark results describe the exact tested configuration and tasks, not all coding agents.
- Rate-card simulations estimate alternate pricing; they are not alternate-model experiments.
- A valid hash establishes artifact integrity, not that a provider actually emitted the artifact.
- A passing reference solution checks benchmark mechanics; it is not an evaluated agent run.

## Source and implementation limitations

The earlier repository review used directory listings and indexed code excerpts rather than a complete execution audit. Existing paths are starting points for inspection, not proof that their behaviour matches documentation. Phase 0 must inspect the current local source and replace assumptions with evidence.

Do not assume Antigravity exposes a headless CLI, provider billing, token counters, per-agent model assignment, or every desired metric. Use a manual execution/import adapter when necessary and disclose its limitations.

## Suggested first milestone

Finish Phases 0–3 before a broad live campaign. That produces a tested measurement pipeline, safe execution/import workflow, and six independently graded benchmark tasks.

Do not start with an RL training loop, a full UI rewrite, multiple providers, or a large external benchmark integration. Those are follow-up decisions, not prerequisites.
