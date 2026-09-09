# Antigravity AI-Lab: Comprehensive Workspace & Measurement System Architecture

**Workspace:** `c:\Users\jayde\.gemini\AI-Lab`  
**Execution Timestamp:** 2026-09-09  
**Role:** Lead Software Architect  
**Status:** FULLY BOOTSTRAPPED, VERIFIED & PRODUCTION READY  

---

## 1. Architectural Foundations & Governance

The Antigravity AI-Lab workspace implements a deterministic, token-budgeted, and mathematically verified autonomous agent environment governed by two foundational methodologies:

### 1.1 Interpretable Context Methodology (ICM)
All development tasks execute through a 5-stage sequential lifecycle enforced via discrete contract files in `tasks/TSK-XXX/`:
1. `01_intake.md`: Explicit boundary constraints, out-of-scope declarations, and turn token budgets.
2. `02_plan.md`: Technical design, affected symbols, and an OKR Acceptance Matrix with machine-verifiable exit criteria.
3. `03_exec.md`: Search/replace change tracking, symbol modification ledger, and escape-hatch justifications.
4. `04_verify.md`: Automated test execution outputs, linter assertions, and token telemetry ledger.
5. `05_retro.md`: Retrospective observations, learnings, and bidirectional knowledge propagation into `docs/`.

### 1.2 Google Cloud Open Knowledge Format (OKF v0.2)
Layer 3 project knowledge is structured as a self-describing, human-reviewed, machine-navigable OKF v0.2 bundle under `docs/`:
- **Bundle Root (`docs/index.md`):** Strictly lowercase, containing only `okf_version: "0.2"` in YAML frontmatter, providing an entry catalog of absolute bundle-relative links (`/concepts/...`).
- **Knowledge Log (`docs/log.md`):** Strictly lowercase chronological update log updated exclusively from task retrospectives.
- **Specification Tracking (`docs/SPEC-VERSIONS.md`):** Pinned upstream SHAs and ISO timestamps.
- **Concepts & Schemas (`docs/concepts/`, `docs/schemas/`):** Strict frontmatter schema (`type`, `title`, `description`, `status`, `verified`, `sources`).
- **Knowledge Visualizer (`docs/viz.html`):** Cytoscape.js interactive graph visualizer mapping concept relationships.

### 1.3 Core Governance Invariants
- **Byte-Stability Invariant:** Prompt prefix context (System persona, Tool definitions, OKF concept slices, Stage contracts) must never include volatile timestamps, build IDs, or dynamic counters that bust KV cache prefix reuse.
- **Diff-Only Editing Rule:** Existing files over 50 lines must use standard Search/Replace blocks (`<<<<<<< SEARCH`, `=======`, `>>>>>>> REPLACE`). Complete overwrites require logged justifications.
- **Context Isolation Rule:** Reading complete files directly is barred when AST queries or symbol lookups suffice. Agents must query via `ast-grep` or `scripts/repo_map.py`.
- **Log Sanitation Rule:** All shell, test, and build commands must execute through `scripts/filter_output.py`. Raw stdout/stderr terminal dumps into agent conversation context are forbidden.
- **Tool Discipline:** Git modifying tools are blocked during `01_intake` and `02_plan`. Sequential-thinking tools are blocked during `03_exec` and `04_verify`.

---

## 2. Cross-Platform Runtime & Toolchain Infrastructure

### 2.1 Preflight Environment
The system operates seamlessly across Windows, macOS, and Linux:
- `python` 3.14.3 (`C:\Users\jayde\AppData\Local\Python\pythoncore-3.14-64\python.exe`)
- `git` 2.53.0 (`C:\Program Files\Git\cmd\git.exe`)
- `uvx` 0.12.12 (`C:\Users\jayde\AppData\Local\Python\bin\uvx.exe`)
- `npx` 11.17.0 (`C:\Program Files\nodejs\npm.cmd`)

### 2.2 Cross-Platform Shim Architecture
Every automation utility is built as a pure Python 3 script accompanied by lightweight wrappers:
- `.ps1` (PowerShell) for Windows hosts.
- `.sh` (POSIX Bash) for Linux/macOS hosts, tracked in git with `100755` executable permissions.

### 2.3 Core Tooling & Upstream Pinned Specifications
- `ast-grep` (`@ast-grep/cli@0.45.3`): Primary structural AST search and rewrite tool.
- `repomix` (`repomix@1.18.0`): Bounded context packing tool.
- `grep-ast` (`grep-ast==0.9.0`): Tree-sitter AST symbol extractor.
- `tiktoken` (`tiktoken==0.14.0`): OpenAI BPE token counting engine (`cl100k_base`).
- **Google Cloud OKF v0.2:**
  - Upstream Repo: `https://github.com/GoogleCloudPlatform/open-knowledge-format.git`
  - Pinned Commit: `ad30107c31c06aec8a7d5636e0d1058118604e6f` (stable reference `0b87c52`)
  - Commit Date: `2026-08-21T20:08:36Z`
