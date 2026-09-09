---
type: schema
title: Domain Interfaces & Data Contracts
description: Domain interfaces, API schemas, and data persistence contracts.
status: active
verified: human-reviewed
sources:
  - https://github.com/GoogleCloudPlatform/open-knowledge-format
---

# Domain Interfaces & Data Contracts

## 1. Scope
This document specifies domain schema contracts, stage contract schemas, and persistence models used across tasks and agentic sessions.

## 2. Stage Contract Data Schemas
Every task directory in `tasks/TSK-XXX` persists its lifecycle state through markdown contracts conforming to the following schemas:

### Intake Contract (`01_intake.md`)
- `Scope Boundaries`: Explicit list of included systems.
- `Out of Scope`: Explicit list of excluded modifications.
- `Token Budget Table`: Fixed allocation enforcing <= 8,000 total active tokens.

### Plan Contract (`02_plan.md`)
- `Impacted Files Manifest`: Table of paths, actions (`CREATE`, `MODIFY`, `DELETE`), and justification.
- `OKR Acceptance Matrix`: Objective, measurable Key Results, and automated test commands.

### Execution Contract (`03_exec.md`)
- `Change Ledger`: Applied search/replace chunks.
- `Symbol Ledger`: Modified symbols (classes, functions).
- `Escape Hatch Log`: Documented rationales for any full-file overwrites.

### Verification Contract (`04_verify.md`)
- `Automated Test Results`: Test run summaries from `scripts/filter_output.py`.
- `Token Telemetry Ledger`: Per-stage input/output token measurements.

### Retrospective Contract (`05_retro.md`)
- `Knowledge Ingestion Log`: Entries pushed to `docs/` and `docs/log.md`.

Cross-references:
- [Architecture Overview](/concepts/architecture-overview.md)
- [Coding Standards](/concepts/coding-standards.md)
