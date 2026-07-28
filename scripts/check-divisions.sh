#!/usr/bin/env bash
#
# check-divisions.sh — enforce a single source of truth for the division set.
#
# divisions.json (repo root) is canonical. This script fails if any of the
# following disagree with it:
#   1. The actual top-level agent directories on disk
#   2. AGENT_DIRS in scripts/convert.sh
#   3. AGENT_DIRS in scripts/lint-agents.sh
#   4. The path filters in .github/workflows/lint-agents.yml
#   5. Every divisions.json entry has label, icon, and color
#
# Add a division: create its directory, add an entry to divisions.json, then
# this script tells you every other place that must be updated. No deps beyond
# bash 3.2 + coreutils (no jq) so it runs the same on macOS and CI.
#
# Usage: ./scripts/check-divisions.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

JSON="divisions.json"
[[ -f "$JSON" ]] || { echo "ERROR $JSON not found at repo root"; exit 1; }

# Fallback chain for cross-platform Python resolution (Python >= 3.9)
PYTHON=""
for py in python3 python; do
    if v=$("$py" -c "import sys; print(sys.version_info[:2] >= (3,9))" 2>/dev/null); then
        if [ "$v" = "True" ]; then PYTHON="$py"; break; fi
    fi
done
if [ -z "$PYTHON" ]; then
    echo "ERROR: Python >= 3.9 is required." >&2
    exit 2
fi
exec "$PYTHON" "$SCRIPT_DIR/check-divisions.py"
