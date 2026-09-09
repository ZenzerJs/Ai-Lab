# Operational Rule: Tool Discipline & Stage-Bound Tool Gating

## Core Mandate
Agent tooling access is strictly compartmentalized across the task lifecycle stages. Using tools outside their authorized stage contracts is a protocol violation.

## Stage-Bound Tool Restrictions
1. **Stage `01_intake`:**
   - **Allowed:** Read-only exploration, `ast-grep`, `repo_map.py`, requirement analysis.
   - **BARRED:** Git modification tools (`git_commit`, `git_reset`, staging), write operations on source files.
2. **Stage `02_plan`:**
   - **Allowed:** Sequential thinking (max 10 reasoning steps), architectural analysis, dependency review, OKR matrix formulation.
   - **BARRED:** Git modification tools, destructive file system writes.
3. **Stage `03_exec`:**
   - **Allowed:** Diff-only editing (`replace_file_content`), surgical creation of new modules, local linting.
   - **BARRED:** Sequential-thinking tools (reasoning must occur during `02_plan`, not mid-implementation).
4. **Stage `04_verify`:**
   - **Allowed:** Automated test execution via `filter_output.py`, linter assertions, regression validation.
   - **BARRED:** Sequential-thinking tools, exploratory refactoring outside the plan.
5. **Stage `05_retro`:**
   - **Allowed:** Knowledge graph documentation updates (`docs/`), appending entries to `docs/log.md`, metric recording.
   - **BARRED:** Unplanned source modifications.
