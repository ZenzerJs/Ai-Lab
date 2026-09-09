---
type: concept
title: System Topology & Execution Architecture
description: System topology, module boundaries, MCP layer, and execution rules.
status: active
verified: human-reviewed
sources:
  - https://github.com/GoogleCloudPlatform/open-knowledge-format
  - https://github.com/RinDig/Interpretable-Context-Methodology
---

# System Topology & Execution Architecture

## 1. Architectural Overview
The Antigravity workspace implements an agentic software engineering environment structured across four decoupled layers:
1. **Governance & Directives Layer (`.agents/rules/`, `AGENTS.md`)**: Defines non-negotiable operational invariants, tool usage constraints, and context lifecycle policies.
2. **Knowledge Base Layer (`docs/`)**: Conforms to the Google Cloud Open Knowledge Format (OKF v0.2), providing self-describing, human- and machine-readable architectural knowledge and schemas.
3. **Execution Pipeline Layer (`tasks/`)**: Follows the Interpretable Context Methodology (ICM) 5-stage contract model (`01_intake.md` through `05_retro.md`).
4. **Automation & Tooling Layer (`scripts/`, `.agents/mcp_config.json`)**: Provides cross-platform AST-based structural navigation, output filtration, and multi-root sandboxed MCP access.

## 2. Module Boundaries & Sandboxing
To protect project governance files and repository metadata, file access is segregated:
- **Sandbox Root Boundaries**: MCP filesystem servers mount only `./tasks`, `./src`, `./docs`, and `./scripts`.
- **Protected Paths**: Root configuration files (`.agents/`, `AGENTS.md`) and `.git/` are strictly isolated from agentic write access via MCP.
- **Application Source**: Net-new application logic lives strictly under `src/`.

## 3. Tool Coordination
Tool access is gated by stage lifecycle contracts:
- Architectural planning occurs in `02_plan.md` using sequential thinking (limited to 10 steps).
- Execution occurs in `03_exec.md` using surgical search/replace diff editing.
- Verification occurs in `04_verify.md` using test runner filters.

See [Coding Standards](/concepts/coding-standards.md) and [Data Contracts](/schemas/data-contracts.md) for detailed invariants.
Upstream specification tracking is cataloged in [Specification Versions](/SPEC-VERSIONS.md).
