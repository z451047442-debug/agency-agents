#!/usr/bin/env bash
#
# Run all quality checks: lint, deps, score, tests.
# Usage: ./scripts/quality.sh [--quick]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PYTHON=""
for cmd in python3 python; do
  command -v "$cmd" &>/dev/null && { PYTHON="$cmd"; break; }
done
[[ -z "$PYTHON" ]] && { echo "ERROR: python3/python not found" >&2; exit 1; }

QUICK=false
[[ "${1:-}" == "--quick" ]] && QUICK=true

PASS=0; FAIL=0

echo "=== Agency Quality Pipeline ==="

echo ""; echo "[1/4] Lint"
if "$PYTHON" "$SCRIPT_DIR/lint-agents.py" --all --no-freshness; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi

echo ""; echo "[2/4] Dependencies"
if bash "$SCRIPT_DIR/check-deps.sh"; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi

echo ""; echo "[3/4] Quality Score"
if "$PYTHON" "$SCRIPT_DIR/score-agents.py" > /dev/null 2>&1; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi

echo ""; echo "[4/4] Tests"
if "$PYTHON" -m pytest "$ROOT/tests/" -q; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi

echo ""; echo "=== Pipeline: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
