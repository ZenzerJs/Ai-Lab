---
type: concept
title: Controlled Campaign Live Smoke Procedure
description: Standard operating procedure and authorization requirements for executing live model smoke campaigns.
status: active
verified: human-reviewed
sources:
  - /concepts/measurement-layer.md
---

# Controlled Campaign Live Smoke Procedure

This document specifies the operational procedure, safety boundaries, pre-flight checklist, and emergency stop protocol for conducting an authorized live model smoke campaign.

> [!WARNING]
> **Safety Boundary**: Automated tests and development workflows must NEVER execute live model calls. Live campaigns require explicit per-campaign user authorization using the template below.

---

## 1. Authorization Protocol

Before any live model execution, the operator must obtain signed user authorization containing all required constraints.

### Required Authorization Template

```text
I approve only this live smoke campaign:
- Task ID/version: [e.g. BENCH-001, version 1.0.0]
- Arms: [e.g. baseline, icm]
- Attempts per arm: [e.g. 1]
- Model/provider and available version/settings: [e.g. gemini-2.5-pro, temp=0.0]
- Execution mode: manual/automated
- Maximum total budget and currency: [e.g. $1.00 USD]
- Maximum runtime per attempt: [e.g. 300 seconds]
- Budget enforcement capability and limitations: [Planner records resource_budget; hard stops enforced via external execution wrapper / stop conditions]
- Allowed telemetry capture and storage: [Local SQLite tmp_db only]
- Human assistance policy: [Zero human intervention during execution]
- Retry policy: [No retries on failure; record failure as-is]
- Stop conditions: [Timeout, unexpected error, budget ceiling, token limit]
```

---

## 2. Pre-Flight Verification Checklist

Before initiating execution:
1. **Pristine Production Database**: Verify that `data/usage.db` is backed up and NOT targeted. The campaign must target an isolated temporary database (e.g. `--db tmp_campaign.db`).
2. **Offline Tests Green**: Verify all hermetic tests pass:
   ```bash
   uv run --isolated --python 3.12 --with pytest pytest
   ```
3. **Plan Manifest Predeclaration**: Generate and inspect the immutable campaign plan:
   ```bash
   python scripts/campaign.py plan --tasks BENCH-001 --arms baseline,icm --repetitions 1 --seed 42 --output live_plan.json
   ```
   Confirm slot count, randomized order, and resource budgets in `live_plan.json`.
4. **Environment Isolation**: Ensure no live API keys or credentials are leaked into untrusted workspaces (`sanitize_subprocess_env`).

---

## 3. Step-by-Step Execution Sequence

1. **Step 1: Manifest Inspection**
   Inspect the scheduled slots and verify integrity hash:
   ```bash
   python -c "import scripts.campaign as c, pathlib as p; m = c.CampaignManifest.load(p.Path('live_plan.json')); print('Valid:', m.verify_integrity(), 'Slots:', len(m.slots))"
   ```

2. **Step 2: Controlled Live Execution**
   Execute only the approved attempts with hard timeout and budget caps.
   If using manual execution adapter:
   - Prepare disposable workspace for each arm:
     ```python
     ws_base, ws_icm = runner.WorkspaceManager.prepare_two_arms(...)
     ```
   - Run evaluated prompt session.
   - Record run outcome, tokens, and evidence immediately into temporary ledger.

3. **Step 3: Verification & Grading**
   Run the protected evaluator outside the agent workspace:
   ```python
   evaluator = runner.ProtectedEvaluator(evaluator_path)
   res = evaluator.evaluate_workspace(workspace_path)
   ```

4. **Step 4: Campaign Report Generation**
   Generate the campaign report and inspect coverage, success rates, and paired differences:
   ```bash
   python scripts/campaign.py report --manifest live_plan.json --db tmp_campaign.db --output live_report.json
   ```

5. **Step 5: Teardown & Archival**
   - Clean up disposable workspaces (`ws.cleanup()`).
   - Retain raw evidence artifacts and checksums.
   - Present report to user without modifying `data/usage.db`.

---

## 4. Emergency Stop Conditions

Execution must abort immediately if:
- Cumulative observed cost reaches 90% of the approved budget cap.
- Any attempt exceeds its allocated `timeout_seconds`.
- Network calls to unauthorized hosts or endpoints are detected.
- Evaluator SHA-256 hash does not match expected reference hash.
