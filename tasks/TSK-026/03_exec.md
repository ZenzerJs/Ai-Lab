# Task Stage Contract: 03_exec

## Task Metadata
- **Task ID:** TSK-026
- **Title:** Large-Scale Multi-File Benchmark Suite (`EXP-009`..`EXP-011`) & Blind Judge Protocol
- **Status:** COMPLETE
- **Owner:** Systems Engineering & Research Agent
- **Subagent ID:** `dbb5ec97-f340-4ad2-a724-1fc76a40c73d` (`flash` ICM Stage 03 Executor)

---

## 1. Symbol Modification Ledger

| File | Symbol / Region | Action | Justification |
|---|---|---|---|
| `experiments/tasks/EXP-009.md` | Task Contract | Created | 7-file, ~1,400 LOC Event-Driven Job Queue & Observability UI spec |
| `experiments/tasks/EXP-010.md` | Task Contract | Created | 8-file, ~1,500 LOC Markdown Knowledge Graph & BM25 Search Engine spec |
| `experiments/tasks/EXP-011.md` | Task Contract | Created | 6-file, ~1,350 LOC Policy-Enforced API Gateway & Billing Engine spec |
| `scripts/scaffold_outlines.py` | `scaffold_task_outline` | Created | Deterministic multi-file starter outline generator for `EXP-009`..`EXP-011` |
| `scripts/campaign.py` | `prepare_blind_ab_packet`, `compute_quality_ci` | Added functions | Blind pairwise A/B diff sanitizer + 95% bootstrap CI per rubric dimension |
| `dashboard/src/lib/workspace.ts` | `experimentNames` | Edited map | Registered `EXP-009`, `EXP-010`, and `EXP-011` labels |
| `tests/unit/test_quality_rubric.py` | `test_scaffold_outlines`, `test_prepare_blind_ab_packet`, `test_compute_quality_ci` | Added unit tests | Automated verification of outlines, blinding, and CIs |

---

## 2. Search / Replace Change Log

```
<<<<<<< SEARCH
  "EXP-008": "Interview intelligence",
};
=======
  "EXP-008": "Interview intelligence",
  "EXP-009": "Event-driven job queue",
  "EXP-010": "Knowledge graph & BM25",
  "EXP-011": "Policy API gateway",
};
>>>>>>> REPLACE
```

*(Full `prepare_blind_ab_packet` and `compute_quality_ci` additions in `scripts/campaign.py` lines 1021–1136.)*

---

## 3. Escape-Hatch Justifications
- None. All edits to existing files used Search/Replace blocks.
