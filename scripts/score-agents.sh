#!/usr/bin/env bash
#
# Agent quality scoring — thin wrapper around canonical Python implementation.
#
# Usage:
#   ./scripts/score-agents.sh                          # all agents
#   ./scripts/score-agents.sh --category engineering   # one category
#   ./scripts/score-agents.sh --threshold 5            # CI gate
#   ./scripts/score-agents.sh --file path/to/agent.md  # single file

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Resolve Python path for cross-platform (Windows Git Bash / MSYS2)
resolve_path() {
  if command -v cygpath &>/dev/null; then
    cygpath -m "$1"
  else
    echo "$1"
  fi
}
PY_SCRIPT="$(resolve_path "$SCRIPT_DIR/score-agents.py")"

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
"$PYTHON" "$PY_SCRIPT" "$@"
exit $?
