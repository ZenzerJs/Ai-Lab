---
task_id: EXP-007
model: gemini-3.8-flash
model_baseline: gemini-3.8-flash
model_icm: gemini-3.8-flash
runs_per_arm: 1
target_repo: .
---
# EXP-007: Dynamic API Gateway Telemetry Simulator

Build a production-grade, interactive single-page simulation dashboard named "PulseEngine Sandbox":
1. Interactive SVG/Canvas node topology (Ingress -> 3 Services -> Influx Sink) with animated traffic pulses.
2. Real-time metrics panel: Live p50, p95, p99 latency sparklines updated every 800ms via vanilla JS ticker.
3. Interactive Chaos Engine toggle: Injects latency and 5xx errors, turning affected nodes amber/red and firing an alert banner.
4. Threshold configuration modal/drawer built according to accessible dialog patterns (ESC to dismiss, focus lock).
5. Responsive layout across 375px mobile and 1440px desktop.

Output constraints: Standalone HTML file utilizing Tailwind CSS CDN. Zero bloated external charting libraries (use bespoke SVG curves).
