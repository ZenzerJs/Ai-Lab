#!/usr/bin/env bash
# Cross-platform POSIX shell shim for scripts/run_experiment.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/run_experiment.py" "$@"
