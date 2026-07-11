#!/usr/bin/env bash
#
# check-dupes.sh — Detect near-duplicate agents by name and description similarity.
#
# Reads AGENTS.json and uses Python difflib to compute string similarity
# ratios between all agent pairs.  Flags pairs above the similarity
# threshold as potential duplicates that merit manual review.
#
# Usage:
#   ./scripts/check-dupes.sh [--threshold 0.85] [--category <name>] [--help]
#
#   --threshold N   Similarity ratio above which to flag (default: 0.85; 0–1)
#   --category NAME  Only compare agents in this category
#   --help           Show this help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INDEX="$REPO_ROOT/AGENTS.json"

# --- defaults ---
THRESHOLD="0.85"
CATEGORY_FILTER=""

# --- helpers ---
usage() {
  sed -n '3,12p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

err() { echo "[ERR] $*" >&2; }

# --- main ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --threshold) THRESHOLD="$2"; shift 2 ;;
    --category)  CATEGORY_FILTER="$2"; shift 2 ;;
    --help|-h)   usage ;;
    *)           err "Unknown option: $1"; usage ;;
  esac
done

[[ -f "$INDEX" ]] || { err "AGENTS.json not found. Run: ./scripts/generate-index.sh"; exit 1; }

# Build Python args
ARGS=("--threshold" "$THRESHOLD")
[[ -n "$CATEGORY_FILTER" ]] && ARGS+=("--category" "$CATEGORY_FILTER")

exec python3 "$SCRIPT_DIR/check-dupes.py" "${ARGS[@]}"
