# Phase 4 Live Smoke Procedure

This document provides the operational guide and authorization protocol for conducting an authorized live model smoke campaign, as specified in `Addon/01-IMPLEMENTATION-ROADMAP.md` and `Addon/04-ANTIGRAVITY-HANDOFF.md`.

> [!CAUTION]
> **Zero Live Model Calls in Automated Testing**:
> Phase 4 development and all automated test suites operate purely on hermetic fixtures, mocks, and simulated matrices.
> Do NOT execute live model calls without explicit per-campaign user authorization.

---

## 1. Required User Authorization Template

Before any live model execution, fill and obtain approval for this template:

```text
I approve only this live smoke campaign:
- Task ID/version: [e.g. BENCH-01, version 1.0.0]
- Arms: [e.g. baseline, icm]
- Attempts per arm: [e.g. 1]
- Model/provider and available version/settings: [e.g. gemini-2.5-pro, temperature=0.0, top_p=1.0]
- Execution mode: manual/automated
- Maximum total budget and currency: [e.g. $1.00 USD]
- Maximum runtime per attempt: [e.g. 300 seconds]
- Budget enforcement capability and limitations: [Hard stop at $1.00 via process monitor]
- Allowed telemetry capture and storage: [Local SQLite tmp_db only]
- Human assistance policy: [Zero human intervention during execution]
- Retry policy: [No retries on failure; record failure as-is]
- Stop conditions: [Timeout, unexpected error, budget ceiling, token limit]
```

---

## 2. Pre-Flight Verification Checklist

1. **Protect Production Database**: Confirm `data/usage.db` is NOT specified as the output database. Use a disposable SQLite database (e.g. `--db tmp_live_smoke.db`).
2. **Hermetic Regression Green**: Verify all existing tests pass:
   ```bash
   uv run --isolated --python 3.12 --with pytest pytest
   ```
3. **Plan Manifest Predeclaration**: Generate the campaign manifest ahead of time with a fixed random seed:
   ```bash
   python scripts/campaign.py plan --tasks BENCH-01 --arms baseline,icm --repetitions 1 --seed 42 --output live_manifest.json
   ```
   Inspect the manifest to confirm scheduled attempts, randomized arm order, and resource budgets.
4. **Environment Sanitization**: Use `runner.sanitize_subprocess_env` to avoid credential leakage.

---

## 3. Execution & Verification Flow

1. **Matrix Inspection**:
   Inspect slots, planned order, and SHA-256 manifest hash:
   ```bash
   python -c "import scripts.campaign as c, pathlib as p; m = c.CampaignManifest.load(p.Path('live_manifest.json')); print('Manifest valid:', m.verify_integrity(), 'Slots:', len(m.slots))"
   ```

2. **Run Execution**:
   Execute the scheduled slots in the predeclared order. Capture raw telemetry streams and token usage into the isolated database.

3. **Protected Grading**:
   Grade the workspace outputs using `runner.ProtectedEvaluator` located outside the workspace:
   ```python
   evaluator = runner.ProtectedEvaluator(Path("benchmarks/bench_01/evaluator.py"))
   result = evaluator.evaluate_workspace(ws.path)
   ```

4. **Campaign Report Generation**:
   Generate the final campaign report:
   ```bash
   python scripts/campaign.py report --manifest live_manifest.json --db tmp_live_smoke.db --output live_report.json
   ```
   Review execution coverage, verified success rates, per-arm sample counts, and paired cost differences.

5. **Stop Conditions**:
   Immediately abort execution if:
   - Cumulative cost exceeds $1.00 USD.
   - Any attempt exceeds 300 seconds.
   - Any evaluator hash mismatch is detected.
