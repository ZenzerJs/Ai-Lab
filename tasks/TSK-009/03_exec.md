# Task Stage Contract: 03_exec

## Task Metadata
- **Task ID:** TSK-009
- **Title:** GitHub Pages Dashboard — Real Data, Few Impactful Statistics
- **Status:** COMPLETE
- **Prerequisite:** `02_plan.md` OKR Gate approved
- **Execution Date:** 2026-10-03

---

## 1. Execution Summary
1. **Transcript Audit & Provenance Verification:**
   - Dispatched subagent `cc04ff17-36dd-45cd-b632-69b7e4b718b1` to audit all 31 candidate transcripts in `~/.gemini/antigravity/brain/`.
   - Confirmed past `data/usage.db` rows originated from fixture replays of `mock_stream.ndjson`.
   - Strictly enforced the Honesty Invariant: fabricated/fixture metrics are barred from live dashboard statistics.

2. **Live Telemetry & Harness Integration:**
   - Verified Antigravity CLI (`agy` v1.2.16) support for `--output-format stream-json` at `C:\Users\jayde\AppData\Local\agy\bin\agy.exe`.
   - Updated `scripts/run_experiment.py` with binary subprocess pipe handling for byte-exact SHA-256 evidence hashing.
   - Updated `scripts/ledger.py` with native `result` telemetry parsing and corrected bounded cache hit ratio formula `cache / (input + cache)`.
   - Updated `config/PRICING.json` and seeded pricing in `data/usage_live.db` for `gemini-3.8-flash-low` and `gemini-3.8-flash-medium`.
   - Executed live trial of `EXP-001` (baseline vs. ICM) into `data/usage_live.db` with verified `evidence_status="verified"` and `source_kind="live"`.

3. **Backend Export Engine Enhancements (`dashboard/build_data.py`):**
   - Implemented `build_headline_block` computing verified primary metrics with 95% bootstrap confidence intervals.
   - Preserved genuine operational tradeoffs (e.g. planning duration / turns overhead).
   - Exported live payload to `dashboard/public/data.json` (`has_data: true`, `is_demo_report: false`).

4. **Single-Page Dashboard Architecture Overhaul:**
   - Designed and built modern, high-impact single-page layout:
     - `dashboard/src/components/HeroStats.tsx`: 3 impactful headline metric cards with 95% CI and source provenance.
     - `dashboard/src/components/TradeoffCallout.tsx`: Transparent operational tradeoff disclosure (duration & turns overhead).
     - `dashboard/src/components/TaskComparison.tsx`: Direct cost comparison bar visualization.
     - `dashboard/src/components/TaskTable.tsx`: Side-by-side telemetry table with verification badges.
     - `dashboard/src/components/MethodologyDrawer.tsx`: Expandable drawer with rate card simulator and SQLite audit ledger.
   - Streamlined `dashboard/src/components/Header.tsx` and `dashboard/src/App.tsx`.
   - Removed obsolete components (`ExecutiveShowcase`, `CumulativeSavings`, `ScaleSelector`, `RollingCounter`, `ExperimentCards`, `CacheHitRatio`, `TurnsDuration`, `OperationalBenchmarkCard`, `PerTaskComparison`, `useAnimatedCounter`).

5. **Cross-Platform Test Harness Fixes:**
   - Added `stdin=subprocess.DEVNULL` to `scripts/runner.py`, `benchmarks/BENCH-006/evaluator/evaluator.py`, `tests/unit/test_benchmarks.py`, and `tests/unit/test_hardening_phase3_4.py` resolving Windows OS handle inheritance (`[WinError 6]`).
   - Verified 126/126 unit & integration tests pass with 100% success rate.

---

## 2. Modified Files Manifest

| File | Status | Description |
|---|---|---|
| `scripts/run_experiment.py` | Modified | Binary streaming for byte-exact SHA-256 hash calculation and `agy` CLI flags. |
| `scripts/ledger.py` | Modified | Bounded cache hit ratio calculation and native `result` usage event parser. |
| `scripts/runner.py` | Modified | Added `stdin=subprocess.DEVNULL` for Windows subprocess compatibility. |
| `config/PRICING.json` | Modified | Added pricing entries for `gemini-3.8-flash-low` and `gemini-3.8-flash-medium`. |
| `dashboard/build_data.py` | Modified | Added headline statistics generation and bootstrap CI calculation. |
| `dashboard/src/App.tsx` | Modified | Consolidated multi-tab interface into clean, high-impact single page. |
| `dashboard/src/types.ts` | Modified | Added `ScaleMode` type and headline schema types. |
| `dashboard/src/components/Header.tsx` | Modified | Simplified header without redundant tablist. |
| `dashboard/src/components/HeroStats.tsx` | Created | Top-level 3-card headline metric display. |
| `dashboard/src/components/TradeoffCallout.tsx` | Created | Transparent operational tradeoff callout banner. |
| `dashboard/src/components/TaskComparison.tsx` | Created | Clean cost comparison visualizer. |
| `dashboard/src/components/TaskTable.tsx` | Created | Detailed task-level telemetry breakdown table. |
| `dashboard/src/components/MethodologyDrawer.tsx` | Created | Collapsible drawer containing audit ledger & rate simulator. |
| `benchmarks/BENCH-006/evaluator/evaluator.py` | Modified | Added `stdin=subprocess.DEVNULL` for Windows pytest runs. |
| `tests/unit/test_benchmarks.py` | Modified | Added `stdin=subprocess.DEVNULL` for subprocess calls. |
| `tests/unit/test_hardening_phase3_4.py` | Modified | Added `stdin=subprocess.DEVNULL` for subprocess calls. |
