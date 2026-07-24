#!/usr/bin/env bash
#
# suggest-nexus-roles.sh — Propose nexus_roles for agents based on content analysis.
#
# Scans each agent's body for phase-related keywords and suggests which
# NEXUS pipeline phases the agent should participate in.
#
# Usage:
#   ./scripts/suggest-nexus-roles.sh [--category name] [--file path] [--min-confidence N]
#
#   --category name       Only analyze one category
#   --file path           Analyze a single agent file
#   --min-confidence N    Minimum keyword match count to suggest (default: 2)
#   --apply               Write suggestions into agent files (prompts for confirmation)

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
    --category|-c)       PY_ARGS+=("--category" "$2"); shift 2 ;;
    --file|-f)           PY_ARGS+=("--file" "$2"); shift 2 ;;
    --min-confidence)    PY_ARGS+=("--min-confidence" "$2"); shift 2 ;;
    --apply)             PY_ARGS+=("--apply"); shift ;;
    --help|-h)           exec "$PYTHON" "$SCRIPT_DIR/suggest-nexus-roles.py" --help ;;
    *)                   echo "Unknown option: $1" >&2; shift ;;
  esac
done

exec "$PYTHON" "$SCRIPT_DIR/suggest-nexus-roles.py" "${PY_ARGS[@]}"
