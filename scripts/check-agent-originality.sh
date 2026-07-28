#!/usr/bin/env bash
#
# check-agent-originality.sh — Flag agent files that substantially duplicate
# an existing agent (or another agent in the same change set).
#
# Why: a new agent should be genuinely new. Find-replace "re-skins" of an
# existing agent (e.g. swapping a country/platform name) are easy to miss in
# review because they're mergeable and well-formed — but they bloat the
# library with duplicates. This compares each candidate against the whole
# existing roster using entity-neutralized 8-word shingle overlap, so a
# swapped proper noun can't hide the copy.
#
# Usage:
#   ./scripts/check-agent-originality.sh [file ...]
#     With files: checks those agent .md files (used by CI on changed files).
#     With no args: checks every agent in the repo against every other (audit).
#
# Exit status:
#   0  all candidates below the FAIL threshold
#   1  at least one candidate at/above FAIL threshold (likely duplicate)
#
# Tunables (env):
#   ORIGINALITY_FAIL   default 40  — at/above this %, treated as a duplicate (exit 1)
#   ORIGINALITY_WARN   default 20  — at/above this %, surfaced as a warning (no fail)
#
# Calibration: across the existing 184-agent library the worst same-pair
# similarity is ~1.5% (median 0%). Anything in the double digits is a strong
# anomaly; the defaults leave a wide safety margin against false positives.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

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

ORIGINALITY_FAIL="${ORIGINALITY_FAIL:-40}" \
ORIGINALITY_WARN="${ORIGINALITY_WARN:-20}" \
exec "$PYTHON" "$SCRIPT_DIR/check-agent-originality.py" \
    --fail-threshold "$ORIGINALITY_FAIL" \
    --warn-threshold "$ORIGINALITY_WARN" \
    "$@"
