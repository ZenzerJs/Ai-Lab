# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-XXX
- **Title:** [Task Name]
- **Status:** DRAFT | APPROVED | ACTIVE
- **Date Created:** YYYY-MM-DD
- **Owner:** [Lead Software Architect / Agent]

---

## 1. Problem Statement & Objectives
[Concise description of the user request, core motivation, and intended outcome.]

---

## 2. Scope Boundaries
The following components and behaviors are within the implementation boundary of this task:
- [System / Module / Feature 1]
- [System / Module / Feature 2]

---

## 3. Out-of-Scope Declarations
The following areas are explicitly excluded from this task to prevent scope creep:
- [Explicitly excluded item 1]
- [Explicitly excluded item 2]

---

## 4. Technical Constraints & Invariants
- **Platform Invariant:** Execution parity across Windows (PowerShell) and POSIX (bash/zsh).
- **Rule Adherence:** Compliance with all operational directives in `.agents/rules/`.
- **Tool Discipline:** Git write/commit tools are strictly barred during this intake stage.

---

## 5. Per-Stage Token Budget Allocation Table
To guarantee that active turn context remains strictly under the **8,000 token limit**, prompt slices must adhere to the following bounded budget:

| Slice Component | Allocated Token Budget | Target Description / Pruning Control |
|---|---|---|
| **System Persona & Rules** | 1,500 tokens | Fixed directives from `AGENTS.md` and `.agents/rules/` |
| **Tool Definitions (MCP/CLI)** | 1,200 tokens | Compact JSON-RPC tool definitions |
| **OKF Knowledge Base Slice** | 1,500 tokens | Targeted concept excerpts from `docs/` |
| **Repository Map (`repo_map.py`)** | 1,800 tokens | AST symbols enforced via `tiktoken` binary search |
| **Stage Contract & History** | 1,200 tokens | Active stage contract (`tasks/TSK-XXX/*.md`) and recent turns |
| **Volatile User Prompt & Headroom** | 800 tokens | Immediate user inputs, safety headroom |
| **Total Active Turn Context** | **8,000 tokens** | **Hard Maximum Ceiling** |

---

## 6. Exit Criteria & Stage Transition Checklist
- [ ] Problem statement validated against user request
- [ ] In-scope and out-of-scope boundaries unambiguously defined
- [ ] Token budget verified and approved
- [ ] Transition sign-off to `02_plan.md` granted
