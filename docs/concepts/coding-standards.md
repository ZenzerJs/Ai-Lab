---
type: standard
title: Coding Standards & Diff Protocol
description: Code conventions, typing invariants, error boundaries, and diff protocols.
status: active
verified: human-reviewed
sources:
  - https://github.com/GoogleCloudPlatform/open-knowledge-format
---

# Coding Standards & Diff Protocol

## 1. Code Style & Typing Invariants
- **Language Level**: Python 3.10+ and TypeScript 5.0+ are standard.
- **Type Annotations**: All function parameters, return values, and exported classes must carry explicit, static type annotations. No bare `Any` or untyped signatures in production interfaces.
- **Docstrings & Comments**: Code definitions must include concise docstrings documenting intent, inputs, return contracts, and potential exceptions.

## 2. Error Boundaries & Return Semantics
- Functions must avoid unhandled crashes or uncommunicative exceptions.
- CLI automation tools must propagate native process exit codes:
  - Exit code `0`: Successful execution.
  - Exit code `1` (or non-zero): Actionable, isolated failure message printed to stderr/stdout.

## 3. Search/Replace Diff Protocol
All modifications to existing files exceeding 50 lines must adhere to standard search/replace diff chunks:
```text
<<<<<<< SEARCH
// Original code lines with 2-3 lines of matching context
=======
// New replacement code lines
>>>>>>> REPLACE
```
Direct full-file rewrites on existing files require documented justification in the active task contract.

## 4. AST Navigation Invariant
Agents must utilize AST-based lookups (`ast-grep`, `scripts/repo_map.py`) to inspect interfaces rather than ingesting entire files.

Cross-references:
- [Architecture Overview](/concepts/architecture-overview.md)
- [Data Contracts](/schemas/data-contracts.md)