- **Interpretable Context Methodology (ICM):**
  - Upstream Repo: `https://github.com/RinDig/Interpretable-Context-Methodology.git`
  - Reference Commit: `02ba5d85c7871b75c7c702a2d8da6524723d53d4`
  - Commit Date: `2026-07-25T16:17:00Z`

---

## 3. Multi-Root MCP Server Configuration (`.agents/mcp_config.json`)

The workspace configures three sandboxed Model Context Protocol (MCP) servers:
1. **`git` (`uvx mcp-server-git`):** Exposes structured git primitives (`git_status`, `git_diff_unstaged`, `git_log`).
2. **`filesystem` (`npx @modelcontextprotocol/server-filesystem`):** Multi-root mounted sandboxing filesystem writes strictly to:
   - `./tasks`
   - `./src`
   - `./docs`
   - `./scripts`
   - `./data`
   - `./experiments`
   - `./dashboard`
   - `./config`
   *(Root files like `AGENTS.md`, `.gitignore`, and `.git/` are strictly protected from MCP writes).*
3. **`sequential-thinking` (`npx @modelcontextprotocol/server-sequential-thinking`):** Dynamic scratchpad restricted to max 10 steps per invocation and active strictly during the `02_plan` stage.

---

## 4. Token-Optimization & Utility Layer

### 4.1 `scripts/repo_map.py` (AST Map Generator)
- Uses `grep-ast` TreeContext to parse Python class definitions, function signatures, type annotations, and module docstrings.
- **Tokenizer Margin Rule:** Enforces an internal target ceiling of **1,800 tokens** using `tiktoken` (`cl100k_base`). This accounts for tokenizer variation between OpenAI BPE and Gemini tokenizers, guaranteeing output remains strictly under 2,000 tokens.
- **Dynamic Binary Search Pruning:** Evaluates complete rendered output (including telemetry header) to guarantee strict `<= max_tokens` compliance across any budget scale (tested down to 50 tokens).

### 4.2 `scripts/filter_output.py` (Log Sanitizer)
- Command wrapper executing processes while isolating stdout/stderr noise.
- On success (`exit code 0`): Collapses output to a single line: `✓ Command succeeded: [args]`.
- On failure (`non-zero exit code`): Strips boilerplate noise and emits only the failing assertion, file, line number, and stack trace.
- **Windows Batch Resolution:** Automatically resolves `.cmd`/`.bat` binaries (`npx`, `npm`, `ast-grep`, `repomix`) via `shutil.which()`.

### 4.3 `scripts/lint_frontmatter.py` (OKF Validator)
- Asserts strict lowercase reserved filenames (`index.md`, `log.md`).
- Enforces that `docs/index.md` contains only `okf_version: "0.2"`.
- Enforces valid OKF v0.2 keys on content markdown (`type`, `title`, `description`, `status`, `verified`, `sources`, `stale_after`).
- Enforces bundle-relative link format (`/path/to/doc.md`) and validates link resolution against disk with case-sensitivity matching to prevent Windows NTFS casing drift.

---

## 5. Measurement Layer & A/B Experimentation System

The measurement layer captures real, granular token economics from Antigravity headless CLI runs and benchmarks the structured ICM pipeline against an unconstrained baseline agent.

### 5.1 Experiment Runner (`scripts/run_experiment.py`)
- Reads task definitions from `experiments/tasks/<TASK-ID>.md`.
- Headless execution with `--output-format stream-json`:
  - **Baseline Arm:** Raw prompt bytes only; no ICM stage contracts loaded.
  - **ICM Arm:** Full ICM pipeline execution (`01_intake` -> `02_plan` -> `03_exec` -> `04_verify`).
- Parses NDJSON streaming event packets to extract cumulative `usage`:
  - `input_tokens`
  - `output_tokens`
  - `thinking_tokens`
  - `cache_read_tokens`
  - `total_tokens`
  - `num_turns`
  - `duration_seconds`
- **Four Strict Fairness Invariants:**
  1. Identical model IDs across both arms.
  2. Starting worktree clean state (checked via git status/checkout).
  3. Exact prompt bytes parity between arms.
  4. Minimum sample size ($n \ge 2$, default $n=3$).
  *Violations abort execution immediately with exit code `1`.*
- **Dry-Run Engine:** Replays synthetic NDJSON event stream fixtures from `experiments/fixtures/mock_stream.ndjson` for zero-cost testing.

