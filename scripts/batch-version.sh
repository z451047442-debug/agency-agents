#!/usr/bin/env bash
#
# Batch adds version: "1.0.0" to YAML frontmatter of agents that lack it.
#
# Usage:
#   ./scripts/batch-version.sh                          # all agents (interactive confirm)
#   ./scripts/batch-version.sh --category infrastructure  # one category
#   ./scripts/batch-version.sh --file path/to/agent.md    # single file
#   ./scripts/batch-version.sh --dry-run                  # preview only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --category|-c) PY_ARGS+=("--category" "$2"); shift 2 ;;
    --file|-f)     PY_ARGS+=("--file" "$2"); shift 2 ;;
    --dry-run|-n)  PY_ARGS+=("--dry-run"); shift ;;
    --help|-h)     exec python3 "$SCRIPT_DIR/batch-version.py" --help ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

exec python3 "$SCRIPT_DIR/batch-version.py" "${PY_ARGS[@]}"
