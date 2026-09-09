# Task Execution Management (ICM Pipeline)

This directory houses task contracts adhering to the **Interpretable Context Methodology (ICM)**.

---

## 1. Initializing a New Task

To instantiate a new structured task, copy the template directory to a new `TSK-XXX` identifier:

### PowerShell (Windows)
```powershell
Copy-Item -Recurse -Path "tasks\_template" -Destination "tasks\TSK-001"
```

### POSIX Shell (macOS / Linux)
```bash
cp -r tasks/_template tasks/TSK-001
```

---

## 2. The 5-Stage Contract Lifecycle

Each task progresses through 5 sequential contracts:
1. `01_intake.md`: Define scope, non-goals, and the per-stage token budget (<= 8,000 tokens active context).
2. `02_plan.md`: Formulate technical architecture and establish the OKR Acceptance Matrix with machine-verifiable exit commands.
3. `03_exec.md`: Execute changes using diff-only editing protocol; record symbol mutations and overwrite justifications.
4. `04_verify.md`: Run automated tests through `scripts/filter_output.py` and log token telemetry.
5. `05_retro.md`: Conduct retrospective, propagate architectural updates into `docs/`, and append to `docs/log.md`.

---

## 3. Session Resume Invariant
Agents entering this repository inspect this directory to find the latest active `TSK-XXX` and resume strictly from its current stage contract without assuming conversational memory.