### 5.2 SQLite Usage Ledger (`scripts/ledger.py` + `data/usage.db`)
- Relational schema:
  - `runs`: Primary table storing run index, arm, model, tokens, turns, duration, timestamp.
  - `tasks`: Catalog of tasks, prompt paths, notes, creation dates.
  - `pricing`: Model rates per million tokens (`input_usd_per_mtok`, `cache_read_usd_per_mtok`, `output_usd_per_mtok`, `source_url`, `fetched_at`).
- **External Pricing Configuration (`config/PRICING.json`):** User-auditable pricing with source documentation URLs. Never hardcoded in application logic.
- **Cache-Aware Cost Formula:**
  $$\text{Cost} = \left(\frac{\text{Input Tokens} \times \text{Input Rate}}{10^6}\right) + \left(\frac{\text{Cache Read Tokens} \times \text{Cache Read Rate}}{10^6}\right) + \left(\frac{\text{Output Tokens} \times \text{Output Rate}}{10^6}\right)$$
- **Paired-Index Mathematical Consistency:** Cumulative savings computations align identically with the dashboard timeline curve.

---

## 6. Local Savings Dashboard (`dashboard/`)

A responsive **Vite + React 18 + TypeScript** web application styled with **Tailwind CSS** and charted with **Recharts**:
- **Static Exporter (`dashboard/build_data.py`):** Queries `data/usage.db` and exports static metrics to `dashboard/public/data.json`.
- **Five Primary Views:**
  1. **Per-Task Cost Comparison:** Grouped bar chart comparing baseline vs. ICM mean costs (USD) with min–max error bars and sample size tags ($n=X$).
  2. **Cache Hit Ratio:** Dual donut visualizer showing cache hit efficiency (`cache_read_tokens / input_tokens`).
  3. **Cumulative Measured Savings:** Metric hero card and running savings curve ($).
  4. **Turns & Duration:** Side-by-side metric bars comparing latency and interaction overhead.
  5. **Raw Ledger Table:** Collapsible, sortable data table with a direct JSON export link.
- **UI Constraints:**
  - Every chart strictly labels sample size ($n=X$).
  - Projections and speculative curves are strictly barred.
  - Fallback empty states render cleanly when no runs are present.

---

## 7. Skill Registrations & AI-Lab Command Interface

### 7.1 Unified `/Ai-Lab` Skill
Available both inside the workspace (`.agents/skills/ai-lab.md`) and in the user's global skill registry (`~/.gemini/config/skills/ai-lab/SKILL.md`):
- `/Ai-Lab --status`: Displays ledger summary, per-task savings, and cache hit ratios.
- `/Ai-Lab --run <TASK-ID>`: Validates task definition, executes A/B experiment, and refreshes static data.
- `/Ai-Lab --dashboard`: Refreshes static JSON and launches the local Vite dev server at `http://localhost:5173`.
- `/Ai-Lab --dry-run`: Runs zero-cost synthetic verification using `MOCK-001`.

### 7.2 Additional Skills
- `.agents/skills/repo_map.md`: Instructions for structural AST navigation.
- `.agents/skills/filter_output.md`: Instructions for executing commands with noise suppression.
- `.agents/skills/run_experiment.md`: Reference for running A/B benchmark trials.
- `.agents/skills/usage_dashboard.md`: Reference for dashboard compilation and hosting.

---

## 8. Verification & Smoke Test Ledger

All smoke tests executed cleanly with exit code `0`:

| Test Target | Command | Result | Verification Notes |
|---|---|---|---|
| Filter Output (Success) | `python scripts/filter_output.py -- python -c "print('test passing')"` | `Exit 0` | Collapsed to 1-line summary |
| Filter Output (Failure) | `python scripts/filter_output.py -- python -c "import sys; sys.stderr.write('fatal error\n'); sys.exit(1)"` | `Exit 1` | Isolated error trace without noise |
| AST Symbol Extraction | `python scripts/repo_map.py --target scripts/_smoke_sample.py` | `Exit 0` | Extracted symbols, tokens = 312 <= 1,800 |
| OKF v0.2 Linter | `python scripts/lint_frontmatter.py` | `Exit 0` | Strict lowercase, schema, and casing check passed |
| MCP Config Validity | `python -c "import json, shutil; ..."` | `Exit 0` | Valid JSON; `uvx` and `npx` resolve on PATH |
| A/B Runner (Dry Run) | `python scripts/run_experiment.py --task MOCK-001 --dry-run` | `Exit 0` | Populated 6 runs into `data/usage.db` |
| Invariant Abort ($n < 2$) | `python scripts/run_experiment.py --task MOCK-001 --dry-run --runs 1` | `Exit 1` | Aborted cleanly on invariant violation |
| Invariant Abort (Model) | `python scripts/run_experiment.py --task MOCK-001 --dry-run --model unknown` | `Exit 1` | Aborted cleanly on missing pricing rate |
| Usage Ledger Summary | `python scripts/ledger.py summary MOCK-001` | `Exit 0` | Baseline $0.13085 vs ICM $0.06379 (51.25% savings) |
| Dashboard Data Build | `python dashboard/build_data.py` | `Exit 0` | Exported `dashboard/public/data.json` |
| Vite Frontend Build | `cd dashboard && npm run build` | `Exit 0` | Compiled `dashboard/dist/` with 0 type errors |
| Frontmatter Regression | `python scripts/lint_frontmatter.py` | `Exit 0` | 0 regressions after measurement additions |

