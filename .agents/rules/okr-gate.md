# Operational Rule: OKR Stage Gate (Plan-to-Execution Transition)

## Core Mandate
Transitioning a task from Stage 2 (`02_plan.md`) to Stage 3 (`03_exec.md`) strictly requires an approved OKR Acceptance Matrix populated with deterministic, machine-verifiable exit criteria.

## Requirements for Stage 2 Sign-Off
1. **Clear Objectives:** High-level architectural target of the task.
2. **Key Results (Measurable):**
   - Specific assertions, test cases, or contract invariants.
   - Ambiguous phrases such as "works properly" or "clean code" are invalid.
3. **Automated Verification Commands:**
   - Every Key Result MUST have a corresponding automated verification command executable via `scripts/filter_output.py`.
   - Example: `python scripts/filter_output.py -- pytest tests/test_parser.py -k test_symbol_extraction`
4. **Impacted Files Manifest:**
   - Explicit enumerations of every file expected to be created, modified, or deleted.
5. **Stage Gate Enforcement:**
   - No code modification may begin in `03_exec.md` until the OKR table in `02_plan.md` has been reviewed, signed off, and validated.
