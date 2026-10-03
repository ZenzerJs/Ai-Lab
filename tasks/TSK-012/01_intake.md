# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-012
- **Title:** AST Dead Code Finder Module
- **Status:** APPROVED
- **Date Created:** 2026-10-03
- **Owner:** Lead Software Architect / Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Objectives
The workspace requires an AST-based dead code finder in `src/dead_code_finder.py` with corresponding test fixtures and test suite in `src/test_dead_code_finder.py`.

Key Requirements:
1. Pure Python implementation using standard library `ast` and typing.
2. Detect unused private functions:
   - Module-level or class-level private functions (prefixed with `_` but not dunder methods `__...__`).
   - Private functions defined but never referenced or invoked within their scope/module.
3. Detect unreachable statement blocks after `return` or `raise` statements:
   - Statements appearing after a terminal statement (`return` or `raise`) within the same sequence of statements (block/body).
4. Provide structured reporting (e.g. filename/source, line number, issue type, symbol name or message).
5. Comprehensive unit test suite in `src/test_dead_code_finder.py` covering all detection scenarios, edge cases (dunders, valid calls, nested functions, if/else branches, try/except/finally), and clean code verification.

---

## 2. Scope Boundaries
The following components are within the boundary of this task:
- `src/dead_code_finder.py`: AST visitor implementation detecting unused private functions and unreachable statements.
- `src/test_dead_code_finder.py`: Unit test fixtures and assertions validating dead code detection.
- `tasks/TSK-012/`: ICM stage contracts (`01_intake.md`, `02_plan.md`, `03_exec.md`, `04_verify.md`).

---

## 3. Out-of-Scope Declarations
The following areas are explicitly excluded from this task:
- External linters or dependencies (e.g., flake8, vulture, pylint).
- Cross-module inter-file reference resolution (analysis is single-module / AST scoped).
- Modifying unrelated workspace tools, orchestrator scripts, or benchmark runners.

---

## 4. Technical Constraints & Invariants
- **Platform Invariant:** Execution parity across Windows (PowerShell) and POSIX (bash/zsh).
- **Rule Adherence:** Compliance with all operational directives in `.agents/rules/`.
- **Tool Discipline:** Git write/commit tools are strictly barred during intake and planning stages.
- **Dependency Invariant:** Python Standard Library only (`ast`, `typing`, `dataclasses`, `unittest`).
- **Log Sanitation:** All test and validation commands executed through `scripts/filter_output.py`.

---

## 5. Per-Stage Token Budget Allocation Table

| Slice Component | Allocated Token Budget | Target Description / Pruning Control |
|---|---|---|
| **System Persona & Rules** | 1,500 tokens | Fixed directives from `AGENTS.md` and `.agents/rules/` |
| **Tool Definitions (MCP/CLI)** | 1,200 tokens | Compact JSON-RPC tool definitions |
| **OKF Knowledge Base Slice** | 1,500 tokens | Excerpts from `docs/` |
| **Active Task Contract** | 2,000 tokens | Current stage contract markdown (`tasks/TSK-012/*.md`) |
| **Volatile User Prompt & Margin** | 1,800 tokens | Immediate user inputs, safety headroom |
| **Total Active Turn Context** | **8,000 tokens** | **Hard Maximum Ceiling** |

---

## 6. Exit Criteria & Stage Transition Checklist
- [x] Problem statement validated against user request.
- [x] In-scope and out-of-scope boundaries unambiguously defined.
- [x] Token budget verified and approved.
- [x] Transition sign-off to `02_plan.md` granted.
