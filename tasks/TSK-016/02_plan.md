# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-016
- **Experiment Ref:** EXP-007
- **Title:** Dynamic API Gateway Telemetry Simulator ("PulseEngine Sandbox")
- **Status:** APPROVED
- **Prerequisite:** `01_intake.md` exit criteria satisfied
- **Task Contract Ref:** ICM Pipeline

---

## 1. Technical Approach & Architecture

### 1.1 Architecture & Design Components
1. **Interactive SVG/Canvas Topology:**
   - Visual nodes: Ingress Gateway (`envoy-edge-01`), 3 microservices (Auth-Service, Billing-Engine, Catalog-Store), and InfluxDB Sink (`telemetry-lake-01`).
   - SVG conduit links connecting Ingress -> microservices -> InfluxDB.
   - Animated SVG packet pulses flowing along paths using cubic spline interpolation via `requestAnimationFrame` with glowing color states (cyan/indigo nominal, rose/amber during chaos).
   - Node hover cards showing live pod metadata, status, and active connection counts.

2. **Real-Time Latency Percentiles & Bespoke SVG Sparklines:**
   - 800ms vanilla JS simulation loop computing p50 (median), p95 (tail), and p99 (critical outliers) over a sliding 30-sample history window.
   - Zero external charting libraries: uses custom cubic Bezier Catmull-Rom smoothing in SVG `<path>` with gradient area fills and active trailing dots.
   - Dynamic evaluation against user-configured latency thresholds updating status badges (`Optimal`, `Warning`, `Breach`).

3. **Chaos Engine Toggle:**
   - Injects simulated latency spikes (up to 550ms on p99) and 5xx HTTP gateway errors (12-18% error rate) on Billing and Catalog services.
   - Visual node state updates: affected nodes transition to amber/rose with pulse halo animations.
   - Dynamic anomaly alert banner displays at top of dashboard with dismiss capability.

4. **Accessible Threshold Configuration Dialog:**
   - Dialog with `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, and `aria-describedby`.
   - Focus lock/trap implementation preventing Tab navigation from escaping dialog while open.
   - Escape key dismisses modal and restores focus back to triggering button.
   - Sliders for adjusting p50, p95, and p99 alert thresholds with live value previews and "Reset Defaults" option.

5. **Responsive Layout:**
   - Fully fluid layout from 375px mobile viewports up to 1440px desktop screens using modern Tailwind CSS grid and flex utilities.

### Cognitive Reasoning Trace (Sequential Thinking)
1. Step 1: Deconstruct requirements into standalone HTML + Tailwind CDN delivery model.
2. Step 2: Ensure bespoke SVG sparklines produce valid SVG paths (`M ... C ... L ... Z`) without external JS dependencies.
3. Step 3: Implement accessible focus trap, Escape handler, and ARIA attributes for modal dialog.
4. Step 4: Validate chaos mode state transitions across nodes, alert banners, and live ticker logs.
5. Step 5: Verify responsiveness across 375px mobile and 1440px desktop.

---

## 2. Impacted Files Manifest

| Target File Path | Action (`CREATE` / `MODIFY`) | Description & Rationale | Diff Block Required (>50 lines) |
|---|---|---|---|
| `experiments/tasks/EXP-007/index.html` | `CREATE` / `VERIFY` | Complete standalone PulseEngine Sandbox HTML dashboard | No |
| `tasks/TSK-016/01_intake.md` | `CREATE` | Intake stage contract | No |
| `tasks/TSK-016/02_plan.md` | `CREATE` | Technical plan and OKR matrix | No |
| `tasks/TSK-016/03_exec.md` | `CREATE` | Execution log and symbol tracking | No |
| `tasks/TSK-016/04_verify.md` | `CREATE` | Verification evidence and checklist | No |

---

## 3. OKR Acceptance Matrix (Machine-Verifiable Exit Criteria)

**Objective:** Deliver an accessible, production-grade API gateway telemetry simulator conforming to all EXP-007 specifications.

| Key Result (KR) | Deterministic Success Metric | Automated Verification Command | Status |
|---|---|---|---|
| **KR 1: Standalone HTML & Tailwind CDN** | Standalone HTML file exists, loads Tailwind CSS CDN, zero external chart libs | File structure inspection & dependency check | PENDING |
| **KR 2: Node Topology & Packet Pulses** | Ingress -> 3 Services -> Influx Sink SVG topology present with animated pulses | Code inspection & node count validation | PENDING |
| **KR 3: Real-Time Latency Sparklines** | 800ms vanilla JS ticker, live p50/p95/p99 sparklines via bespoke SVG paths | JS function & event loop validation | PENDING |
| **KR 4: Chaos Engine & Alert Banner** | Chaos toggle switches node states to amber/rose, triggers alert banner & 5xx logs | Chaos engine state machine validation | PENDING |
| **KR 5: Accessible Dialog & Responsiveness** | Accessible modal with focus trap, ESC dismissal, ARIA attributes; responsive 375px/1440px | Accessibility check & layout verification | PENDING |

---

## 4. Stage Gate Transition Check
Per `.agents/rules/okr-gate.md`, implementation in `03_exec.md` must not commence until:
- [x] Technical architecture reviewed and validated.
- [x] Impacted files manifest completely populated.
- [x] OKR Acceptance Matrix defined with automated verification commands.
- [x] Sign-off approved to transition to `03_exec.md`.
