# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-009
- **Title:** GitHub Pages Dashboard — Real Data, Few Impactful Statistics
- **Status:** IN_REVIEW (awaiting user sign-off → `03_exec.md`)
- **Prerequisite:** `01_intake.md` (see §0 for decision resolutions)
- **Executor:** Gemini (Antigravity agent). Read §6 "Executor Guardrails" before touching anything.

---

## 0. Ground Truth (verified 2026-10-03 — do not re-derive, do not contradict)

| Fact | Evidence |
|---|---|
| **Every row in `data/usage.db` (EXP-001…008, MOCK-001) is a dry-run fixture replay**, not a real session. | Identical values in `experiments/fixtures/mock_stream.ndjson` (e.g. `input_tokens: 9800` at lines 15, 33). |
| The "61.9% cheaper / 16× cache / 55% faster" figures quoted earlier in this conversation came from those fixtures. **They are retracted and must not appear anywhere.** | — |
| The only real-provenance dataset today is EXP-005 operational (`data/ops_exp005.db`, glm-5.3-flash). It shows ICM: 0/8 defect runs vs 2/8, **+65% duration, 2× turns**. | `data.json → operational` |
| The user really ran tasks 1–7 in Antigravity, with and without the harness. The transcripts exist (37 sessions under `~/.gemini/antigravity/brain/*/` mention `EXP-00x`). | `transcript.jsonl` per session |
| **Transcripts contain no token/usage fields** (keys: `step_index, source, type, status, created_at, content, thinking, tool_calls`). From transcripts we can get duration, step/tool-call counts, files touched and outcome. We cannot get tokens or cost. | Key scan of `transcript_full.jsonl` |
| The harness already has a correct live path: `agy … --output-format stream-json` → `experiments/evidence/*.ndjson` + SHA-256 → `source_kind="live"`. The eligibility engine (`ledger.evaluate_run_eligibility`) accepts these rows. | `scripts/run_experiment.py` L328, L374-391, L555-558 |
| `agy` v1.2.16 is **installed** at `C:\Users\jayde\AppData\Local\agy\bin\agy.exe` but not yet on PATH in already-open terminals (restart terminal, or prepend that dir to `$env:Path`). | Installer output + `--version` |
| **Track B is viable.** `agy -p "<prompt>" --output-format stream-json` emits a final `result` event with `usage{input_tokens, output_tokens, thinking_tokens, cache_read_tokens, total_tokens}`, `duration_seconds`, `num_turns`. Verified 2026-10-03 with a 1-word prompt (22,742 input tokens, 0 cached). | Smoke test, conversation `3acc3222…` |
| Note: a bare `agy` session already carries ~22.7k input tokens of tool/system context, so absolute token counts include that fixed overhead in both arms. | Smoke test |

