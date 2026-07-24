#!/usr/bin/env bash
#
# clean.sh — Cleanup generated and temporary files for The Agency.
#
# Usage:
#   ./scripts/clean.sh                  # clean generated integrations (safe)
#   ./scripts/clean.sh --all            # deep clean (integrations + temp + pycache)
#   ./scripts/clean.sh --dry-run        # preview what would be deleted
#   ./scripts/clean.sh --all --dry-run  # preview deep clean
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

PY_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)       PY_ARGS+=("--all"); shift ;;
    --dry-run)   PY_ARGS+=("--dry-run"); shift ;;
    --help|-h)   exec "$PYTHON" "$SCRIPT_DIR/clean.py" --help ;;
    *)           echo "Unknown option: $1" >&2; exec "$PYTHON" "$SCRIPT_DIR/clean.py" --help ;;
  esac
done

exec "$PYTHON" "$SCRIPT_DIR/clean.py" "${PY_ARGS[@]}"
