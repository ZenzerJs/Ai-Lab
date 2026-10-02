# Ai-Lab Implementation Roadmap

Prepared: 2026-10-02
Status: proposed; implementation begins only after local inspection and approval.

## Success definition

A user can prepare a coding task, run a documented agent configuration, capture available evidence, grade the result independently, and reproduce the report without mixing fixtures, unknown historical data, and pricing simulations into measured performance.

## Non-goals

- Rewriting the application or replacing the current stack.
- Claiming official SWE-bench scores for first-party tasks.
- Implementing reinforcement learning or learned incentive mechanisms.
- Certifying historical results without source evidence.
- Inventing provider capabilities or promising publication readiness.
- Automatically running paid model calls or merging changes.

## Architecture boundaries

Reuse existing components where feasible. Inspect `scripts/ledger.py`, `scripts/run_experiment.py`, `dashboard/build_data.py`, pricing configuration, experiment fixtures, task-stage records, and existing tests. New module names and CLI flags must be agreed during Phase 0, not assumed from this plan.

Separate these responsibilities:

| Layer | Responsibility |
|---|---|
| Run preparation | Task snapshot, configuration, isolation, execution manifest |
| Execution adapter | Automated execution if supported; otherwise manual preparation and import |
| Evidence intake | Parse telemetry, retain origin, validate references, redact public output |
| Ledger | Preserve runs, outcomes, provenance, usage, and pricing references |
| Evaluator | Run protected correctness and regression checks against submitted output |
| Reporter | Use shared eligibility rules and explicit missing-data semantics |
| Dashboard | Display reported facts and limitations without reinterpreting them |

The ledger and dashboard exporter must call the same eligibility and accounting helpers rather than implementing different policies.

## Run data model

Adapt to the current schema rather than creating a competing ledger. Proposed concepts:

- Stable run ID, task ID/version, repetition ID, arm, and experiment manifest ID.
- Source kind: `live`, `fixture`, `imported`, or `unknown`.
- Evidence validation status and reasons for exclusion; source kind alone is insufficient.
- Execution status: scheduled, running, completed, failed, timed out, interrupted, or cancelled before execution.
- Verification status: passed, failed, not run, or evaluator error; keep this distinct from execution status.
- Available provider/model identifiers, model settings, budgets, starting commit, environment version, and intervention configuration hash.
- Available timestamps, elapsed time, retries, tool calls, and human interventions.
- Raw telemetry reference, integrity hash, capture origin, and capture time when available.
- Token counters with provider-specific semantics and completeness status.
- Pricing version, currency, price source, and whether cost is observed billing, usage-based estimate, or simulation.

Do not store missing measurements as zero. Do not label inferred settings as observed settings. A provider model label from an import remains a supplied label unless independently established.

## Evidence eligibility

Write an eligibility policy before implementing headline totals. Maintain separate outcomes for verified correctness and evidence-qualified measurement.

- Fixture runs never enter measured performance totals, regardless of task ID.
- Legacy data defaults to unknown; preserve its original values and annotations.
- Importing a record does not establish its live origin. An imported run may qualify only if documented source evidence meets the approved policy.
- A run may have verified correctness but unavailable usage or cost. Keep it in correctness reporting and disclose cost coverage.
- A completed run with missing telemetry is not automatically a failed coding task; it is an evidence completeness problem.
- Evidence validation failures must exclude affected metrics with explicit reasons rather than silently erase the run.
- Public exports must not depend on access to private raw files in a browser. Validate evidence locally and export a safe validation snapshot.
- A checksum supports integrity, not source authenticity. Record source limitations honestly.

## Phase 0 — Inspect and establish baseline

Deliver:

1. Architecture and data-flow inventory based on current source.
2. Current Git status and a list of existing uncommitted files to protect.
3. Baseline checks with actual commands and outcomes.
4. Existing schema, test framework, dependency, and fixture inventory.
5. Capability assessment for Antigravity execution and telemetry capture.
6. Approved proposed file layout, migration approach, test matrix, and CLI interface.
7. Open questions requiring user decisions.