### Intake decision resolutions
1. Legacy runs: **fixtures**. They stay out of all public numbers (they can remain in a "Harness demo" fixture view inside the methodology drawer, labeled as such).
2. Live re-run: **yes, at $0 API cost**, through the Antigravity CLI (`agy`) on the user's existing Antigravity quota. No API-key billing.
3. Primary story: decided by data, not up front (§1.3 headline rules).
4. Sandbox viewer: kept, demoted to "See the output" section (it's real generated output, a credible proof artifact).

---

## 1. Technical Approach

### 1.1 Data Track A — Real-session operational import (free, immediate)
Import the user's real Antigravity sessions for EXP-001…007 as an **operational dataset**, the same class as `ops_exp005.db`: turns/duration/outcome, no tokens.

1. **`experiments/session_manifest.json`** (CREATE). Maps conversation IDs → `{task_id, arm: "baseline"|"icm", outcome: "pass"|"fail"|"unknown", notes}`.
   - Gemini **proposes** candidates by scanning transcripts (first `USER_INPUT` mentions `EXP-00x`; harness arm = session references `tasks/TSK-` stage contracts or `/ai-lab`). It writes them with `"confirmed": false`.
   - **The user confirms each row.** The importer only ingests rows with `"confirmed": true`.
2. **`scripts/import_sessions.py`** (CREATE, + `.ps1`/`.sh` shims). For each confirmed row:
   - Copy `transcript.jsonl` → `experiments/evidence/session_<task>_<arm>_<convid8>.jsonl`, compute SHA-256.
   - Derive: `duration_seconds` (first→last `created_at`), `num_turns` (count `USER_INPUT`), `model_steps` (count `PLANNER_RESPONSE`), `tool_calls`, `files_edited` (count of write/replace tool calls), `outcome` (from manifest).
   - Write to **`data/ops_sessions.db`**, using the `ops_exp005.db` schema plus `evidence_ref`, `evidence_hash`, `source_kind="live_session"`, `outcome`. Token columns stay NULL. **Never invent tokens.**
3. Generalize `build_operational_payload` in `dashboard/build_data.py` so it reads a list of ops DBs (`ops_exp005.db`, `ops_sessions.db`), each with its own model/provider metadata, instead of the hard-coded glm block.

### 1.2 Data Track B — Live token telemetry via `agy` (free on Antigravity quota)
1. `agy` is installed (v1.2.16) and `--output-format stream-json` confirmed. In each shell run `$env:Path = "C:\Users\jayde\AppData\Local\agy\bin;$env:Path"` first, or restart the terminal. **If `agy` is not resolvable or usage fields come back null, STOP Track B and report.** Do not substitute fixtures.
   - Before the campaign, check `scripts/run_experiment.py` (~L320-335) builds the command as `agy -p <prompt> --output-format stream-json` and parses the final `result` event. The harness was written against an assumed CLI shape, so reconcile any mismatch (diff-only edit) and add a unit test with a recorded real `result` line.
   - Pin one `--model` (see `agy models`) for both arms and record it in the evidence.
2. Smoke test with one run: `python scripts/run_experiment.py --task EXP-001` with `runs_per_arm: 1` override → confirm one evidence file plus 2 rows with `source_kind=live` and non-null `input_tokens`.
3. Full campaign: EXP-001…007, **n=3 per arm** (42 runs). Run into a **fresh DB** `data/usage_live.db` (`--db`). Point `build_data.py` at it via `--db` / env `AILAB_DB`.
4. `data/usage.db` (fixtures) is kept only for the fixture/demo view and is never merged into the live DB.

### 1.3 Headline block (`build_data.py` → `data.json.headline`)
Computed server-side so the UI just renders. Each stat = `{label, value, unit, baseline, icm, n_baseline, n_icm, n_tasks, source, ci95?: [lo, hi]}`.

| Slot | Stat | Source | Emit only if |
|---|---|---|---|
| H1 | Δ cost per **passing** task (%) | Track B | ≥3 tasks with ≥3 comparison-eligible runs/arm |
| H2 | Pass/defect rate baseline vs ICM | Track A ∪ Track B ∪ EXP-005 ops | ≥8 runs/arm with known outcome |
| H3 | Cache-hit % baseline vs ICM | Track B | same as H1 |
| H4 (trade-off, always shown if data exists) | Δ wall-clock duration (%) | Track A ∪ B ∪ ops | ≥8 runs/arm |

- CI: paired bootstrap over tasks (10k resamples, seeded `random.Random(9)`), pure stdlib.
- `headline.sentence`: generated from whichever of H1/H2 qualifies, e.g. `"Across {n_tasks} real tasks, the ICM harness {cut cost by X% | cut defect runs from a/n to b/n}"`. If no stat qualifies → `headline = null`.
- **Sign is reported as measured.** If ICM is slower or more expensive, the number says so.

### 1.4 UI — single page, no tabs (`dashboard/src`)
Top to bottom:
1. **Header** (slim: title, `generated_at`, `build_identity`, GitHub link). No tabs, no refresh-button chrome.
2. **`HeroStats`**: `headline.sentence` + up to 3 big stat tiles (H1–H3), each with `n` and a source chip (`live CLI` / `live session` / `operational`). If `headline=null`, show one "Collecting live data — N of 42 runs recorded" progress tile.
3. **`TradeoffCallout`**: H4 duration/turns, stated plainly.
4. **`TaskComparison`**: one chart. Dumbbell, baseline vs ICM per task, metric toggle `cost | duration | pass rate` (only metrics with data are enabled). Sorted by effect size. Built by adapting `PerTaskComparison.tsx`.
5. **`TaskTable`**: task × {n, pass rate, cost, tokens, cache %, turns, duration} with Δ columns. Empty cells show `—`, never 0.
6. **"See the output"**: `SandboxViewer`, collapsed by default.
7. **`<details>` Methodology & audit**: fairness invariants, exclusion reasons, `RawLedgerTable`, rate-card simulator (`SpendCascadeComparison` + `ModelSelector`, labeled SIMULATION), fixture demo view (labeled FIXTURE).

**Delete** (first confirm no other importers via `ast-grep` / `rg`): `ExecutiveShowcase.tsx`, `CumulativeSavings.tsx`, `ScaleSelector.tsx`, `RollingCounter.tsx`, `hooks/useAnimatedCounter.ts`, `ExperimentCards.tsx`, `CacheHitRatio.tsx`, `TurnsDuration.tsx` (folded into table/chart), `OperationalBenchmarkCard.tsx` (folded into hero/table), `public/visual_showcase.html`, `public/visual_showcase_2.html`.
Remove `projected_savings_10m/100m` and `scaleMode` plumbing from `types.ts` / `recalculate.ts`.

---

## 2. Impacted Files Manifest

| Target File Path | Action | Description & Rationale | Diff Block Required (>50 lines) |
|---|---|---|---|
| `experiments/session_manifest.json` | CREATE | Convid → task/arm/outcome; user-confirmed | No |
| `scripts/import_sessions.py` (+ `.ps1`, `.sh`) | CREATE | Track A importer with evidence hashing | No |
| `data/ops_sessions.db` | CREATE (generated) | Track A output | n/a |
| `data/usage_live.db` | CREATE (generated) | Track B output | n/a |
| `experiments/evidence/*` | CREATE (generated) | Hashed evidence files | n/a |
| `dashboard/build_data.py` | MODIFY | `--db`/`AILAB_DB`, multi-ops loader, `headline` block | Yes |
| `scripts/ledger.py` | MODIFY (only if needed) | Accept `source_kind="live_session"` as operational, not cost-measured | Yes |
| `dashboard/src/App.tsx` | MODIFY | Single-page layout | Yes |
| `dashboard/src/types.ts` | MODIFY | `Headline` types; drop scale/projection fields | Yes |
| `dashboard/src/lib/recalculate.ts` | MODIFY | Drop scale logic | Yes |
| `dashboard/src/components/Header.tsx` | MODIFY | Remove tabs | Yes |
| `dashboard/src/components/HeroStats.tsx` | CREATE | Headline + tiles | No |
| `dashboard/src/components/TradeoffCallout.tsx` | CREATE | H4 | No |
| `dashboard/src/components/TaskComparison.tsx` | CREATE (from `PerTaskComparison.tsx`) | One chart | No |
| `dashboard/src/components/TaskTable.tsx` | CREATE | Per-task table | No |
| `dashboard/src/components/MethodologyDrawer.tsx` | CREATE | Wraps ledger/simulator/fixtures | No |
| Components listed in §1.4 "Delete" | DELETE | Bloat removal | n/a |
| `.github/workflows/deploy-dashboard.yml`, `ci.yml` | MODIFY | **Blocker found in final check:** `data/*.db` is gitignored and no DB/evidence is tracked, so `python dashboard/build_data.py` in CI builds from an empty DB and overwrites the tracked `data.json` snapshot with demo/empty data. Fix: build `data.json` **locally**, commit it plus `experiments/evidence/*` (hashed proof), and remove the `build_data.py` step from the deploy workflow (or make it a verify-only check that `data.json` matches evidence hashes). Do not un-ignore the DBs. | No |
| `tests/unit/test_headline.py` | CREATE | Headline gating + honesty tests | No |
| `tests/unit/test_import_sessions.py` | CREATE | Importer tests on a synthetic transcript in `tmp_path` | No |
| `tests/browser/test_dashboard_production.py` | MODIFY | New layout assertions | Yes |
| `docs/log.md`, `docs/concepts/` (provenance concept) | MODIFY | Record retraction + new data classes | Per size |

---

## 3. OKR Acceptance Matrix

**Objective:** The public dashboard shows ≤4 headline numbers, every one traceable to a hashed real-run evidence file, on a single page.

| KR | Deterministic Success Metric | Automated Verification Command (via `filter_output.py`) | Status |
|---|---|---|---|
| **KR1** Honesty gate | With only fixture/unknown rows, `headline is None`. With a fixture row injected into a live DB, it is excluded from every headline stat. | `python scripts/filter_output.py -- python -m pytest tests/unit/test_headline.py -q` | PENDING |
| **KR2** Session import | Importer ingests only `confirmed:true` rows, writes a SHA-256 that matches the copied file, leaves token columns NULL. | `python scripts/filter_output.py -- python -m pytest tests/unit/test_import_sessions.py -q` | PENDING |
| **KR3** Track A data present | `data.json.operational` includes ≥1 dataset with `source_kind=="live_session"` and ≥2 tasks. | `python scripts/filter_output.py -- python -c "import json;d=json.load(open('dashboard/public/data.json'));assert any(x.get('source_kind')=='live_session' for x in d['operational']['datasets'])"` | PENDING |
| **KR4** Track B data present *(conditional on `agy`)* | `comparison_eligible_runs_count ≥ 42`, `is_demo_report == false`, `headline.stats` non-empty. | `python scripts/filter_output.py -- python -c "import json;d=json.load(open('dashboard/public/data.json'));c=d['cumulative'];assert c['comparison_eligible_runs_count']>=42 and not d['is_demo_report'] and d['headline']"` | PENDING |
| **KR5** No fixture leakage | No headline/hero value derives from a run with `source_kind in {fixture, unknown}`. | covered by KR1 + `python scripts/filter_output.py -- python -m pytest tests/unit/test_provenance.py -q` | PENDING |
| **KR6** Bloat removed | Deleted components absent; no `scaleMode` / `projected_savings` references in `src/`. | `python scripts/filter_output.py -- python -c "import pathlib,sys;s=''.join(p.read_text() for p in pathlib.Path('dashboard/src').rglob('*.ts*'));sys.exit(any(k in s for k in ['ExecutiveShowcase','ScaleSelector','projected_savings','RollingCounter']))"` | PENDING |
| **KR7** Build + types | `tsc` + Vite build exit 0. | `python scripts/filter_output.py -- npm --prefix dashboard run build` | PENDING |
| **KR8** Layout | Playwright: no `role=tablist`; hero shows ≤3 stat tiles, each containing `n=`; Methodology is a closed `<details>` on load. | `python scripts/filter_output.py -- python -m pytest tests/browser/test_dashboard_production.py -q` | PENDING |
| **KR9** Regression | Existing unit/integration suites pass. | `python scripts/filter_output.py -- python -m pytest tests/unit tests/integration -q` | PENDING |
| **KR10** OKF docs | Frontmatter lint clean. | `python scripts/filter_output.py -- python scripts/lint_frontmatter.py` | PENDING |

---

## 4. Execution Order (for `03_exec.md`)
1. **Phase 1, Track A:** manifest proposal → **pause for user confirmation** → importer + tests (KR2) → build_data multi-ops (KR3).
2. **Phase 2, headline:** `headline` block + tests (KR1, KR5). It works with Track A alone: H2/H4 can qualify before any token data exists.
3. **Phase 3, UI:** single page + deletions (KR6–KR8). Ship to Pages at this point. The site is honest even before Track B.
4. **Phase 4, Track B:** `agy` check → 1-run smoke test → **pause, report smoke result to user** → 42-run campaign → rebuild (KR4).
5. **Phase 5:** KR9, KR10, `04_verify.md`, `05_retro.md`, `docs/log.md` entry (includes the fixture retraction).

---

## 5. Stage Gate Transition Check
- [x] Technical architecture reviewed and validated.
- [x] Impacted files manifest populated.
- [x] OKR Acceptance Matrix defined with automated verification commands.
- [x] **User sign-off to transition to `03_exec.md`.** (granted 2026-10-03)

---

## 6. Executor Guardrails (Gemini: non-negotiable)
1. **Never set `source_kind`, `evidence_status`, `verification_status`, or `evidence_hash` on existing `data/usage.db` rows.** Re-tagging fixtures as live is falsification. The only way a row becomes eligible is through the harness or the importer writing a real evidence file.
2. **Never type a number into UI copy, README, retro, or commit message.** Every displayed number comes from `data.json`.
3. **Never fill missing tokens/cost** with estimates, averages, or rate-card math. Show `—`.
4. If a measured result is unflattering (ICM slower or more expensive), **publish it**. Do not drop the stat, re-scope the task set, or re-run until it looks better.
5. Do not invent task names/descriptions. Use the `# Task Prompt` heading/first line from `experiments/tasks/<ID>.md`.
6. Stop and report (don't work around it) when: `agy` is missing, the smoke test yields null tokens, or fewer than 2 confirmed sessions exist for a task/arm.
7. Workspace rules apply: diff-only edits for files >50 lines (`.agents/rules/diff-only-editing.md`); every test/build command goes through `scripts/filter_output.py`; no sequential-thinking tool in `03_exec`/`04_verify`; no git writes until `03_exec`.
