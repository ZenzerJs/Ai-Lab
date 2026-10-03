# Task Stage Contract: 02_plan

## Task Metadata
- **Task ID:** TSK-014
- **Title:** EXP-005 Full-Stack Marketing Landing Page
- **Status:** APPROVED
- **Date Created:** 2026-10-03
- **Owner:** Frontend Engineering Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Technical Architecture & Blueprint
The PulseEngine marketing landing page is architected as a modern, high-converting, single-page application built with semantic HTML5, utility-first Tailwind CSS (via CDN), and performant vanilla JavaScript.

### Component Architecture
1. **Header & Navigation (`<header>`):**
   - Fixed/Sticky top banner (`sticky top-0 z-50 backdrop-blur-md bg-[#090d16]/80`).
   - SVG Brand mark with glowing gradient badge and bold typography.
   - Desktop navigation list (`Features`, `Metrics`, `Pricing`) and primary "Get Started" CTA button.
   - Mobile hamburger button and collapsible responsive navigation drawer.

2. **Hero Section (`<section>`):**
   - High-contrast visual hierarchy with subtle background ambient gradients (`blur-[130px]`).
   - Value proposition headline emphasizing sub-millisecond API telemetry.
   - Dual action CTAs: Primary gradient button ("Start Free Trial") and secondary glassmorphic button ("Watch Interactive Demo").
   - 4-item social proof telemetry metrics grid (12.8B+ calls, <0.2ms overhead, 99.999% SLA, 3,400+ workspaces).

3. **Feature Capabilities Grid (`<section id="features">`):**
   - 3 feature cards highlighting core capabilities:
     * Card 1: Sub-Millisecond Ingestion (eBPF hooks, latency).
     * Card 2: Instant Bottleneck Triage (outlier clustering, p99 isolation).
     * Card 3: Automated SLA Shields (dynamic rate-limiting, anomaly alerts).
   - Handcrafted clean inline SVGs, distinct border accents, and micro-interaction hover transforms (`hover:-translate-y-1.5`, icon scale).

4. **Interactive Pricing Calculator (`<section id="pricing">`):**
   - Two plan tiers:
     * Starter: $29/mo (monthly) vs $23/mo (annual, 20% discount).
     * Professional: $99/mo (monthly) vs $79/mo (annual, 20% discount).
   - Accessible vanilla JavaScript toggle switch (`role="switch"`, `aria-checked`) dynamically updating DOM price values and discount calculation badges without page reload.

5. **Minimalist Footer (`<footer>`):**
   - Brand lockup with live status indicator (99.999% SLA operational).
   - Essential legal and navigation links.
   - Responsive flex layout adapting seamlessly from mobile vertical stack to desktop horizontal row.

---

## 2. Impacted Files Manifest
| Target File | Purpose | Edit Mode |
|---|---|---|
| `experiments/tasks/index.html` | Complete standalone landing page with Tailwind CDN & vanilla JS | Verified / Complete |
| `tasks/TSK-014/01_intake.md` | Intake stage contract | Created |
| `tasks/TSK-014/02_plan.md` | Planning stage contract & OKR matrix | Created |
| `tasks/TSK-014/03_exec.md` | Execution ledger & symbol tracking | Pending Stage 03 |
| `tasks/TSK-014/04_verify.md` | Verification checklist & automated test script | Pending Stage 04 |

---

## 3. OKR Acceptance Matrix
| Objective | Key Result | Verification Method | Status |
|---|---|---|---|
| **O1: Sticky Navigation** | Sticky header with logo, 3 nav links, primary CTA, mobile menu | DOM inspection & CSS assertion (`sticky top-0`) | MET |
| **O2: Hero & Proof** | Value prop, subheading, dual CTA buttons, 4 metric cards | Text node and link verification | MET |
| **O3: Feature Grid** | 3 capability cards with distinct SVG icons and hover micro-interactions | Element count & SVG presence verification | MET |
| **O4: Interactive Pricing** | Interactive toggle applying 20% discount to $29 and $99 tiers | JavaScript execution & DOM update validation | MET |
| **O5: Minimalist Footer** | Footer links, operational indicator, copyright string | Footer DOM node verification | MET |
| **O6: Responsive Design** | Viewport meta, Tailwind responsive breakpoints (`sm:`, `md:`, `lg:`) | Responsive class audits (375px to 1440px) | MET |

---

## 4. Exit Criteria & Stage Transition Checklist
- [x] Architecture blueprint fully specified.
- [x] OKR Acceptance Matrix defined with deterministic criteria.
- [x] File modification manifest confirmed.
- [x] Ready to transition to `03_exec.md`.
