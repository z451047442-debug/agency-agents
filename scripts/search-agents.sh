#!/usr/bin/env bash
# Search The Agency's agents by keyword, category, or list all.
# Usage: ./scripts/search-agents.sh [query] [--category name] [--list-categories] [--stats] [--page N] [--per-page N]
# Wraps canonical Python implementation at scripts/search-agents.py.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Resolve Python 3 interpreter (python3 on Linux/macOS, python on Windows).
PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" 2>/dev/null; then
      PYTHON="$candidate"
      break
    fi
  fi
done
if [ -z "$PYTHON" ]; then
  echo "ERROR: Python 3.9+ required. Install from https://python.org." >&2
  exit 1
fi

PY_SCRIPT="$SCRIPT_DIR/search-agents.py"
exec "$PYTHON" "$PY_SCRIPT" "$@"
