# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-010
- **Title:** Pure-Python Slugify Utility Module
- **Status:** APPROVED
- **Date Created:** 2026-10-03
- **Owner:** Lead Software Architect / Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Objectives
The workspace requires a standalone, zero-external-dependency pure-Python `slugify` utility function located at `src/slugify.py` with corresponding unit tests located at `src/test_slugify.py`.

Key Requirements:
1. Pure Python implementation with zero third-party dependencies (using standard library: `re`, `unicodedata`).
2. Robust slugification handling unicode transliteration (e.g. converting accents/diacritics in ASCII mode or preserving unicode when specified).
3. Support configurable separators (default `-`) and lowercase normalization.
4. Comprehensive unit test suite covering basic strings, custom separators, repeated whitespace/hyphens, special characters, unicode handling, edge cases (empty strings, numbers, whitespace).

---

## 2. Scope Boundaries
The following components are within the boundary of this task:
- `src/slugify.py`: Standalone pure-Python `slugify` function implementation.
- `src/test_slugify.py`: Comprehensive `unittest` test suite covering functional requirements and boundary conditions.
- `tasks/TSK-010/`: ICM stage contracts (`01_intake.md`, `02_plan.md`, `03_exec.md`, `04_verify.md`).

---

## 3. Out-of-Scope Declarations
The following areas are explicitly excluded from this task:
- Introducing any third-party dependencies (e.g., `python-slugify`, `awesome-slugify`).
- Modifying workspace orchestration or experiment harness scripts (`scripts/run_experiment.py`, `dashboard/`).
- Database migrations or schema modifications.

---

## 4. Technical Constraints & Invariants
- **Platform Invariant:** Execution parity across Windows (PowerShell) and POSIX (bash/zsh).
- **Rule Adherence:** Compliance with all operational directives in `.agents/rules/`.
- **Tool Discipline:** Git write/commit tools are strictly barred during intake and planning stages.
- **Dependency Invariant:** Python Standard Library only (`re`, `unicodedata`, `typing`).
- **Log Sanitation:** All test and validation commands executed through `scripts/filter_output.py`.

---

## 5. Per-Stage Token Budget Allocation Table
To guarantee that active turn context remains strictly under the **8,000 token limit**, prompt slices adhere to the bounded budget:

| Slice Component | Allocated Token Budget | Target Description / Pruning Control |
|---|---|---|
| **System Persona & Rules** | 1,500 tokens | Fixed directives from `AGENTS.md` and `.agents/rules/` |
| **Tool Definitions (MCP/CLI)** | 1,200 tokens | Compact JSON-RPC tool definitions |
| **OKF Knowledge Base Slice** | 1,500 tokens | Excerpts from `docs/` |
| **Active Task Contract** | 2,000 tokens | Current stage contract markdown (`tasks/TSK-010/*.md`) |
| **Volatile User Prompt & Margin** | 1,800 tokens | Immediate user inputs, safety headroom |
| **Total Active Turn Context** | **8,000 tokens** | **Hard Maximum Ceiling** |

---

## 6. Exit Criteria & Stage Transition Checklist
- [x] Problem statement validated against user request
- [x] In-scope and out-of-scope boundaries unambiguously defined
- [x] Token budget verified and approved
- [x] Transition sign-off to `02_plan.md` granted