Gate: the implementation plan distinguishes confirmed behaviour, proposed changes, and unresolved assumptions. No live calls or feature implementation in this phase.

## Phase 1 — Trustworthy evidence and accounting

Implement:

- Backward-compatible, repeat-safe migration and transactional failure handling.
- Explicit source kind and evidence-validation fields.
- Dry-run recording that always marks fixture origin.
- Stable import identifiers and duplicate handling.
- Validated telemetry parsing and documented token-counter semantics.
- Shared eligibility, accounting, and exclusion-reason helpers.
- Measured, historical/unknown, fixture, and simulated reporting categories.

Preserve all historical records. Do not automatically promote a row to live because its task starts with `EXP` or because a dashboard calls it empirical.

Gate: provenance, migration, telemetry, accounting, and initial report tests pass against temporary databases. No user database is migrated during automated tests.

## Phase 2 — Safe preparation and execution

Implement:

- Disposable workspace preparation from a pinned task snapshot.
- Protected evaluator files outside the writable agent workspace.
- Run manifests with task instructions, arm configuration, available model settings, budgets, and evidence destinations.
- Automated execution only if genuinely supported.
- Otherwise, manual preparation, completion recording, and evidence import.
- Timeout/interruption recording and documented resume/retry policy.
- Configuration mismatch checks and explicit intentional intervention differences.

Safety: never run destructive reset or cleanup against the user's checkout. Environment isolation is not a security guarantee; treat generated code as untrusted and avoid exposing secrets, host mounts, and unrestricted credentials.

Gate: disposable workspace tests, interruption tests, evaluator-integrity checks, and a fixture-only end-to-end smoke workflow pass.

## Phase 3 — First-party benchmark pack

Implement the six tasks in `03-BENCHMARK-PACK.md` with pinned initial states, task instructions, accessible tests, protected evaluator checks, and reference solutions kept outside agent access.

Gate for every task:

- Initial broken state fails the target check for the expected reason.
- Reference solution passes target checks and preserves previously passing checks.
- A deliberately wrong solution fails.
- Agent changes cannot alter the evaluator or reference material.
- Environment and dependency versions are recorded.

Do not expose reference answers through Git history, shared directories, prompt attachments, or accessible manifests.

## Phase 4 — Controlled repeated comparisons

Implement a matrix planner and report generator. Start with two arms; enable delegation as a third arm only if supported and recorded accurately.

- Same initial task snapshot and comparable total resource budget.
- Fresh sessions and isolated writable state.
- Randomized arm order, recorded ahead of execution.
- Cold-cache and warm-cache conditions reported separately.
- All scheduled attempts retained, including failures and missing evidence.
- Predeclared aggregation and retry policy.
- Sample counts and cost/usage coverage in every relevant report.

Gate: a fixture-driven campaign reproduces expected counts, outcomes, missing-data labels, and ledger/dashboard agreement. A small live smoke run requires separate approval.

## Phase 5 — Evidence-first dashboard

Implement:

- Source and evidence status labels.
- Per-arm scheduled, completed, verified, failed, and excluded counts.
- Correctness reporting separate from cost-eligible sample counts.
- Honest empty states and undefined metric labels.
- Safe evidence metadata and exclusion reasons.
- Visually separate model-price simulations.
- Task-level views alongside pooled summaries.

Gate: browser acceptance checks, export consistency tests, and the actual configured production build pass. Preserve the existing design unless necessary for evidence clarity.

## Phase handoff record

For each phase record:

- Objective and approved scope.
- Changed files and rationale.
- Migration/data implications.
- Added tests and acceptance IDs covered.
- Exact commands, exit codes, and results.
- Skipped checks and reasons.
- Known limitations and unresolved risks.
- Next proposed phase; stop for approval.

## Release checklist

- All offline gates pass on a clean environment.
- Legacy data is preserved and honestly labelled.
- No raw private telemetry or secrets appear in public exports.
- User documentation gives verified commands rather than guessed CLI syntax.
- Paid execution is opt-in with a run-count and budget cap.
- Benchmark tasks are independently graded.
- Reports disclose sample counts, failures, and measurement completeness.
- No performance claims exceed the actual evidence.
