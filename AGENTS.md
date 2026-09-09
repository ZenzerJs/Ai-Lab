# Antigravity Workspace Master Architectural Directives

Welcome to the **Antigravity AI-Lab Workspace**. This workspace strictly enforces the **Interpretable Context Methodology (ICM)**, the **Google Cloud Open Knowledge Format (OKF v0.2)**, AST-based structural code navigation, and automated token-budget optimization.

---

## 1. Architectural Foundation

### Interpretable Context Methodology (ICM)
All tasks progress through a 5-stage formal pipeline with explicit stage contracts located in `tasks/TSK-XXX/`:
1. `01_intake.md`: Scope boundaries, constraints, out-of-scope declarations, and stage token budgets.
2. `02_plan.md`: Technical architecture, impacted files manifest, and OKR Acceptance Matrix.
3. `03_exec.md`: Search/replace change tracking, symbol modification ledger, and escape-hatch justifications.
4. `04_verify.md`: Automated test assertions, linter outputs, and token telemetry ledger.
5. `05_retro.md`: Retrospective observations, learnings, and knowledge propagation into `docs/`.

### Google Cloud Open Knowledge Format (OKF v0.2)
Layer 3 project knowledge is structured as a self-describing OKF bundle under `docs/`:
- Bundle Root: `docs/index.md` (strictly lowercase, frontmatter contains *only* `okf_version: "0.2"`).
- Knowledge Log: `docs/log.md` (strictly lowercase, chronological update log).
- Specification Tracking: `docs/SPEC-VERSIONS.md` (pinned upstream SHAs).
- Concepts & Schemas: `docs/concepts/` and `docs/schemas/`.
- Knowledge Graph Visualizer: `docs/viz.html` (Cytoscape.js interface).

---

## 2. Master Operational Directives

Autonomous agents must strictly comply with the modular rules defined in `.agents/rules/`:

| Rule File | Summary Directive |
|---|---|
| [`.agents/rules/session-resume.md`](.agents/rules/session-resume.md) | Inspect `tasks/` to locate active `TSK-XXX` and resume from its latest stage contract; never assume conversational memory. |
| [`.agents/rules/context-assembly.md`](.agents/rules/context-assembly.md) | Assemble prompt context deterministically: (1) System Persona, (2) Tool Definitions, (3) OKF Concept slice, (4) Active Stage Contract, (5) Volatile User Input. Invariant: Sections 1–4 must never contain volatile timestamps or build IDs that bust prefix caching. |
| [`.agents/rules/diff-only-editing.md`](.agents/rules/diff-only-editing.md) | Edits to files >50 lines must use standard Search/Replace blocks (`<<<<<<< SEARCH`, `=======`, `>>>>>>> REPLACE`). Full overwrites require explicit justification. |
| [`.agents/rules/context-isolation.md`](.agents/rules/context-isolation.md) | Full-file dumps are barred when symbol lookups suffice. Query code via `ast-grep` or `scripts/repo_map.py`. |
| [`.agents/rules/log-sanitation.md`](.agents/rules/log-sanitation.md) | Test/build commands must execute via `scripts/filter_output.py`. Raw stdout/stderr terminal dumps into conversation context are forbidden. |
| [`.agents/rules/okr-gate.md`](.agents/rules/okr-gate.md) | Moving from `02_plan` to `03_exec` strictly requires an approved OKR matrix with deterministic, machine-verifiable exit criteria. |
| [`.agents/rules/tool-discipline.md`](.agents/rules/tool-discipline.md) | Git modification tools barred during `01_intake` and `02_plan`. Sequential-thinking tools barred during `03_exec` and `04_verify`. |

---

## 3. Tooling & MCP Server Infrastructure

### Multi-Root MCP Server Configuration (`.agents/mcp_config.json`)
The workspace provides sandboxed MCP servers configured in `.agents/mcp_config.json`:
- **`git` (`uvx mcp-server-git`)**: Structured git status, diffs, and commit history.
- **`filesystem` (`npx @modelcontextprotocol/server-filesystem`)**: Multi-root mounting sandboxed exclusively to `./tasks`, `./src`, `./docs`, and `./scripts`. Root configuration and `.git` are protected from MCP write operations.
- **`sequential-thinking` (`npx @modelcontextprotocol/server-sequential-thinking`)**: Cognitive scratchpad constrained to max 10 steps per invocation, active strictly during the `02_plan` stage.

### Automation Scripts (`scripts/`)
All scripts are implemented as cross-platform Python 3 utilities with `.ps1` and `.sh` shims:
- `scripts/repo_map.py`: Tree-sitter AST symbol extractor with `tiktoken` binary-search pruning enforcing a strict 1,800-token margin budget.
- `scripts/filter_output.py`: Output wrapper collapsing successful test runs into a 1-line summary (`✓ Command succeeded: [args]`) and isolating failure traces.
- `scripts/lint_frontmatter.py`: Linter enforcing OKF v0.2 frontmatter compliance, case sensitivity, link integrity, and schema house rules across `docs/`.
