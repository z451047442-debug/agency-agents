#!/usr/bin/env bash
#
# generate-index.sh — thin wrapper around the canonical Python generator.
#
# Usage:
#   ./scripts/generate-index.sh [--check] [--out <path>]
#
# The Python implementation (scripts/generate-index.py) is the single source
# of truth for AGENTS.json. This wrapper exists only so the documented shell
# command keeps working on every platform.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON="$candidate"
    break
  fi
done
if [[ -z "$PYTHON" ]]; then
  echo "ERROR: Python 3 is required to generate AGENTS.json." >&2
  exit 1
fi

exec "$PYTHON" "$SCRIPT_DIR/generate-index.py" "$@"
