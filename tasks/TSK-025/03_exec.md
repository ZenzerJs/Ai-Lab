# Task Stage Contract: 03_exec

## Task Metadata
- **Task ID:** TSK-025
- **Title:** Multi-Dimensional Benchmark Scoring Rubric (Quality, Design, Engineering, Process)
- **Status:** COMPLETE
- **Owner:** Systems Engineering & Research Agent
- **Subagent ID:** `dbb5ec97-f340-4ad2-a724-1fc76a40c73d` (`flash` ICM Stage 03 Executor)

---

## 1. Symbol Modification Ledger

| File | Symbol / Region | Action | Justification |
|---|---|---|---|
| `scripts/campaign.py` | `CampaignSlot.quality_scores` | Added optional field | Stores 5-dimension rubric dict on slot |
| `scripts/campaign.py` | `CampaignSlot.to_ledger_run` | Updated serialization | Persists `quality_scores` inside `runs.notes` JSON column (`ponytail`: zero schema migration) |
| `scripts/campaign.py` | `_run_to_slot` | Updated deserialization | Restores `quality_scores` from `runs.notes` JSON |
| `scripts/campaign.py` | `score_workspace` | Added function | Deterministic 0–5 scorer across Correctness, Engineering, Maintainability, Process, and Design |
| `tests/unit/test_quality_rubric.py` | `test_*` (8 tests) | Created file | Unit coverage for backend 20-pt, UI 25-pt, AST LOC tiers, scope penalties, and ledger round-trip |

---

## 2. Search / Replace Change Log (`scripts/campaign.py`)

```
<<<<<<< SEARCH
    evidence_hash: Optional[str] = None
    error_message: Optional[str] = None
    notes: Optional[str] = None
=======
    evidence_hash: Optional[str] = None
    error_message: Optional[str] = None
    notes: Optional[str] = None
    quality_scores: Optional[Dict[str, Any]] = None
>>>>>>> REPLACE
```

```
<<<<<<< SEARCH
        if self.notes:
            notes_dict["user_notes"] = self.notes

        return {
=======
        if self.notes:
            notes_dict["user_notes"] = self.notes
        if self.quality_scores is not None:
            notes_dict["quality_scores"] = self.quality_scores

        return {
>>>>>>> REPLACE
```

*(Full `score_workspace` implementation added at line 883 of `scripts/campaign.py`.)*

---

## 3. Escape-Hatch Justifications
- None. All edits used Search/Replace blocks; `tests/unit/test_quality_rubric.py` is a newly created test file.
