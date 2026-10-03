# Ai-Lab First-Party Coding Benchmark Pack

Prepared: 2026-10-02
Status: task specifications to implement; no performance results claimed.

## Purpose

Measure whether staged governance and, when supported, delegation change correctness, resource consumption, latency, and human intervention on controlled coding tasks.

These are first-party tasks. Do not call their results official SWE-bench scores or evidence of general superiority. SWE-bench's isolated patch-and-test evaluation is a useful design reference, not an endorsement of this pack.

## Shared task contract

Each task needs:

- Immutable task ID/version and pinned initial snapshot.
- Plain-language task instructions and explicit acceptance criteria.
- Environment/dependency specification and verification commands.
- Agent-accessible visible tests and representative examples.
- Protected evaluator tests unavailable to the agent.
- Reference solution unavailable to the agent, including through Git history.
- Allowed edit scope and common safety restrictions.
- Time/resource budget and timeout policy agreed before the campaign.
- A hash or version for the task snapshot and evaluator.
- Expected failures of the broken snapshot and reference verification output.

Do not use active personal production repositories as disposable benchmark workspaces. Create small standalone snapshots that reproduce the required failure modes.

## BENCH-001 — Boundary bug

### Agent assignment

Fix a Python date-range helper that incorrectly includes the exclusive end date or excludes the inclusive start date. Preserve the documented public API and handle reversed or invalid ranges according to the supplied contract.

### Accessible material

Function source, API documentation, visible ordinary-range tests, and a requirements/environment file.

### Protected checks

- Start date included, end date excluded.
- Equal start/end returns an empty range.
- Single-day and month/year boundary transitions behave correctly.
- Reversed and invalid inputs follow the explicit contract.
- Existing valid behaviour remains unchanged.

### Release evidence

Broken snapshot fails a boundary case. Reference fix passes. A patch that simply changes every comparison without input handling is rejected.

## BENCH-002 — Cross-file API contract

### Agent assignment

Update a small Python API server and client consumer from a flat item list to a documented paginated response. Preserve client data processing and handle empty pages and request errors. (Note: Initial pack implements a Python server/client contract; a TypeScript/browser task may be added in future iterations).

### Accessible material

Server handler (`server.py`), client consumer (`client.py`), schema/contract definitions, and visible contract tests (`tests/test_client.py`).

### Protected checks

- Response shape and client parsing agree on pagination metadata.
- Empty and populated pages process correctly.
- Pagination metadata (`total_items`, `page`, `page_size`, `has_next`) is correct.
- Error responses do not masquerade as successful empty data.
- No unrelated public endpoints change.

### Release evidence

Old mismatch fails integration checks. Reference implementation passes both server and client tests. A server-only fix is rejected.

## BENCH-003 — Behaviour-preserving parser refactor

### Agent assignment

Split a Python event parser into maintainable modules while preserving its public entry point, return values, and documented error behaviour.

### Accessible material

Existing parser, public API specification, sample inputs, and representative golden tests.

### Protected checks

- Golden outputs match exactly.
- Documented exceptions and invalid-input handling remain compatible.
- Import paths/public API remain supported.
- Input ordering and Unicode cases remain correct.
- No new network access or mutable global state is introduced.

### Release evidence

A faulty refactor that changes error handling is rejected. Reference refactor passes all compatibility checks. A no-op submission fails only if structural refactoring requirements are explicitly defined and objectively checked.

## BENCH-004 — Filter controller state regression

### Agent assignment

Fix a stale filter state in a Python filter-controller class. Preserve the filter logic, keyboard event handling (e.g. Escape key resets), and multi-criteria sequence processing. (Note: Initial pack implements a Python state controller; a full browser Playwright task may be added in future iterations).

### Accessible material

Controller source (`filter_controller.py`), sample dataset, visible tests (`tests/test_filter_controller.py`), and documented state transition requirements.

### Protected checks

- Changing filters updates filtered rows and result count.
- Clearing filters or pressing Escape resets the complete dataset.
- Sequence of filter changes handles resets cleanly without stale residue.
- Empty result states return expected structure without exceptions.
- Key event handler correctly processes Escape and reset actions.

### Release evidence

Protected tests fail on the broken snapshot and pass on the reference solution. Patches modifying unrelated state or breaking keyboard handlers are rejected.

## BENCH-005 — Distractor resistance and scope control

### Agent assignment

Fix a specific configuration-precedence bug in a repository with irrelevant files and explicitly dated stale design notes. Follow the current task contract and modify only the allowed source area.

### Accessible material

Current task specification, relevant source, visible tests, irrelevant modules, and stale documents clearly distinguished from authoritative requirements.

### Protected checks

- Precedence follows the current contract across supplied combinations.
- No prohibited files are modified.
- Existing unrelated behaviour remains unchanged.
- No dependency or network access is added to solve a local logic bug.

### Release evidence

A solution that follows stale notes fails. Reference fix succeeds with a minimal allowed diff. Treat this as context/scope robustness, not a general security benchmark.

## BENCH-006 — Test quality through faulty variants

### Agent assignment

