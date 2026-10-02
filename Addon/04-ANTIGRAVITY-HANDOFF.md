# Antigravity Handoff Prompts

Prepared: 2026-10-02
Target: current local Ai-Lab checkout.
Status: instructions for staged implementation; not authorization for paid execution or remote writes.

## Initial planning prompt

Copy this prompt with the other specification files attached or accessible.

```text
You are the implementation lead for the existing Ai-Lab repository.

Read these specifications in order:
- 01-IMPLEMENTATION-ROADMAP.md
- 02-ACCEPTANCE-TEST-MATRIX.md
- 03-BENCHMARK-PACK.md

Objective:
Improve the existing project into a trustworthy, reproducible coding-agent
measurement harness with an offline regression suite and six first-party
benchmark tasks. Preserve the existing architecture and historical data.

Begin with Phase 0 only. Do not implement features yet.

1. Read AGENTS.md and applicable local agent rules.
2. Inspect Git status. Protect existing work and uncommitted files.
3. Inspect actual ledger, runner, export, dashboard, fixtures, pricing,
   task-stage documents, and test implementation.
4. Trace how data enters the ledger and becomes a dashboard metric.
5. Identify working baseline commands and run safe offline checks only.
6. Determine what Antigravity execution and telemetry interfaces are
   actually available. Do not invent a CLI, token counters, cache metrics,
   model-routing capabilities, or billing evidence.
7. If automation is unavailable, plan a manual preparation/import adapter.
8. Produce a reviewable implementation plan, proposed file changes,
   schema migration, evidence eligibility policy, command contract,
   acceptance-test mapping, and unresolved decisions.
9. Distinguish confirmed behaviour, proposed behaviour, and unknowns.
10. Stop for approval before Phase 1.

Mandatory boundaries:
- No live model calls, automatic merges, destructive cleanup, or remote writes.
- No modification to the user's database during automated tests.
- Preserve legacy values; unknown provenance is not proof of fabrication.
- Missing metrics remain unknown, not zero.
- Fixture and simulated data never become empirical headline results.
- Protected evaluators and reference answers stay outside agent access.
- A checksum is integrity evidence, not proof of provider authenticity.
- Reuse existing modules and test tools instead of introducing parallel systems.

For every later phase, run the relevant tests, fix failures without weakening
assertions, rerun checks, and produce a verification record before stopping.
Never claim a phase is complete based on a checklist or UI screenshot alone.
```

## Phase 1 approval prompt

```text
Implement only the approved Phase 1 plan: provenance, backward-compatible
migration, telemetry validation, shared eligibility rules, and accounting.

Preserve historical records. Use temporary databases in tests. Imported data
must not automatically become verified live data. Implement provider-specific
counter semantics only where documented; otherwise keep cost unavailable.

Cover MIG, PROV, IMP, TEL, and ACC acceptance cases. Include shared report
checks necessary to prevent fixtures and simulations entering measured totals.
Run the relevant offline suite and produce the phase verification record.
Stop before Phase 2. Do not run live models or remote writes.
```

## Phase 2 approval prompt

```text
Implement only the approved Phase 2 plan: isolated workspaces, manifests,
execution/import adapter, lifecycle handling, and configuration checks.

Use a manual adapter if the actual environment lacks supported automation.
Keep protected grading material outside the writable workspace. Never reset
or clean the user's checkout. Preserve partial and interrupted attempts.

Cover RUN acceptance cases and build the fixture-only end-to-end smoke flow.
Run Phase 1 regression checks as well. Document actual working commands and
unsupported capabilities. Stop before Phase 3.
```

## Phase 3 approval prompt

```text
Implement the six first-party tasks in 03-BENCHMARK-PACK.md as small pinned
standalone snapshots. Do not mutate active personal production repositories.

Provide task contracts, visible tests, protected evaluators, environments,
reference solutions, and deliberately wrong solutions for validation.
Ensure reference/evaluator material is inaccessible to the evaluated agent,
including through Git history or shared attachments.

Run BEN acceptance cases for every task. Confirm intended broken-state
failures, reference passes, and rejection of wrong patches. Run the existing
regression suite and produce verification evidence. No live model calls.
Stop before Phase 4.
```

## Phase 4 approval prompt

```text
Implement the approved campaign planner and report generator using fixtures
only. Support baseline, staged governance, and optional supported delegation.

Record planned order, task/repetition pairings, budgets, configurations, and
all attempt statuses. Keep correctness counts separate from cost coverage.
Do not mix unknown cache state with verified cold/warm strata. Do not discard
failures or select best-of-many submissions without an explicit protocol.

Cover REP acceptance cases. Re-run prior regression checks. Document the
live smoke procedure but do not execute it. Stop before Phase 5.
```

## Phase 5 approval prompt

```text
Implement the approved evidence-focused dashboard changes. Reuse existing
styling and components; do not turn this into a design rewrite.

Show source kind, evidence status, sample counts, failures, measurement
coverage, exclusions, and honest empty states. Clearly separate simulations.
Use shared report outputs rather than duplicating accounting in the UI.
Keep private raw telemetry and sensitive paths out of public exports.

Cover EXP and UI acceptance cases, run regression checks and the actual
configured build, and produce the final release checklist. Do not merge,
publish, or run live models without separate approval.
```

## Optional live smoke authorization template

Fill every field before execution. This template itself grants no permission.

```text
I approve only this live smoke campaign:
- Task ID/version:
- Arms:
- Attempts per arm:
- Model/provider and available version/settings:
- Execution mode: manual/automated
- Maximum total budget and currency:
- Maximum runtime per attempt:
- Budget enforcement capability and limitations:
- Allowed telemetry capture and storage:
- Human assistance policy:
- Retry policy:
- Stop conditions:

Do not expand the campaign, change providers, or run additional attempts.
Report actual outcomes, missing evidence, failures, and observed usage.
```

## Required completion response

```text
Phase:
Status: complete / blocked / incomplete
Changed files:
Acceptance IDs covered:
Commands executed:
Actual results and exit codes:
Skipped checks and reasons:
Migration/data effects:
Model/API calls:
Limitations:
Next proposed action:
```

An approval for one implementation phase is not approval to run a paid
benchmark campaign, publish artifacts, modify remote GitHub state, or merge.
