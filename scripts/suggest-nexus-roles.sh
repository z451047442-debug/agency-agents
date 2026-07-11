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
PY_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --category|-c)       PY_ARGS+=("--category" "$2"); shift 2 ;;
    --file|-f)           PY_ARGS+=("--file" "$2"); shift 2 ;;
    --min-confidence)    PY_ARGS+=("--min-confidence" "$2"); shift 2 ;;
    --help|-h)           exec python3 "$SCRIPT_DIR/suggest-nexus-roles.py" --help ;;
    *) shift ;;
  esac
done

exec python3 "$SCRIPT_DIR/suggest-nexus-roles.py" "${PY_ARGS[@]}"
