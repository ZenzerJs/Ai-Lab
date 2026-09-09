# Task Stage Contract: 03_exec

## Task Metadata
- **Task ID:** TSK-XXX
- **Title:** [Task Name]
- **Status:** ACTIVE | COMPLETE
- **Prerequisite:** `02_plan.md` OKR Gate signed off

---

## 1. Execution Summary
[Summary of executed code modifications, refactors, and test preparations.]

---

## 2. Search/Replace Change Tracking Ledger
*Per `.agents/rules/diff-only-editing.md`, changes to files >50 lines must record search/replace blocks.*

### Target File: `path/to/file.py`
```text
<<<<<<< SEARCH
# Existing code block with 2-3 lines of matching context
=======
# Modified code block
>>>>>>> REPLACE
```

---

## 3. Symbol Modification Ledger
*Tracks all newly introduced, modified, or deprecated classes, interfaces, and function signatures.*

| Symbol Name | Symbol Type (`Class` / `Function` / `Interface`) | File Path | Modification Summary |
|---|---|---|---|
| `FunctionName` | `Function` | `src/module.py` | Added parameter `x: int` with return type annotation |
| `ClassName` | `Class` | `src/service.py` | Implemented new domain interface |

---

## 4. Escape-Hatch Justification Log
*Full-file overwrites on existing files require an explicit rationale logged below prior to execution.*

| Target File Path | File Size (lines) | Overwrite Rationale (`Net-New` / `Generated Config` / `Documented Refactor`) | Architect Approval |
|---|---|---|---|
| `src/...` | N/A | Net-new file creation | APPROVED |

---

## 5. Exit Criteria & Transition Checklist
- [ ] All planned code changes executed according to diff-only protocol.
- [ ] No syntax errors or unfinished placeholders remain.
- [ ] Symbol modification ledger updated.
- [ ] Ready for automated verification in `04_verify.md`.
