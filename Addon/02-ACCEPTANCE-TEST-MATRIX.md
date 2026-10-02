# Ai-Lab Acceptance-Test Matrix

Prepared: 2026-10-02
Status: requirements for implementation, not existing test results.

## Test strategy

Use the repository's existing Python test framework where feasible; pytest is the recommended default if one is needed. Use temporary directories and SQLite databases, deterministic fixture inputs, controlled clocks where necessary, and mocks for external calls. Reuse the existing browser framework where practical.

All default tests must run without model APIs. Assert that live execution adapters are never invoked in offline mode. Installing dependencies is a separate environment setup operation; offline test execution must not download packages or contact providers.

No arbitrary test-count or coverage percentage is a substitute for these behaviours. Parameterize cases where useful and report actual collected tests.

## Phase 1 — Migration and provenance

| ID | Setup and action | Expected result |
|---|---|---|
| MIG-01 | Migrate a legacy database containing known original values | Values and row counts preserved; unestablished source kind becomes unknown |
| MIG-02 | Apply the migration twice | Second application makes no destructive or duplicate changes |
| MIG-03 | Inject a migration failure | Transaction is rolled back or recovery behaviour is explicit and tested |
| PROV-01 | Replay fixture telemetry with task ID EXP-008 | Fixture classification; absent from measured totals |
| PROV-02 | Insert an unknown legacy run | Visible in historical view; excluded from evidence-qualified metrics |
| PROV-03 | Import telemetry without source evidence | Remains imported/unverified; cannot silently qualify as live |
| PROV-04 | Validate a referenced artifact with mismatching hash | Evidence invalid; affected metrics excluded with a reason |
| PROV-05 | Validate missing or unreadable evidence | No fabricated metadata; explicit unavailable/invalid status |
| IMP-01 | Import the same run twice | Idempotent ingestion or clear duplicate rejection |
| IMP-02 | Same ID arrives with conflicting content | Explicit conflict; no silent overwrite |

## Phase 1 — Telemetry and accounting

| ID | Setup and action | Expected result |
|---|---|---|
| TEL-01 | Parse malformed NDJSON and invalid event fields | Useful validation error with event location; no accidental valid-run record |
| TEL-02 | Omit usage counters from a completed run | Usage remains unknown; not zero |
| TEL-03 | Supply negative counts or invalid numeric values | Input rejected according to documented validation policy |
| TEL-04 | Replay duplicated events | No double counting; documented duplicate handling |
| TEL-05 | Supply cumulative counters plus per-turn counters | Correct total under the declared adapter schema; no double summation |
| ACC-01 | Use a tiny hand-calculated rate-card fixture | Result agrees with documented decimal/rounding rules |
| ACC-02 | Cache counters are a subset of provider input tokens | Cached and uncached input charged once under that adapter's rules |
| ACC-03 | Cache counters are separate under another adapter | Correct total without imposing the previous provider's semantics |
| ACC-04 | Thinking tokens lack documented billing semantics | No guessed bill; unavailable or qualified cost status |
| ACC-05 | Model rate is absent | Cost unavailable rather than zero or borrowed from another model |
| ACC-06 | Apply a different model rate to a recorded run | Simulation labelled separately; empirical totals unchanged |
| ACC-07 | Incomplete telemetry has partial usage | Partial cost labelled incomplete; not a complete-run bill |

## Phase 2 — Runner and isolation

| ID | Setup and action | Expected result |
|---|---|---|
| RUN-01 | Prepare two arms from a task snapshot | Same starting state; separate writable directories |
| RUN-02 | Write in arm A | Arm B and source checkout unchanged |
| RUN-03 | Existing user files and uncommitted changes are present | Preparation and cleanup preserve them |
| RUN-04 | Model/configuration differs unintentionally | Mismatch rejected or segregated; not silently pooled |
| RUN-05 | Governance instructions differ intentionally | Difference recorded; same task specification remains shared |
| RUN-06 | Simulate timeout | Timed-out attempt retained with available partial evidence |
| RUN-07 | Simulate interruption and resume/import | Original attempt preserved; no invented completion or duplicate run |
| RUN-08 | Execute the offline workflow | No provider or paid adapter invocation |
| RUN-09 | Agent edits test files in its workspace | Protected evaluator remains intact and determines grading |
| RUN-10 | Compare recorded and actual evaluator hashes | Tampering detected; verification marked invalid/evaluator error |
| RUN-11 | Manual adapter lacks usage telemetry | Correctness can be evaluated; usage and cost remain unavailable |

