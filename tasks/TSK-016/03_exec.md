# Task Stage Contract: 03_exec

## Task Metadata
- **Task ID:** TSK-016
- **Experiment Ref:** EXP-007
- **Title:** Dynamic API Gateway Telemetry Simulator ("PulseEngine Sandbox")
- **Status:** COMPLETE
- **Prerequisite:** `02_plan.md` OKR Gate signed off
- **Task Contract Ref:** ICM Pipeline

---

## 1. Execution Summary
The standalone production-grade telemetry simulation dashboard "PulseEngine Sandbox" is implemented at `experiments/tasks/EXP-007/index.html`. It incorporates all five core architectural components:
1. **Interactive SVG/Canvas Topology:**
   - Ingress Gateway (`envoy-edge-01`) -> 3 Microservices (Auth, Billing, Catalog) -> InfluxDB Sink (`telemetry-lake-01`).
   - SVG cubic Bézier conduits (`link-ingress-auth`, `link-ingress-billing`, `link-ingress-catalog`, `link-auth-influx`, `link-billing-influx`, `link-catalog-influx`).
   - Dynamic packet pulse particle engine running on `requestAnimationFrame` spawning glowing data packets along SVG conduits.
   - Interactive hover cards detailing active connections, pods, error rates, and cluster topology.
2. **Real-time Metrics Panel:**
   - 800ms vanilla JS simulation loop (`tickIntervalMs: 800`).
   - Live p50, p95, and p99 latency percentiles with smooth Catmull-Rom / Bézier SVG curves and dynamic gradient area fills.
   - Real-time RPS counter, 5xx error rate tracker, and synthetic ingestion live tail table.
3. **Interactive Chaos Engine Toggle:**
   - Chaos toggle injecting latency slowdowns and 5xx HTTP gateway errors into upstream services.
   - Visual node state mutations: shifts affected nodes to amber/rose with animated pulsing glows.
   - Animated anomaly alert notification banner with dismiss capability.
4. **Accessible Threshold Configuration Modal:**
   - Accessible WAI-ARIA dialog (`role="dialog"`, `aria-modal="true"`, `aria-labelledby="modal-title"`, `aria-describedby="modal-desc"`).
   - Strict keyboard focus trap (Tab cycling between modal inputs and buttons).
   - Escape key dismisses modal and restores focus to triggering button.
   - Customizable p50, p95, and p99 threshold sliders with live updating value chips and reset to defaults.
5. **Responsive & Lightweight:**
   - Styled with Tailwind CSS CDN and custom theme extensions.
   - Zero external charting library dependencies.
   - Responsive across 375px mobile and 1440px desktop layouts.

---

## 2. Symbol Modification Ledger

| Symbol Name | Symbol Type | Target File | Description |
|---|---|---|---|
| `generateSmoothPath` | Function | `experiments/tasks/EXP-007/index.html` | Computes smoothed cubic Bezier path and area strings for SVG sparklines |
| `updateSparkline` | Function | `experiments/tasks/EXP-007/index.html` | Updates SVG path `d` attributes and trailing indicator dot coordinates |
| `simulationTick` | Function | `experiments/tasks/EXP-007/index.html` | 800ms periodic simulation loop updating metrics, nodes, logs, and pulses |
| `toggleChaos` | Function | `experiments/tasks/EXP-007/index.html` | Toggles chaos injection state, updates button ARIA and styles, reveals alert banner |
| `openModal` / `closeModal` | Function | `experiments/tasks/EXP-007/index.html` | Manages accessible dialog state, body scroll lock, and focus restoration |
| `getFocusableElements` | Function | `experiments/tasks/EXP-007/index.html` | Discovers interactive focusable elements for keyboard focus trapping |
| `spawnPacket` / `renderParticles` | Function | `experiments/tasks/EXP-007/index.html` | Generates and animates SVG packet pulses traversing conduit paths |

---

## 3. Exit Criteria & Transition Checklist
- [x] All planned code changes executed according to specification.
- [x] No syntax errors or unfinished placeholders remain.
- [x] Symbol modification ledger updated.
- [x] Ready for automated verification in `04_verify.md`.
