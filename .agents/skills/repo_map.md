# Agent Skill: `repo_map`

## Overview
The `repo_map` skill extracts a high-density, AST-derived architectural map of code symbols (class declarations, function/method signatures, and docstrings) using `grep-ast` and enforces a strict token budget using `tiktoken` (`cl100k_base`).

## Token Margin Rule
Enforces an internal target of **1,800 tokens** to account for tokenizer variance between OpenAI BPE and Gemini tokenizers, guaranteeing that the emitted context strictly satisfies the <= 2,000 token limit in Antigravity.

## Usage

### Command Line
```bash
python scripts/repo_map.py [--target <path>] [--root <path>] [--max-tokens <int>]
```

### PowerShell Shim (Windows)
```powershell
.\scripts\repo_map.ps1 --target src\
```

### POSIX Shim (Linux / macOS)
```bash
./scripts/repo_map.sh --target src/
```

## Arguments
- `--target`: Target source file or directory to scan. Defaults to the repository root.
- `--root`: Root workspace path for relative path display. Defaults to `.`.
- `--max-tokens`: Target token budget (default: `1800`). Employs binary search pruning when extracted symbols exceed this budget.

## When to Use
- Stage `01_intake` and `02_plan` to inspect interfaces without ingesting whole files.
- Adhering to `.agents/rules/context-isolation.md` to prevent whole-file reads.
