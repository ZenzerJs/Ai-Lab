# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-026
- **Title:** Large-Scale Multi-File Benchmark Suite (`EXP-009`..`EXP-011`) & Blind Judge Protocol
- **Status:** APPROVED
- **Owner:** Systems Engineering & Research Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Technical Architecture & Impacted Files Manifest

1. **Large-Scale Benchmark Prompts (`experiments/tasks/`):**
   - `experiments/tasks/EXP-009.md`: **Multi-Tenant Event-Driven Job Queue & Observability UI** (~1,400 LOC target across 7 files: `queue_engine/schema.py`, `queue_engine/storage.py`, `queue_engine/dag.py`, `queue_engine/worker.py`, `queue_engine/retry.py`, `queue_engine/ui.html`, `tests/test_exp009.py`).
   - `experiments/tasks/EXP-010.md`: **Local-First Markdown Knowledge Graph & BM25 Search Engine** (~1,500 LOC target across 8 files: `kg_engine/parser.py`, `kg_engine/graph.py`, `kg_engine/bm25.py`, `kg_engine/indexer.py`, `kg_engine/cli.py`, `kg_engine/exporter.py`, `kg_engine/viewer.html`, `tests/test_exp010.py`).
   - `experiments/tasks/EXP-011.md`: **Policy-Enforced API Gateway & Rate-Limit Billing Engine** (~1,350 LOC target across 6 files: `gateway/limiter.py`, `gateway/webhook.py`, `gateway/billing.py`, `gateway/router.py`, `gateway/console.html`, `tests/test_exp011.py`).
2. **Deterministic Starter Repo Scaffolder (`scripts/scaffold_outlines.py`):**
   - `scaffold_task_outline(task_id: str, dest_dir: Path) -> List[Path]`: Materializes the multi-file starter outline (with planted concurrency/logic bugs and incomplete modules) into `dest_dir` so both Baseline and Governed arms start from the exact same SHA-verified repo state.
3. **Blind Pairwise A/B Judge Packet & Quality CI (`scripts/campaign.py`):**
   - `prepare_blind_ab_packet(campaign_id: str, task_id: str, baseline_diff: str, governed_diff: str, seed: int = 42) -> Dict[str, Any]`: Strips ICM stage contract paths (`tasks/TSK-*`) and arm identifiers from diffs, deterministically randomizes `Arm_Alpha` / `Arm_Beta` order, and returns `{ "blind_packet": { "Arm_Alpha": ..., "Arm_Beta": ..., "rubric": ... }, "sealed_key": { "Arm_Alpha": ..., "Arm_Beta": ... } }`.
   - `compute_quality_ci(paired_scores: List[Tuple[Dict[str, Any], Dict[str, Any]]], seed: int = 42) -> Dict[str, Any]`: Computes mean paired difference and 95% bootstrap CI per dimension (`correctness`, `engineering`, `maintainability`, `process`, `design`, `normalized_pct`).
4. **Dashboard Task Registry (`dashboard/src/lib/workspace.ts`):**
   - Add `EXP-009`, `EXP-010`, `EXP-011` titles to `experimentNames`.
5. **Unit Tests (`tests/unit/test_quality_rubric.py`):**
   - Add unit tests verifying `EXP-009`..`EXP-011` outline scaffolding, `prepare_blind_ab_packet` blinding/randomization, and `compute_quality_ci` bootstrap intervals.

---

## 2. OKR Acceptance Matrix

| Objective | Key Result | Machine-Verifiable Exit Command | Expected Value | Status |
|---|---|---|---|---|
| **O1: Task Specs & Outlines** | KR1.1: `EXP-009`..`EXP-011` specs exist and `scaffold_task_outline` materializes 6–8 files per task | `python scripts/filter_output.py -- python -m pytest tests/unit/test_quality_rubric.py -k test_scaffold_outlines -q -p no:cacheprovider` | `exit=0` | COMPLETE |
| **O2: Blind Judge & Quality CI** | KR2.1: `prepare_blind_ab_packet` strips ICM artifacts and `compute_quality_ci` computes 95% CIs | `python scripts/filter_output.py -- python -m pytest tests/unit/test_quality_rubric.py -q -p no:cacheprovider` | `exit=0` | COMPLETE |
| **O3: Docs & Build Integrity** | KR3.1: OKF frontmatter linter passes | `python scripts/filter_output.py -- python scripts/lint_frontmatter.py` | `exit=0` | COMPLETE |
