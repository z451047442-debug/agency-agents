#!/usr/bin/env bash
#
# Validates depends_on references in agent frontmatter.
# Thin wrapper around analyze-deps.py (the canonical implementation).
#
# Usage: ./scripts/check-deps.sh [--manifest]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/analyze-deps.py"

if [[ ! -f "$PY_SCRIPT" ]]; then
  echo "ERROR: analyze-deps.py not found at $PY_SCRIPT" >&2
  exit 1
fi

MANIFEST_MODE=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest) MANIFEST_MODE=true; shift ;;
    --help|-h)
      echo "Usage: check-deps.sh [--manifest]"
      echo "  --manifest  Output depends_on.json manifest to stdout"
      echo ""
      echo "Thin wrapper around analyze-deps.py."
      echo "On Windows, run directly: python scripts/analyze-deps.py --validate"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 2 ;;
  esac
done

PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    PYTHON="$cmd"
    break
  fi
done

if [[ -z "$PYTHON" ]]; then
  echo "ERROR: python3 or python not found on PATH" >&2
  exit 1
fi

if $MANIFEST_MODE; then
  exec "$PYTHON" "$PY_SCRIPT" --validate --json
else
  exec "$PYTHON" "$PY_SCRIPT" --validate
fi
