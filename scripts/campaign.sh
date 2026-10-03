#!/usr/bin/env bash
# Cross-platform Shell shim for scripts/campaign.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/campaign.py" "$@"
