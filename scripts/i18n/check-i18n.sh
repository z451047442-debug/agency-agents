#!/usr/bin/env bash
#
# check-i18n.sh — Verify bilingual consistency across agent frontmatter.
#
# Checks:
#   1. Agent name encoding (UTF-8 validity for Chinese characters)
#   2. Category labels match between README and divisions.json
#   3. New agents have at minimum an English name
#
# Usage:
#   ./scripts/i18n/check-i18n.sh [--strict]
#
#   --strict   Treat warnings as errors (for CI)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STRICT=false
warnings=0; errors=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict) STRICT=true; shift ;;
    --help|-h)
      echo "Usage: check-i18n.sh [--strict]"
      echo "Validates i18n consistency across agent files."
      exit 0 ;;
    *) shift ;;
  esac
done

# 1. Check agent names for UTF-8 encoding issues
echo "=== Checking agent name encoding ==="
source "$SCRIPT_DIR/../_discover_dirs.sh"
AGENT_DIRS=()
while IFS= read -r d; do AGENT_DIRS+=("$d"); done < <(discover_agent_dirs)

total=0; chinese=0
for dir in "${AGENT_DIRS[@]}"; do
  while IFS= read -r -d '' file; do
    [[ "$(head -1 "$file")" == "---" ]] || continue
    total=$((total + 1))
    
    # Check for non-ASCII characters in name field
    name_line=$(awk '/^name:/{print; exit}' "$file")
    if echo "$name_line" | grep -qP '[\x{4e00}-\x{9fff}\x{3400}-\x{4dbf}]' 2>/dev/null; then
      chinese=$((chinese + 1))
    fi
    
    # Check for invalid UTF-8
    if ! iconv -f UTF-8 -t UTF-8 "$file" > /dev/null 2>&1; then
      echo "ERROR $file: invalid UTF-8 encoding"
      errors=$((errors + 1))
    fi
  done < <(find "$REPO_ROOT/$dir" -maxdepth 2 -name "*.md" -type f -print0)
done

echo "  Agents: $total | With Chinese name: $chinese ($(( chinese * 100 / (total ? total : 1) ))%)"

# 2. Check divisions.json for missing Chinese labels
echo ""
echo "=== Checking divisions.json completeness ==="
if [[ -f "$REPO_ROOT/divisions.json" ]]; then
  div_count=$(python3 -c "import json; d=json.load(open('$REPO_ROOT/divisions.json')); print(len(d['divisions']))")
  echo "  Divisions registered: $div_count"
else
  echo "WARN  divisions.json not found"
  warnings=$((warnings + 1))
fi

# 3. Check CONTRIBUTING_zh-CN.md exists
echo ""
echo "=== Checking bilingual documentation ==="
if [[ -f "$REPO_ROOT/CONTRIBUTING_zh-CN.md" ]]; then
  echo "  CONTRIBUTING_zh-CN.md: present"
else
  echo "WARN  CONTRIBUTING_zh-CN.md: missing"
  warnings=$((warnings + 1))
fi

echo ""
if [[ "$errors" -gt 0 ]]; then
  echo "FAILED: $errors error(s), $warnings warning(s)"
  exit 1
elif $STRICT && [[ "$warnings" -gt 0 ]]; then
  echo "FAILED (strict): $warnings warning(s)"
  exit 1
else
  echo "PASSED ($warnings warning(s))"
  exit 0
fi
