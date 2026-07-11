#!/usr/bin/env bash
#
# batch-date-added.sh — Bulk-add date_added frontmatter from git history.
#
# For each agent .md file without a date_added field, looks up the first git
# commit that introduced the file and inserts date_added: "YYYY-MM-DD" after
# the version: line (or after color: if no version exists).
#
# Usage:
#   ./scripts/batch-date-added.sh [--category name] [--file path] [--dry-run]
#
#   --category name   Only process agents in one category
#   --file path       Process a single agent file
#   --dry-run         Print what would be changed without writing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --category|-c) PY_ARGS+=("--category" "$2"); shift 2 ;;
    --file|-f)     PY_ARGS+=("--file" "$2"); shift 2 ;;
    --dry-run)     PY_ARGS+=("--dry-run"); shift ;;
    --help|-h)     exec python3 "$SCRIPT_DIR/batch-date-added.py" --help ;;
    *) shift ;;
  esac
done

exec python3 "$SCRIPT_DIR/batch-date-added.py" "${PY_ARGS[@]}"
