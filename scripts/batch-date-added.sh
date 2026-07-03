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
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DRY_RUN=false
CATEGORY_FILTER=""
SINGLE_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --category|-c) CATEGORY_FILTER="$2"; shift 2 ;;
    --file|-f)     SINGLE_FILE="$2"; shift 2 ;;
    --dry-run)     DRY_RUN=true; shift ;;
    --help|-h)
      echo "Usage: batch-date-added.sh [--category name] [--file path] [--dry-run]"
      echo "Adds date_added frontmatter from git first-commit dates."
      exit 0 ;;
    *) shift ;;
  esac
done

# Collect files
files=()
if [[ -n "$SINGLE_FILE" ]]; then
  files=("$SINGLE_FILE")
elif [[ -n "$CATEGORY_FILTER" ]]; then
  cat_dir="$REPO_ROOT/$CATEGORY_FILTER"
  [[ -d "$cat_dir" ]] || { echo "ERROR: category not found: $CATEGORY_FILTER"; exit 1; }
  while IFS= read -r f; do files+=("$f"); done < <(find "$cat_dir" -maxdepth 2 -name "*.md" -type f | sort)
else
  source "$SCRIPT_DIR/_discover_dirs.sh"
  AGENT_DIRS=()
  while IFS= read -r d; do AGENT_DIRS+=("$d"); done < <(discover_agent_dirs)
  for dir in "${AGENT_DIRS[@]}"; do
    while IFS= read -r f; do files+=("$f"); done < <(find "$REPO_ROOT/$dir" -maxdepth 2 -name "*.md" -type f | sort)
  done
fi

count=0; skipped=0
for file in "${files[@]}"; do
  # Skip files that already have date_added
  if grep -q '^date_added:' "$file" 2>/dev/null; then
    skipped=$((skipped + 1)); continue
  fi

  # Get first commit date from git
  first_date=$(git -C "$REPO_ROOT" log --diff-filter=A --follow --format="%ad" --date=short -- "$file" 2>/dev/null | tail -1)
  [[ -z "$first_date" ]] && { skipped=$((skipped + 1)); continue; }

  # Insert date_added after version: (preferred) or after color:
  if grep -q '^version:' "$file" 2>/dev/null; then
    insert_after="version:"
  else
    insert_after="color:"
  fi
  insert_line_num=$(grep -n "^${insert_after}" "$file" | head -1 | cut -d: -f1)

  if $DRY_RUN; then
    echo "[DRY-RUN] $file → date_added: \"$first_date\""
  else
    sed -i "${insert_line_num}a date_added: \"$first_date\"" "$file"
    echo "$file → date_added: \"$first_date\""
  fi
  count=$((count + 1))
done

echo ""
echo "Updated: $count | Skipped: $skipped | Total: ${#files[@]}"
$DRY_RUN && echo "(dry-run — no files were changed)"
