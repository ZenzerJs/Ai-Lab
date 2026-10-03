# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-012
- **Title:** AST Dead Code Finder Module
- **Status:** APPROVED
- **Prerequisite:** `01_intake.md` exit criteria satisfied

---

## 1. Technical Approach & Architecture

We will implement an AST visitor in `src/dead_code_finder.py` to identify:
1. **Unused Private Functions**: Functions/methods beginning with `_` (excluding double-underscore dunders like `__init__`) defined but never referenced (via `ast.Name` or `ast.Attribute`).
2. **Unreachable Code Blocks**: Statements appearing directly after `return` or `raise` in any statement sequence block (functions, conditionals, loops, try blocks).

### Data Structures & Public Interface
- `class FindingType(enum.Enum)`:
  - `UNUSED_PRIVATE_FUNCTION = "unused_private_function"`
  - `UNREACHABLE_CODE = "unreachable_code"`
- `@dataclass(frozen=True) class DeadCodeFinding`:
  - `finding_type: FindingType`
  - `name: str`
  - `lineno: int`
  - `col_offset: int`
  - `message: str`
- `class DeadCodeFinder(ast.NodeVisitor)`:
  - Traverses AST, collects private function definitions and name/attribute usages.
  - Checks block statement sequences for terminal statements (`ast.Return`, `ast.Raise`) and flags unreachable trailing statements.
  - Exposes `find_dead_code(source: str, filename: Optional[str] = None) -> List[DeadCodeFinding]`.
  - Exposes `find_dead_code_from_file(filepath: Union[str, Path]) -> List[DeadCodeFinding]`.

### Cognitive Reasoning Trace (Sequential Thinking)
1. **Step 1 (Decomposition):** Separate dead code analysis into two independent concerns:
   - Control-flow reachability: Sequential block walk checking for statements after `Return` or `Raise`.
   - Symbol usage analysis: Two-pass or visitor-based collection of defined private functions and referenced identifiers (both `ast.Name` loads and `ast.Attribute` access).
2. **Step 2 (Scope & Dunders):** Dunder methods (`__...__`) must be excluded from private function analysis. Names referenced anywhere in the module (including decorator references, callbacks, or class method calls via attributes) mark the private function as used.
3. **Step 3 (Unreachable Blocks):** Examine all AST statement lists: `Module.body`, `FunctionDef.body`, `AsyncFunctionDef.body`, `If.body`, `If.orelse`, `While.body`, `While.orelse`, `For.body`, `For.orelse`, `Try.body`, `Try.handlers`, `Try.orelse`, `Try.finalbody`, `With.body`, etc. Flag every statement that follows a terminal statement in the same body.
4. **Step 4 (Test Fixtures):** In `src/test_dead_code_finder.py`, define string fixtures and file-based test cases covering:
   - Unused module-level private functions.
   - Used private functions (direct call, passed as reference).
   - Unused private class methods.
   - Used private class methods (called via `self._method()`).
   - Dunder methods ignored.
   - Unreachable statements after `return` in function body.
   - Unreachable statements after `raise` in function body and conditionals.
   - Complex nested blocks (if/else, try/except/finally).
   - Completely clean code with zero false positives.

---

## 2. Impacted Files Manifest

| Target File Path | Action (`CREATE` / `MODIFY` / `DELETE`) | Description & Rationale | Diff Block Required (>50 lines) |
|---|---|---|---|
| `src/dead_code_finder.py` | `CREATE` | AST visitor and dead code detector | No (Initial Creation) |
| `src/test_dead_code_finder.py` | `CREATE` | Test fixtures and test suite for dead code detection | No (Initial Creation) |
| `tasks/TSK-012/03_exec.md` | `CREATE` | Execution tracking ledger | No (Stage Contract) |
| `tasks/TSK-012/04_verify.md` | `CREATE` | Test verification results | No (Stage Contract) |

---

## 3. OKR Acceptance Matrix

| Objective ID | Key Result (KR) Description | Target Metric / Exit Criteria | Verification Method |
|---|---|---|---|
| **OKR-1** | Detect unused private functions | 100% detection of uncalled `_func` without false positives on dunders or public functions | `unittest` / `pytest` test suite |
| **OKR-2** | Detect unreachable code blocks | 100% detection of statements following `return` or `raise` in blocks | `unittest` / `pytest` test suite |
| **OKR-3** | Zero regressions & Clean Code | 0 findings on clean code fixtures | `unittest` / `pytest` test suite |
| **OKR-4** | Log Sanitation & Standards | Standard library only; filtered command execution exit code 0 | `python scripts/filter_output.py` |

---

## 4. Exit Criteria & Transition Checklist
- [x] Technical design reviewed and verified against user requirements.
- [x] Impacted files manifest finalized.
- [x] OKR acceptance matrix established with deterministic criteria.
- [x] Transition to `03_exec.md` approved.
