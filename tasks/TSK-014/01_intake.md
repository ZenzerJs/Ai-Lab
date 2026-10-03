# Task Stage Contract: 01_intake

## Task Metadata
- **Task ID:** TSK-014
- **Title:** EXP-005 Full-Stack Marketing Landing Page
- **Status:** APPROVED
- **Date Created:** 2026-10-03
- **Owner:** Frontend Engineering Agent
- **Task Contract Ref:** ICM Pipeline

---

## 1. Problem Statement & Objectives
The workspace requires a complete, responsive marketing landing page for an API analytics SaaS named "PulseEngine". The implementation must be self-contained in `index.html` using Tailwind CSS CDN and vanilla JavaScript.

Key Functional Requirements:
1. **Sticky Navbar:** Modern sticky navigation bar with PulseEngine logo/branding, 3 navigation links (`Features`, `Metrics`, `Pricing`), and a "Get Started" primary action button.
2. **Hero Section:** Bold value proposition, explanatory subheading, dual CTA buttons ("Start Free Trial", "Book Live Demo"), and social proof metric badges (e.g. latency, events tracked, enterprise uptime).
3. **Feature Grid:** 3 feature cards highlighting core capabilities (Sub-millisecond latency tracking, Distributed tracing & root cause analysis, Automated anomaly alerts) with clean SVG icons, distinct borders, and micro-interactions/hover effects.
4. **Interactive Pricing Switch:** Interactive Monthly / Annual pricing switch with two plan tiers:
   - Starter Tier: $29/mo (Monthly) vs $23/mo (Annual with 20% discount applied via vanilla JavaScript, $276/yr).
   - Pro Tier: $99/mo (Monthly) vs $79/mo (Annual with 20% discount applied via vanilla JavaScript, $948/yr).
5. **Clean Minimalist Footer:** Links, branding, operational status badge, and copyright notice.
6. **Responsive Design:** Fully responsive layout with mobile navigation support catering from 375px mobile viewport to 1440px+ desktop viewport.

---

## 2. Scope Boundaries
The following files and components are within boundary:
- `experiments/tasks/index.html`: Standalone landing page with Tailwind CSS CDN and inline vanilla JavaScript.
- `tasks/TSK-014/`: Stage contracts (`01_intake.md`, `02_plan.md`, `03_exec.md`, `04_verify.md`).

---

## 3. Out-of-Scope Declarations
- External backend server APIs or database connections.
- Bundler/build-step frameworks (e.g. React, Next.js, Vite); must remain a standalone static HTML file.
- Changes to unrelated experiment files or tasks.

---

## 4. Technical Constraints & Invariants
- **Format:** Standalone single-file HTML document (`index.html`).
- **Styling:** Tailwind CSS CDN (`https://cdn.tailwindcss.com`) with custom theme extensions.
- **Interactivity:** Vanilla JavaScript for pricing discount recalculation and mobile drawer navigation.
- **Responsiveness:** Validated for 375px (mobile) and 1440px (desktop) layouts.

---

## 5. Token Budget Allocation
- **System & Rules:** 1,500 tokens
- **Active Task Contract:** 1,500 tokens
- **File Workspace:** 3,500 tokens
- **Margin Headroom:** 1,500 tokens
- **Total Turn Budget:** 8,000 tokens

---

## 6. Exit Criteria & Stage Transition Checklist
- [x] Functional requirements mapped and verified against user specification.
- [x] Scope boundaries and out-of-scope boundaries defined.
- [x] Constraints identified (standalone `index.html`, Tailwind CDN, vanilla JS).
- [x] Transition to `02_plan.md` authorized.
