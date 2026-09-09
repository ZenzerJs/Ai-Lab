#!/usr/bin/env bash
# Cross-platform POSIX shell shim for dashboard/build_data.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/build_data.py" "$@"
