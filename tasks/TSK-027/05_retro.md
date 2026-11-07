# Task Stage Contract: 05_retro

## Task Metadata
- **Task ID:** TSK-027
- **Title:** Full Benchmark Quality Audit (`EXP-001`..`EXP-008`) & Live Multi-File Evaluation (`EXP-009`..`EXP-011`)
- **Status:** COMPLETE
- **Owner:** Systems Engineering & Research Agent

---

## 1. Retrospective Observations & Learnings
- **Quality CIs Do Not Cross Zero:** While cost delta across the original 7 tasks had wide variance (−68.3% to +41.1%), the 5-dimension quality delta across all 11 tasks (`EXP-001`..`EXP-011`) is **+8.91 percentage points with a 95% CI of [+2.00%, +17.64%]** — strictly positive.
- **Where ICM Wins on Quality:**
  1. **Design & Accessibility (+1.00 / 5.00, 95% CI: [+0.29, +1.71]):** On UI tasks (`EXP-005`..`EXP-008`), baseline builds omitted semantic `<main>` landmarks and ARIA dialog/control attributes, whereas ICM enforced accessible semantic markup and fuller UI state coverage (+43% to +174% richer DOM structure).
  2. **Process & Tool Hygiene (+0.73 / 5.00, 95% CI: [0.00, +1.64]):** Across live NDJSON logs, baseline agents committed **11 tool/path errors** (wrong directory paths, failed file overwrites), whereas ICM committed only **1** (a 91% reduction in execution errors).
  3. **Pre-Seeded Outline Parity (`EXP-009`..`EXP-011`):** When starter HTML files already contained semantic `<main>` and `aria-live` attributes in the scaffolded outline, both Baseline (64 steps) and ICM (75 steps) achieved 24/25 (96.0%) and 100% test pass rates on the concurrency, graph/BM25, and security fixes.
