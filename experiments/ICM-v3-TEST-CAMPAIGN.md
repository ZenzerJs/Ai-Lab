# ICM v3 & ICM Staged Test Campaign Playbook

This playbook targets the exact coverage gaps in the current 802-run snapshot (`dashboard/public/data.json`) so the newer workflows (**`icm_v3`** and **`icm_staged`**) have matched, statistically meaningful comparisons across models and harder multi-file tasks.

---

## 1. Current Data Gaps (from the 802-run snapshot)

| Arm | Live Runs | Models Covered | Tasks Covered | Key Gap |
|---|---:|---|---|---|
| **`icm_v3`** | **16** | `gemini-3.8-flash-low` only | 8 tasks (`BENCH-005..008, 014, 016..018`, 2 reps) | 0 runs on Argon, Hydrogen, Claude, Neon, or `BENCH-021..034`. Early Flash signal is strong (`$0.0593/run` vs `$0.1235` baseline, `11/16` passes). |
| **`icm_staged`** | **4** | `gemini-3.8-flash-low` only | 4 tasks (`BENCH-007, 008, 014, 018`, 1 rep) | Only 1 rep on 4 tasks; 0 runs on large repos where two-session context shedding matters most. |
| **Hard multi-file suites** | **0 priced** | — | `BENCH-021`..`BENCH-034` | All `BENCH-021..034` runs so far are unpriced (`swe-2-max-lightning`, `gemini-4-neon-devin`, `claude-fable-5-2-devin`). |

---

## 2. Local Antigravity (`agy`) CLI Batches (Priced Models)

> [!IMPORTANT]
> Always hydrate `data/usage.db` from `dashboard/public/data.json` first so existing 802 runs are preserved, and run batches from a clean checkout or disposable worktree.

### Step 0: Hydrate the local SQLite ledger (PowerShell)

```powershell
python scripts/hydrate_db.py --from-snapshot dashboard/public/data.json --db data/usage.db --force
```

### Batch 1 (Highest ROI): Matched `icm_v3` + `icm_staged` on Argon & Hydrogen

Both `gemini-4-argon-low` and `gemini-4-hydrogen-low` already have `baseline` and `icm` (`icm_v1`) runs on `BENCH-001`..`BENCH-012`. Running `icm_v3` and `icm_staged` on `BENCH-007`..`BENCH-012` immediately unlocks full Pareto frontier curves for both models (24 runs per model):

```powershell
# 1A. gemini-4-argon-low (24 runs: 6 tasks x 2 arms x 2 reps)
python scripts/campaign.py plan-batch `
  --tasks BENCH-007,BENCH-008,BENCH-009,BENCH-010,BENCH-011,BENCH-012 `
  --arms icm_v3,icm_staged `
  --repetitions 2 `
  --model gemini-4-argon-low `
  --output tmp/manifest_argon_v3_staged.json

python scripts/campaign.py execute-batch `
  --manifest tmp/manifest_argon_v3_staged.json `
  --db data/usage.db `
  --cli agy `
  --timeout 240

# 1B. gemini-4-hydrogen-low (24 runs: 6 tasks x 2 arms x 2 reps)
python scripts/campaign.py plan-batch `
  --tasks BENCH-007,BENCH-008,BENCH-009,BENCH-010,BENCH-011,BENCH-012 `
  --arms icm_v3,icm_staged `
  --repetitions 2 `
  --model gemini-4-hydrogen-low `
  --output tmp/manifest_hydrogen_v3_staged.json

python scripts/campaign.py execute-batch `
  --manifest tmp/manifest_hydrogen_v3_staged.json `
  --db data/usage.db `
  --cli agy `
  --timeout 240
```

### Batch 2: Hard Multi-File Stress Test (`BENCH-021`..`BENCH-034`) on Flash

Tests `baseline` vs `icm_v3` vs `icm_staged` on 6 larger multi-file tasks where two-phase fresh-context execution is designed to shed exploration bloat (36 runs total):

```powershell
python scripts/campaign.py plan-batch `
  --tasks BENCH-021,BENCH-022,BENCH-024,BENCH-027,BENCH-030,BENCH-034 `
  --arms baseline,icm_v3,icm_staged `
  --repetitions 2 `
  --model gemini-3.8-flash-low `
  --output tmp/manifest_flash_hard_v3.json

python scripts/campaign.py execute-batch `
  --manifest tmp/manifest_flash_hard_v3.json `
  --db data/usage.db `
  --cli agy `
  --timeout 240
```

### Batch 3: Close Flash `icm_staged` Rep 2 & `BENCH-017` Gaps (5 runs)

```powershell
python scripts/campaign.py plan-batch `
  --tasks BENCH-007,BENCH-008,BENCH-014,BENCH-018 `
  --arms icm_staged `
  --repetitions 1 `
  --start-repetition 2 `
  --model gemini-3.8-flash-low `
  --output tmp/manifest_flash_staged_rep2.json

