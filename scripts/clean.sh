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
PY_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)       PY_ARGS+=("--all"); shift ;;
    --dry-run)   PY_ARGS+=("--dry-run"); shift ;;
    --help|-h)   exec python3 "$SCRIPT_DIR/clean.py" --help ;;
    *)           echo "Unknown option: $1" >&2; exec python3 "$SCRIPT_DIR/clean.py" --help ;;
  esac
done

exec python3 "$SCRIPT_DIR/clean.py" "${PY_ARGS[@]}"