*Constraint Verification:* **No live model calls were made. The ledger currently contains only MOCK-001 data.**

---

## 9. Complete Repository Tree Structure

```text
c:\Users\jayde\.gemini\AI-Lab
├── .agents/
│   ├── mcp_config.json
│   ├── rules/
│   │   ├── context-assembly.md
│   │   ├── context-isolation.md
│   │   ├── diff-only-editing.md
│   │   ├── log-sanitation.md
│   │   ├── okr-gate.md
│   │   ├── session-resume.md
│   │   └── tool-discipline.md
│   └── skills/
│       ├── ai-lab.md
│       ├── filter_output.md
│       ├── repo_map.md
│       ├── run_experiment.md
│       └── usage_dashboard.md
├── .gitignore
├── AGENTS.md
├── BOOTSTRAP_ARTIFACT.md
├── MEASUREMENT_LAYER_ARTIFACT.md
├── AI_LAB_COMPREHENSIVE_RECORD.md
├── AI_LAB_COMPREHENSIVE_RECORD.xml
├── config/
│   └── PRICING.json
├── data/
│   └── usage.db
├── dashboard/
│   ├── build_data.ps1
│   ├── build_data.py
│   ├── build_data.sh
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── dist/
│   ├── public/
│   │   └── data.json
│   └── src/
│       ├── App.tsx
│       ├── index.css
│       ├── main.tsx
│       ├── types.ts
│       └── components/
│           ├── CacheHitRatio.tsx
│           ├── CumulativeSavings.tsx
│           ├── Header.tsx
│           ├── PerTaskComparison.tsx
│           ├── RawLedgerTable.tsx
│           └── TurnsDuration.tsx
├── docs/
│   ├── SPEC-VERSIONS.md
│   ├── index.md
│   ├── log.md
│   ├── viz.html
│   ├── concepts/
│   │   ├── architecture-overview.md
│   │   ├── coding-standards.md
│   │   └── measurement-layer.md
│   └── schemas/
│       └── data-contracts.md
├── experiments/
│   ├── README.md
│   ├── fixtures/
│   │   └── mock_stream.ndjson
│   └── tasks/
│       └── MOCK-001.md
├── scripts/
│   ├── filter_output.ps1
│   ├── filter_output.py
│   ├── filter_output.sh
│   ├── ledger.ps1
│   ├── ledger.py
│   ├── ledger.sh
│   ├── lint_frontmatter.ps1
│   ├── lint_frontmatter.py
│   ├── lint_frontmatter.sh
│   ├── repo_map.ps1
│   ├── repo_map.py
│   ├── repo_map.sh
│   ├── run_experiment.ps1
│   ├── run_experiment.py
│   └── run_experiment.sh
├── src/
│   └── .gitkeep
└── tasks/
    ├── README.md
    ├── _template/
    │   ├── 01_intake.md
    │   ├── 02_plan.md
    │   ├── 03_exec.md
    │   ├── 04_verify.md
    │   └── 05_retro.md
    └── TSK-001/
        ├── 01_intake.md
        ├── 02_plan.md
        ├── 03_exec.md
        ├── 04_verify.md
        └── 05_retro.md
```

---

## 10. Operator Execution Guide

### 10.1 Running a Real A/B Experiment
1. Create a task specification at `experiments/tasks/<TASK-ID>.md`.
2. Run the experiment CLI from the terminal:
   ```bash
   python scripts/run_experiment.py --task <TASK-ID>
   ```
3. Check analytical metrics:
   ```bash
   python scripts/ledger.py summary <TASK-ID>
   ```

### 10.2 Hosting the Savings Dashboard
1. Re-compile static metrics:
   ```bash
   python dashboard/build_data.py
   ```
2. Start the local Vite server:
   ```bash
   cd dashboard
   npm run dev
   ```
3. Open `http://localhost:5173`.

### 10.3 Initializing a New Development Task
1. Clone the stage template into a new task folder:
   ```bash
   cp -r tasks/_template tasks/TSK-002
   ```
2. Complete `01_intake.md` and `02_plan.md` prior to code modifications.