python scripts/campaign.py execute-batch `
  --manifest tmp/manifest_flash_staged_rep2.json `
  --db data/usage.db `
  --cli agy `
  --timeout 240
```

### Export updated snapshot after batches finish

```powershell
python dashboard/build_data.py dashboard/public/data.json
cd dashboard; npm test; npm run build; cd ..
```

> Note: When opening a GitHub PR that updates `dashboard/public/data.json`, apply the `data-publish` PR label so CI's snapshot guard passes.

---

## 3. Copy-Paste Prompt for ChatGPT Codex (Free Account)

Use this prompt directly in **ChatGPT Codex** pointed at `ZenzerJs/Ai-Lab` (never paste API keys or share account credentials):

```text
Work in ZenzerJs/Ai-Lab on a new branch from main.

Goal: Add an OpenAI/Codex model cohort comparing baseline vs icm_v3 vs icm_staged on hard multi-file benchmarks, or (if outbound network/CLI execution is disabled in the Codex sandbox) add clean Codex CLI adapter support + unit tests and a ready-to-run manifest without touching dashboard/public/data.json unless verified live runs were executed.

First check whether the local Codex CLI can make live model calls in this environment:
1. Read scripts/runner.py, scripts/campaign.py, scripts/hydrate_db.py, and contracts/registry.json.
2. If live CLI calls work here:
   - Hydrate data/usage.db from dashboard/public/data.json using:
     python scripts/hydrate_db.py --from-snapshot dashboard/public/data.json --db data/usage.db --force
   - Plan and execute a matched campaign on BENCH-007, BENCH-008, BENCH-014, BENCH-018, BENCH-021, BENCH-024 across arms baseline,icm_v3,icm_staged (repetitions=2) using your available Codex/GPT model ID matching config/PRICING.json if applicable.
   - Verify all runs in data/usage.db, export dashboard/public/data.json via python dashboard/build_data.py dashboard/public/data.json, and keep all NDJSON files under experiments/evidence/.
3. If the sandbox is offline / cannot run live Codex CLI calls:
   - Do NOT fabricate or simulate live runs, and do NOT modify dashboard/public/data.json.
   - Inspect how scripts/runner.py invokes CLI tools (_resolve_cli_binary / _invoke_cli_phase) and add clean, tested support for `--cli codex` (parsing Codex JSON/NDJSON usage events and token counts cleanly into the ledger schema), plus unit tests in tests/unit/test_codex_adapter.py.
4. Run full verification before opening a PR:
   - python -m pytest tests/unit/ -v --tb=short
   - python scripts/lint_frontmatter.py
   - cd dashboard && npm test && npm run build
5. Summarize exact pass/fail counts, token/cost totals (if live), and modified files in the PR description.
```

---

## 4. Copy-Paste Prompt for Devin / Neon Sessions

Use this prompt in a **Devin / Neon** session on `ZenzerJs/Ai-Lab` to extend the `gemini-4-neon-devin` and `claude-fable-5-2-devin` cohorts to `icm_v3` and `icm_staged`:

```text
Work in ZenzerJs/Ai-Lab on a new branch from origin/main.

Goal: Run the first Devin/Neon icm_v3 and icm_staged benchmark batch across our multi-file suites so we can compare them directly against existing baseline, icm (v1), and icm_v2 runs in the Pareto frontier.

Instructions:
1. Hydrate the local ledger from the committed snapshot first:
   python scripts/hydrate_db.py --from-snapshot dashboard/public/data.json --db data/usage.db --force
2. Run a matched campaign on tasks:
   BENCH-014,BENCH-017,BENCH-018,BENCH-021,BENCH-024,BENCH-027,BENCH-030,BENCH-034
   across arms `icm_v3,icm_staged` with `--repetitions 2` on `gemini-4-neon-devin` (or `claude-fable-5-2-devin`).
   Use `scripts/campaign.py plan-batch` + `execute-batch` (or your native runner adapter writing verified NDJSON logs to `experiments/evidence/` with `contract_version`, `contract_hash`, `llm_calls_count`, `cache_bust_count`, `tools_per_llm_call`, and `context_reset` telemetry for `icm_staged`).
3. Ensure every run is recorded into `data/usage.db` with `source_kind="live"` and `evidence_status="verified"` (keep `cost_usd=None` if no real provider token billing applies, and record `acus_consumed` as metadata if available — never invent dollar estimates).
4. Re-export `dashboard/public/data.json` using:
   python dashboard/build_data.py dashboard/public/data.json
5. Verify everything passes:
   - python -m pytest tests/unit/ tests/browser/test_dashboard_production.py::TestSnapshotIntegrity tests/browser/test_dashboard_production.py::TestPagesWorkflowRegression -v --tb=short
   - python scripts/lint_frontmatter.py
   - cd dashboard && npm test && npm run build
6. Open a PR and note that it needs the `data-publish` label because `dashboard/public/data.json` is updated.
```
