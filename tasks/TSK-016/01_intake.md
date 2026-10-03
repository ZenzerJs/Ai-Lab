# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-016
- **Experiment Ref:** EXP-007
- **Title:** Dynamic API Gateway Telemetry Simulator ("PulseEngine Sandbox")
- **Status:** APPROVED
- **Date Created:** 2026-10-03
- **Owner:** Full-Stack & Frontend Engineering Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Objectives
Build a production-grade, interactive single-page simulation dashboard named "PulseEngine Sandbox" satisfying all core requirements:
1. Interactive SVG/Canvas node topology (Ingress -> 3 Services -> Influx Sink) with animated traffic pulses.
2. Real-time metrics panel: Live p50, p95, p99 latency sparklines updated every 800ms via vanilla JS ticker.
3. Interactive Chaos Engine toggle: Injects latency and 5xx errors, turning affected nodes amber/red and firing an alert banner.
4. Threshold configuration modal/drawer built according to accessible dialog patterns (ESC to dismiss, focus lock).
5. Responsive layout across 375px mobile and 1440px desktop.

Output constraints: Standalone HTML file utilizing Tailwind CSS CDN. Zero bloated external charting libraries (use bespoke SVG curves).

---

## 2. Scope Boundaries
The following files and components are within boundary:
- `experiments/tasks/EXP-007/index.html`: Standalone HTML file containing the complete application with Tailwind CSS CDN, bespoke SVG sparklines, accessible modal dialog, chaos toggle, and live topology.
- `tasks/TSK-016/`: Formal ICM stage contracts (`01_intake.md`, `02_plan.md`, `03_exec.md`, `04_verify.md`, `05_retro.md`).

---

## 3. Out-of-Scope Declarations
- External charting dependencies (Chart.js, D3.js, Highcharts, Recharts); bespoke SVG spline rendering must be utilized.
- Backend server dependencies; must operate completely client-side in a standalone HTML file.
- Any modifications to other benchmark experiments or unrelated workspace files.

---

## 4. Technical Constraints & Invariants
- **Styling:** Tailwind CSS CDN (`https://cdn.tailwindcss.com`) with custom dark palette extensions.
- **Visuals:** Bespoke SVG Bezier curves and SVG traffic pulses along conduits using requestAnimationFrame.
- **Accessibility:** WAI-ARIA compliance for dialog (`role="dialog"`, `aria-modal="true"`, focus trap, Escape dismissal).
- **Responsive Design:** Fluid responsiveness tested for 375px viewport up to 1440px+ desktop.

---

## 5. Token Budget Allocation Table
| Slice Component | Allocated Token Budget | Target Description / Pruning Control |
|---|---|---|
| **System Persona & Rules** | 1,500 tokens | Fixed directives from `AGENTS.md` and `.agents/rules/` |
| **Tool Definitions (MCP/CLI)** | 1,200 tokens | Compact JSON-RPC tool definitions |
| **OKF Knowledge Base Slice** | 1,500 tokens | Targeted concept excerpts from `docs/` |
| **Repository Map (`repo_map.py`)** | 1,800 tokens | AST symbols enforced via `tiktoken` binary search |
| **Stage Contract & History** | 1,200 tokens | Active stage contract (`tasks/TSK-016/*.md`) and recent turns |
| **Volatile User Prompt & Headroom** | 800 tokens | Immediate user inputs, safety headroom |
| **Total Active Turn Context** | **8,000 tokens** | **Hard Maximum Ceiling** |

---

## 6. Exit Criteria & Stage Transition Checklist
- [x] Problem statement validated against user request.
- [x] In-scope and out-of-scope boundaries unambiguously defined.
- [x] Token budget verified and approved.
- [x] Transition sign-off to `02_plan.md` granted.
