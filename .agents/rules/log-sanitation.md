# Operational Rule: Log Sanitation & Terminal Output Filtration

## Core Mandate
Direct, un-sanitized dumps of terminal stdout and stderr into the conversation context are strictly forbidden. All automated tests, linters, and build executions MUST be invoked through `scripts/filter_output.py` (or its platform shims `filter_output.ps1` / `filter_output.sh`).

## Enforcement Protocol
1. **Command Invocation Pattern:**
   ```bash
   python scripts/filter_output.py -- <command> [args...]
   ```
2. **Success Behavior:**
   - On successful exit (code `0`), output is collapsed into a single deterministic summary line:
     `✓ Command succeeded: <command_string>`
3. **Failure Isolation:**
   - On error or test failure (non-zero exit code), voluminous noise (passing assertions, environment banners, deprecation warnings) is stripped.
   - Only the failing assertion, file path, line number, and immediate stack trace are preserved.
4. **Context Conservation:**
   - Prevents prompt cache churn and conversational flooding from multi-thousand-line compiler or test outputs.