Write tests for a supplied validator or accounting helper. Do not change the implementation. The task specification describes required behaviour, including error and boundary cases.

### Accessible material

Correct implementation, public contract, test tooling, and illustrative examples.

### Protected checks

- Submitted tests pass against the correct implementation.
- Tests fail against predefined faulty variants: reversed comparison, removed validation, missing boundary case, double-counted cache input, and swallowed error.
- Tests do not depend on external networks, time, user paths, or provider calls.
- Tests do not hard-code implementation identities or inspect hidden mutation labels.
- Implementation files remain unchanged.

### Metrics

Report faulty variants detected out of the predefined valid variants. Do not present this as a universal mutation score. Invalid/non-runnable variants are separately disclosed and excluded according to a predeclared rule.

## Experimental arms

| Arm | Configuration | Question |
|---|---|---|
| A | Task instructions and common safety rules, without mandatory stage gates | Baseline behaviour |
| B | Same task plus intake/plan/execute/verify governance | Added effect of staged governance |
| C | Arm B plus delegation when supported | Added effect of delegation |

Keep common evaluator restrictions and safety requirements in every arm. The baseline is not permitted to damage files merely to create a contrast.

Record governance instructions as the intended intervention. Task instructions and starting state are identical, but prompt bytes need not be identical because the intervention changes instructions.

If multiple mechanisms change between A and B, interpret the result as the combined workflow effect. To isolate pruning or individual gates, define separate later ablations. Do not attribute a combined result to one component.

## Fairness and contamination controls

- Use the same model/settings and comparable total budgets initially.
- Include all delegated calls and overhead in Arm C measurements.
- Start fresh sessions; prevent writable memory or artifacts from leaking across arms.
- Randomize and record arm order before execution.
- Pin tool/dependency versions and note provider/model-version changes.
- Keep reference patches and protected tests outside agent access (organizational separation: evaluators and solutions are kept external to copied workspaces; note this is structural layout rather than OS sandbox access enforcement).
- Record human assistance using a predeclared policy. Assisted runs remain labelled.
- Run evaluator checks after the agent finishes; evaluator compute is separate from agent execution compute.
- Count failed attempts and retries rather than selecting the best submission.
- Treat evaluator errors separately from agent failures; retain them and follow a documented repair/rerun rule.

## Cache conditions

Do not infer actual cache state from session freshness. A fresh conversation does not guarantee a provider cache miss.

- Label intended cache condition and available observed cache telemetry separately.
- Report cold/warm comparisons only if the execution interface can establish or meaningfully characterize them.
- Otherwise label cache state unknown and avoid causal cache claims.
- Never infer cache hits simply because prompt prefixes repeat.

## Execution stages

1. Offline: validate all tasks and reference solutions; no model calls.
2. Live smoke: one task, Arms A and B, one attempt each, after explicit budget approval.
3. Pilot: six tasks, three supported arms, five repetitions each = 90 scheduled attempts.
4. If delegation is unsupported: six tasks, two arms, five repetitions each = 60 attempts.
5. Expand only after inspecting pilot failures, measurement completeness, and resource use.

Five repetitions is a pilot choice, not proof of statistical significance. Do not estimate the whole campaign bill from unverified historical dashboard numbers. Set a budget cap and stop policy before execution; if the execution interface cannot enforce billing caps, disclose that limitation.

## Reporting definitions

- Scheduled attempts: all predeclared trial slots, including unexecuted slots.
- Execution coverage: executed attempts divided by scheduled attempts.
- Verified success rate: successes divided by executed attempts; failures/timeouts included, evaluator errors disclosed separately.
- Campaign completion rate: successes divided by scheduled attempts, labelled separately from success rate.
- Cost coverage: attempts with sufficiently complete usage/cost evidence divided by executed attempts.
- Usage-based cost: computed with a documented rate card; not actual provider billing unless supported.
- Cost per verified success: total complete observed/estimated attempt spend divided by verified successes only when the spend coverage is sufficient; otherwise explicitly partial/unavailable.
- Paired differences: same task and repetition, with comparable settings and complete evidence for the metric. Report excluded/missing pairs.
- Savings percentage: undefined if baseline cost is zero.
- Latency: agent execution wall time; disclose queueing, human intervention, and evaluator timing separately where available.

Report task-level outcomes before pooled summaries. Include counts, variation, failures, missing evidence, and pricing versions. Do not headline a cost reduction without adjacent correctness outcomes.

## Run checklist

Before each approved live attempt:

1. Confirm task snapshot, evaluator version, arm, repetition, and available model settings.
2. Prepare a disposable workspace and fresh session.
3. Confirm evaluator/reference material is inaccessible.
4. Confirm budget/time limits and telemetry capabilities.
5. Execute without changing the task or grader mid-run.
6. Preserve available output, usage, status, and assistance records.
7. Evaluate the submitted output independently.
8. Import with honest provenance and validate available evidence.
9. Inspect the report and exclusions before counting the result.

## Design reference

[SWE-bench evaluation harness](https://www.swebench.com/SWE-bench/reference/harness/) documents its Docker-based reproducible evaluation approach. Integrating official SWE-bench is a later optional project with its own environment and resource requirements.
