---
type: standard
title: Upstream Specification Versions & Commit Pins
description: Upstream commit pins, dates, and version tracking for OKF v0.2 and ICM.
status: active
verified: human-reviewed
sources:
  - https://github.com/GoogleCloudPlatform/open-knowledge-format
  - https://github.com/RinDig/Interpretable-Context-Methodology
---

# Upstream Specification Versions & Commit Pins

This document records the exact upstream specification pins, commit SHAs, dates, and declared versions for the core methodologies governing the Antigravity workspace.

---

## 1. Google Cloud Open Knowledge Format (OKF)

- **Declared Spec Version:** `okf_version: "0.2"`
- **Upstream Repository:** `https://github.com/GoogleCloudPlatform/open-knowledge-format.git`
- **Pinned Commit SHA (HEAD):** `ad30107c31c06aec8a7d5636e0d1058118604e6f`
- **Commit Date:** `2026-08-21T20:08:36Z`
- **Reference Stable Commit:** `0b87c52`
- **Bundle Invariants:**
  - Strict lowercase bundle root `index.md` carrying exclusively `okf_version: "0.2"` in frontmatter.
  - Strict lowercase chronological change log `log.md`.
  - Required `type` field in all content documents.
  - Standard vocabulary for metadata (`title`, `description`, `status`, `verified`, `sources`, `stale_after`).
  - Absolute bundle-relative links (`/concepts/...`, `/schemas/...`).

---

## 2. Interpretable Context Methodology (ICM)

- **Specification Framework:** Interpretable Context Methodology (ICM)
- **Upstream Repository:** `https://github.com/RinDig/Interpretable-Context-Methodology.git`
- **Reference Commit SHA:** `02ba5d85c7871b75c7c702a2d8da6524723d53d4`
- **Commit Date:** `2026-07-25T16:17:00Z`
- **Variant:** Numbered stage-contract lifecycle pipeline
  - Stage 1: `01_intake.md` (Scope, constraints, per-stage token budgets)
  - Stage 2: `02_plan.md` (Technical plan, impacted files, OKR matrix)
  - Stage 3: `03_exec.md` (Search/replace diff ledger, symbol changes)
  - Stage 4: `04_verify.md` (Automated verification outputs, token telemetry)
  - Stage 5: `05_retro.md` (Knowledge propagation to `docs/` and `docs/log.md`)
