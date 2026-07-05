#!/usr/bin/env bash
#
# lint-agents.sh — Thin wrapper around scripts/lint-agents.py (the canonical implementation).
#
# DEPRECATED: This script is maintained for backwards compatibility with existing
# CI workflows and pre-existing user muscle memory.  All new development should
# target scripts/lint-agents.py directly.  This wrapper will be removed in a
# future major version.
#
# Usage (same as lint-agents.py):
#   ./scripts/lint-agents.sh [file ...]
#   ./scripts/lint-agents.sh --all
#   ./scripts/lint-agents.sh --all --no-freshness

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/lint-agents.py"

# Resolve Python 3 interpreter (python3 on Linux/macOS, python on Windows).
# We must actually execute a test — the Windows Store stub "python3.exe" is
# findable but cannot run anything (exits 49 without output).
PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" &>/dev/null \
     && "$candidate" -c "import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)" 2>/dev/null; then
    PYTHON="$candidate"
    break
  fi
done

if [[ -z "$PYTHON" ]]; then
  echo "ERROR: Python 3 is required but not found on PATH." >&2
  echo "Install Python 3.9+ from https://python.org or your package manager." >&2
  exit 1
fi

exec "$PYTHON" "$PY_SCRIPT" "$@"
