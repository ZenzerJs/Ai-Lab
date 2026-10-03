# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-010
- **Title:** Pure-Python Slugify Utility Module
- **Status:** APPROVED
- **Prerequisite:** `01_intake.md` exit criteria satisfied

---

## 1. Technical Approach & Architecture
We will provide a clean, standalone, zero-dependency `slugify` implementation in `src/slugify.py` adhering to the following design:
- Interface: `slugify(value: str, allow_unicode: bool = False, separator: str = "-") -> str`
- Type Hints: Fully annotated inputs and return type using Python 3 typing conventions.
- Unicode handling:
  - If `allow_unicode=False`: Perform `unicodedata.normalize('NFKD', value)`, strip diacritical marks via `.encode('ascii', 'ignore').decode('ascii')`, lowercase, and remove characters matching `[^a-z0-9\s-]`.
  - If `allow_unicode=True`: Perform `unicodedata.normalize('NFKC', value)`, lowercase, and remove characters matching `[^\w\s-]`.
- Separators & Whitespace:
  - Consolidate consecutive whitespaces and separators into a single configured `separator`.
  - Strip leading/trailing occurrences of `separator`.
- Non-string inputs: Coerce to `str` safely before processing.

### Cognitive Reasoning Trace (Sequential Thinking)
1. **Step 1 (Decomposition):** Separate string sanitization into normalization (NFKD/NFKC), casing/filtering, delimiter condensation, and trimming.
2. **Step 2 (Regex & Escaping):** Ensure configurable `separator` is safely escaped when interpolated into regular expressions to avoid delimiter injection errors.
3. **Step 3 (Edge Cases):** Handle empty string `""`, whitespace-only strings `"   "`, special character strings, numeric types, and multi-lingual characters.
4. **Step 4 (Test Structure):** Provide `unittest.TestCase` in `src/test_slugify.py` testing each dimension of behavior, compatible with both direct execution and package runner.

---

## 2. Impacted Files Manifest

| Target File Path | Action (`CREATE` / `MODIFY` / `DELETE`) | Description & Rationale | Diff Block Required (>50 lines) |
|---|---|---|---|
| `src/slugify.py` | `CREATE` | Net-new standalone slugify implementation (< 50 lines) | No (new file) |
| `src/test_slugify.py` | `CREATE` | Comprehensive unit test suite (< 50 lines) | No (new file) |
| `tasks/TSK-010/03_exec.md` | `CREATE` | Stage 3 execution tracking contract | No (new file) |
| `tasks/TSK-010/04_verify.md` | `CREATE` | Stage 4 verification report | No (new file) |

---

## 3. OKR Acceptance Matrix (Machine-Verifiable Exit Criteria)

**Objective:** Implement and verify a robust, standalone pure-Python slugify utility module with zero external dependencies.

| Key Result (KR) | Deterministic Success Metric | Automated Verification Command (via `filter_output.py`) | Status |
|---|---|---|---|
| **KR 1** | Standalone module imports cleanly with no syntax/import errors | `python scripts/filter_output.py -- python -c "from src.slugify import slugify; assert callable(slugify)"` | APPROVED |
| **KR 2** | Full unit test suite passes with 100% success and exit code 0 | `python scripts/filter_output.py -- python -m unittest src/test_slugify.py` | APPROVED |
| **KR 3** | Pytest execution succeeds cleanly across the workspace test runner | `python scripts/filter_output.py -- python -m pytest src/test_slugify.py` | APPROVED |

---

## 4. Stage Gate Transition Check
Per `.agents/rules/okr-gate.md`, implementation in `03_exec.md` must not commence until:
- [x] Technical architecture reviewed and validated.
- [x] Impacted files manifest completely populated.
- [x] OKR Acceptance Matrix defined with automated verification commands.
- [x] Sign-off approved to transition to `03_exec.md`.
