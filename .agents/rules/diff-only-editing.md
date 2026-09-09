# Operational Rule: Diff-Only Editing Protocol

## Core Mandate
All modifications to existing files exceeding 50 lines MUST use targeted Search/Replace diff blocks (`<<<<<<< SEARCH`, `=======`, `>>>>>>> REPLACE`) or surgical line-range replacements. Complete file overwrites on existing long files are strictly prohibited.

## Enforcement Rules
1. **Search/Replace Formatting:**
   ```
   <<<<<<< SEARCH
   exact lines of original code to replace
   =======
   new replacement code lines
   >>>>>>> REPLACE
   ```
2. **Context Padding:**
   - Include 2–3 lines of unique leading and trailing context in the search block to ensure unambiguous matching.
   - Do not replace entire classes or functions when only modifying internal logic.
3. **Exceptions for Full-File Overwrites:**
   Full file overwrites are permissible ONLY in the following three cases:
   - **(a) Net-New Files:** Creating a file that did not previously exist.
   - **(b) Generated Machine Configs:** Compiling lockfiles, small config artifacts, or generated metadata bundles.
   - **(c) Explicit Rationale:** When structural file reorganization renders diffs larger than the file itself, and an explicit justification is recorded in the task's `03_exec.md` ledger prior to execution.
4. **Safety Verification:**
   After applying diffs, agents must run linter assertions and test suites via `scripts/filter_output.py` to confirm structural and syntactical integrity.