## Phase 3 — Benchmark validation

For each of the six tasks, require all four cases below. Task-specific protected tests are specified in the benchmark document.

| ID | Setup and action | Expected result |
|---|---|---|
| BEN-01 | Evaluate the initial broken snapshot | Target test fails for the intended reason |
| BEN-02 | Evaluate the reference solution | Target tests pass and previously passing checks remain green |
| BEN-03 | Evaluate a deliberately wrong patch | Protected tests reject it |
| BEN-04 | Inspect workspace and accessible history | Reference answers and evaluator-only material inaccessible to agent |

A flaky result blocks release. Record repeated reference evaluations on the same pinned environment and investigate differing outcomes rather than averaging them away.

## Phase 4 — Scheduling and reporting

| ID | Setup and action | Expected result |
|---|---|---|
| REP-01 | Generate a 2-task, 2-arm, 2-repeat fixture campaign | Eight unique scheduled attempts; stable manifest |
| REP-02 | Include failed, timed-out, and unexecuted attempts | Every attempt retained with separate status and execution coverage |
| REP-03 | Supply uneven sample counts | Per-arm counts visible; no appearance of a balanced experiment |
| REP-04 | No eligible measured runs exist | Honest empty state; no synthetic substitute |
| REP-05 | Baseline estimated cost is zero | Savings percentage undefined; absolute values still reported |
| REP-06 | All verified outcomes fail | Cost per success undefined, not zero |
| REP-07 | A correct run lacks token telemetry | Included in correctness count; excluded from cost sample with reason |
| REP-08 | One member of a pair lacks complete cost | Pair excluded from paired cost difference; missing-pair count reported |
| REP-09 | Cold and warm cache conditions coexist | Separate strata; no silent combined headline |
| REP-10 | Large and small tasks coexist | Task-level results retained; pooling method explicit |

## Phase 5 — Export and browser acceptance

| ID | Setup and action | Expected result |
|---|---|---|
| EXP-01 | Compare shared ledger report with JSON export | Same counts, eligibility decisions, costs, and completeness labels |
| EXP-02 | Put sentinel secrets and private paths in raw evidence | Public export omits them |
| UI-01 | Open a fixture-only report | Demo label visible; no measured-performance headline |
| UI-02 | Open mixed-provenance data | Source labels, exclusion reasons, and sample counts visible |
| UI-03 | Filter by task/arm/source | Counts and charts update consistently |
| UI-04 | Missing cost or zero eligible rows | Unavailable/empty state; no NaN, Infinity, or fake zero cost |
| UI-05 | Open pricing simulator | Simulation clearly distinguished from model measurements |
| UI-06 | Run configured production build | Actual build succeeds; warnings and skipped checks disclosed |

## Proposed test organization

This layout is a proposal. Adapt it after inspecting existing imports and test discovery.

```text
 tests/
   unit/          # eligibility, parsers, pricing, report calculations
   integration/   # migrations, imports, exporter, workspace lifecycle
   benchmark/     # pack integrity and reference-solution acceptance
   e2e/           # end-to-end fixture pipeline and dashboard flows
```

Protected task evaluators should be stored separately from agent-accessible benchmark snapshots.

## Command contract

Phase 0 must publish actual working commands for:

1. Unit and integration checks.
2. Complete offline regression suite.
3. Fixture-only smoke workflow using a temporary database.
4. Reference benchmark acceptance.
5. Dashboard/browser checks and production build.
6. Optional explicitly approved live smoke run.

Do not assume a new CLI command or flag exists. `python -m pytest` may be a suitable starting point only after dependencies, discovery, and the absence of unintended live calls are confirmed.

## Verification evidence template

```markdown
# Phase verification
- Phase:
- Date:
- Commit/worktree state:
- Acceptance IDs covered:
- Commands:
- Exit codes and actual results:
- Failed or skipped checks:
- Data migration effects:
- External/model calls: none / approved details
- Remaining limitations:
- Ready for next phase: yes/no, with reason
```

## Testing reference

[pytest monkeypatch documentation](https://docs.pytest.org/en/stable/how-to/monkeypatch.html) describes replacing dependencies and environment values for isolated tests. Use the installed version's documentation when implementation details differ.
