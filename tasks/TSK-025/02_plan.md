# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-025
- **Title:** Multi-Dimensional Benchmark Scoring Rubric & Evaluation Architecture
- **Status:** APPROVED
- **Owner:** Systems Engineering & Research Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Pre-Registered 5-Dimension Rubric (0–5 Scale Each)

Every paired run (`baseline` vs. `governed`) is scored 0–5 on five orthogonal dimensions. Automated gates compute deterministic base scores; blind A/B review resolves subjective ties.

| Dimension | Automated Signal (Primary) | Blind A/B Judge Signal (Secondary) | 0 (Fail) | 3 (Acceptable) | 5 (Exemplary) |
|---|---|---|---|---|---|
| **1. Correctness** | `pytest` / Playwright assertion pass rate | Edge-case coverage check | <50% assertions pass or runtime crash | All core happy-path tests pass | 100% assertions + edge cases pass |
| **2. Engineering Practices** | Typecheck (`tsc`/`mypy`), linter (`ruff`/`eslint`), test delta | Idiomatic stdlib/platform usage (YAGNI) | New lint/type errors or broken build | Zero new warnings; basic tests included | Zero warnings, deterministic tests, minimal dependency footprint |
| **3. Maintainability** | Diff line churn (`git diff --numstat`), max function AST depth/LOC | Readability, single-responsibility clarity | Bloated diff (>3x minimal), dead code left | Clean diff, modular functions (<50 LOC) | Surgical diff, self-documenting symbols, zero dead code |
| **4. Process Discipline** | Out-of-scope file touches, unapproved full-file overwrites | Contract adherence | Touches forbidden files or bypasses gates | Stays within target files; minor churn | Exact manifest match, diff-only edits, zero wasted turns |
| **5. Design & UX** *(UI tasks)* | Playwright axe/a11y violations, zero horizontal overflow (375/768/1440px) | Visual hierarchy, token consistency, states | Layout overflow, missing focus/a11y, broken states | Responsive, accessible contrast, clean layout | Intentional typography/spacing, complete async/empty states, zero a11y defects |

*Note: For pure backend/CLI tasks, Dimension 5 is omitted and total score is normalized to 0–20 (or scaled to 100%).*

---

## 2. Blind Pairwise Evaluation Protocol

1. **Automated Harvester First:** Run static/dynamic checks inside `DisposableWorkspace` immediately post-run before teardown.
2. **Sanitization & Blinding:** Strip `tasks/TSK-XXX/` contract artifacts and arm labels from diff bundles. Assign randomized labels (`Arm_Alpha`, `Arm_Beta`) seeded by `campaign_id`.
3. **Cross-Family Judge + Human Spot-Check:** Evaluate blinded diffs using a judge model distinct from the execution model, verified by human spot-check on ≥25% of pairs.
4. **Statistical Reporting:** Compute paired difference ($\Delta = \text{Score}_{\text{governed}} - \text{Score}_{\text{baseline}}$) with 95% bootstrap confidence intervals across $n \ge 20$ paired tasks.

---

## 3. Minimal Architecture & Impacted Files Manifest (`ponytail` compliant)

Reuse existing `runs.notes` JSON column in `data/usage.db` (`quality_scores` key) instead of a database migration.

- `tasks/TSK-025/01_intake.md` (Created)
- `tasks/TSK-025/02_plan.md` (Created)
- `scripts/campaign.py` (Future `03_exec`: add `score_workspace(workspace_path, manifest)` helper using stdlib `subprocess` + `ast` to populate `slot.notes["quality_scores"]`)
- `tests/unit/test_quality_rubric.py` (Future `03_exec`: unit tests for deterministic rubric calculation)

---

## 4. OKR Acceptance Matrix

| Objective | Key Result | Machine-Verifiable Exit Command | Expected Value | Status |
|---|---|---|---|---|
| **O1: Pre-Registered Rubric** | KR1.1: Stage 01 & 02 contracts exist with deterministic 5-dimension rubric | `python scripts/filter_output.py -- python -c "import pathlib; assert pathlib.Path('tasks/TSK-025/01_intake.md').exists() and pathlib.Path('tasks/TSK-025/02_plan.md').exists()"` | `exit=0` | COMPLETE |
| **O2: Automated Scorer** | KR2.1: Deterministic scorer unit tests pass when implemented in Stage 03 | `python scripts/filter_output.py -- python -m pytest tests/unit/test_quality_rubric.py -q -p no:cacheprovider` | `exit=0` | COMPLETE |
| **O3: Docs Integrity** | KR3.1: OKF frontmatter linter passes | `python scripts/filter_output.py -- python scripts/lint_frontmatter.py` | `exit=0` | COMPLETE |
