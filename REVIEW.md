# Ai-Lab pre-merge review checklist

Review changes against these repository invariants. Flag violations with the
affected code and a concrete fix; do not treat simulated or fixture output as
empirical evidence.

## Published dashboard snapshot

- Preserve `dashboard/public/data.json`, the published 134-run empirical snapshot.
  Never regenerate or overwrite it without an explicit request and a verified,
  complete `data/usage.db`. A fixture-only or empty database is not sufficient.
- Keep old snapshots readable: new payload fields must be optional or have safe
  defaults. Preserve missing-cost, evidence eligibility, and simulation semantics.
- Distinguish routing guidance and projected savings from measured results. Do
  not invent ICM-Lite records or infer LOC/file counts from token usage.

## Cross-module arm parity

- Check `baseline`, `icm`, `icm_lite`, `icm-subagents`, and `delegation` consistently
  across runner/CLI routing, ledger ingestion and summaries, exporter, TypeScript
  types, selectors, simulations, labels, filters, and evidence exports.
- Respect the declared `governed_arm`; do not silently relabel or select full ICM
  when a comparison explicitly uses ICM-Lite. Preserve raw IDs in exported data.
- Auto routing uses ICM-Lite only for exactly one target file and <150 estimated
  LOC. At ≥150 LOC, 2+ files, or unknown scope/size, use full five-stage ICM.
  Cover boundary and ambiguous-metadata cases; the threshold is not a savings guarantee.

## Benchmark calibration and isolation

- Preserve identical model IDs, task scope, acceptance tests, and equivalent task
  instructions across comparison arms; only the governance contract may differ.
- Keep deterministic fixtures, calibration checks, and independent hidden
  regression oracles meaningful. New BENCH tasks should exercise genuine
  multi-module behavior, not trivial implementations that pass mirrored tests.
- Run arms in isolated, disposable worktrees. Never execute live experiments
  against a dirty tree; runner cleanup can discard work. Use `MOCK-001 --dry-run`
  on a clean tree for offline compatibility verification.
- Keep fixture, imported, live, simulated, excluded, and cost-incomplete evidence
  separate, with source provenance and comparison eligibility intact.

## OKF v0.2 and repository discipline

- Follow `AGENTS.md` and `.agents/rules/`: staged contracts, symbol-level context,
  targeted diffs, and sanitized verification output.
- Keep `docs/index.md` frontmatter limited to `okf_version: "0.2"`; validate
  required metadata, case-sensitive paths, schema rules, and links for other OKF docs.
- Use a feature branch and PR; never push directly to `main`. Do not commit
  credentials, runtime databases, generated fixture snapshots, or unrelated changes.

## Required verification before opening a PR

Run from the repository root through `scripts/filter_output.py` (run the final
command from `dashboard/` with `../scripts/filter_output.py`):

```sh
python3 scripts/filter_output.py -- python3 -m pytest tests/unit/ -v --tb=short
python3 scripts/filter_output.py -- python3 -m pytest tests/browser/test_dashboard_production.py::TestSnapshotIntegrity tests/browser/test_dashboard_production.py::TestPagesWorkflowRegression -v --tb=short
python3 scripts/filter_output.py -- python3 scripts/lint_frontmatter.py
python3 scripts/filter_output.py -- python3 scripts/run_experiment.py --task MOCK-001 --dry-run
cd dashboard && python3 ../scripts/filter_output.py -- npm test && python3 ../scripts/filter_output.py -- npm run build
```

Confirm `git diff --exit-code origin/main -- dashboard/public/data.json` and all
required CI checks pass. For UI changes, inspect light/dark themes, narrow
layouts, empty states, and existing snapshot behavior.
