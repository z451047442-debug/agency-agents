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
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DRY_RUN=false
CATEGORY_FILTER=""
SINGLE_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --category|-c)
      CATEGORY_FILTER="$2"
      shift 2
      ;;
    --file|-f)
      SINGLE_FILE="$2"
      shift 2
      ;;
    --dry-run|-n)
      DRY_RUN=true
      shift
      ;;
    --help|-h)
      echo "Usage: batch-version.sh [--category name] [--file path] [--dry-run]"
      echo ""
      echo "Adds version: \"1.0.0\" to agent YAML frontmatter that lacks it."
      echo ""
      echo "Options:"
      echo "  --category, -c   Process only one category directory"
      echo "  --file, -f       Process a single agent .md file"
      echo "  --dry-run, -n    Preview changes without applying"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

VERSION_STRING='version: "1.0.0"'

echo "=== Batch Version Tool ==="
if $DRY_RUN; then
  echo "Dry run: scanning agents..."
else
  echo "Scanning agents..."
fi
echo ""

# ---- Collect files ----
files=()

if [[ -n "$SINGLE_FILE" ]]; then
  # Single file mode
  abs_file="$SINGLE_FILE"
  # Make absolute if relative
  if [[ "$abs_file" != /* ]]; then
    abs_file="$REPO_ROOT/$abs_file"
  fi
  if [[ ! -f "$abs_file" ]]; then
    echo "ERROR: file not found: $abs_file"
    exit 1
  fi
  files+=("$abs_file")
elif [[ -n "$CATEGORY_FILTER" ]]; then
  # Category mode
  cat_dir="$REPO_ROOT/$CATEGORY_FILTER"
  if [[ ! -d "$cat_dir" ]]; then
    echo "ERROR: category directory not found: $cat_dir"
    exit 1
  fi
  while IFS= read -r f; do
    files+=("$f")
  done < <(find "$cat_dir" -maxdepth 2 -name "*.md" -type f 2>/dev/null | sort)
else
  # All agent directories — use shared dynamic discovery
  source "$SCRIPT_DIR/_discover_dirs.sh"
  AGENT_DIRS=()
  while IFS= read -r d; do
    AGENT_DIRS+=("$d")
  done < <(discover_agent_dirs)
  for dir in "${AGENT_DIRS[@]}"; do
    while IFS= read -r f; do
      files+=("$f")
    done < <(find "$REPO_ROOT/$dir" -maxdepth 2 -name "*.md" -type f 2>/dev/null | sort)
  done
fi

if [[ ${#files[@]} -eq 0 ]]; then
  echo "No agent files found."
  exit 0
fi

# ---- Process files ----
total_checked=0
total_has_version=0
total_needs_version=0
total_updated=0
total_errors=0
samples=()
error_files=()

for file in "${files[@]}"; do
  total_checked=$((total_checked + 1))
  rel_path="${file#$REPO_ROOT/}"

  # Check frontmatter exists
  first_line=$(head -1 "$file")
  if [[ "$first_line" != "---" ]]; then
    total_errors=$((total_errors + 1))
    error_files+=("${rel_path}: missing frontmatter")
    continue
  fi

  # Extract frontmatter
  frontmatter=$(awk 'NR==1{next} /^---$/{exit} {print}' "$file")

  # Check if version: already exists in frontmatter
  if echo "$frontmatter" | grep -qE '^version:'; then
    total_has_version=$((total_has_version + 1))
    continue
  fi

  total_needs_version=$((total_needs_version + 1))

  # Check that color: exists (we need it for insertion point)
  if ! echo "$frontmatter" | grep -qE '^color:'; then
    total_errors=$((total_errors + 1))
    error_files+=("${rel_path}: no color: field to anchor version insertion")
    continue
  fi

  # Save sample for reporting (up to 5)
  if [[ ${#samples[@]} -lt 5 ]]; then
    samples+=("$rel_path")
  fi

  # Apply if not dry run
  if $DRY_RUN; then
    continue
  fi

  # Insert version: "1.0.0" after the color: line in the frontmatter
  # We use awk to:
  #   1. Track when we're inside the YAML frontmatter
  #   2. When we find the color: line, print it and then insert version
  #   3. Print everything else as-is
  tmpfile=$(mktemp)
  if awk -v ver="$VERSION_STRING" '
    BEGIN { in_fm = 0; fm_done = 0; inserted = 0 }
    NR == 1 && /^---$/ { in_fm = 1; print; next }
    in_fm && !fm_done && /^---$/ { print; in_fm = 0; fm_done = 1; next }
    in_fm && !inserted && /^color:/ { print; print ver; inserted = 1; next }
    { print }
  ' "$file" > "$tmpfile" 2>/dev/null; then
    # Verify the file was written correctly
    if [[ -s "$tmpfile" ]]; then
      cp "$tmpfile" "$file"
      total_updated=$((total_updated + 1))
    else
      total_errors=$((total_errors + 1))
      error_files+=("${rel_path}: write produced empty file")
    fi
  else
    total_errors=$((total_errors + 1))
    error_files+=("${rel_path}: awk processing failed")
  fi
  rm -f "$tmpfile"
done

# ---- Report ----
if [[ -n "$CATEGORY_FILTER" ]]; then
  echo "  ${total_checked} agents in ${CATEGORY_FILTER}/"
elif [[ -n "$SINGLE_FILE" ]]; then
  echo "  1 file specified"
else
  echo "  ${total_checked} agents across all categories"
fi

echo "  ${total_has_version} already have version"
echo "  ${total_needs_version} will be updated with ${VERSION_STRING}"
echo ""

if [[ ${#samples[@]} -gt 0 ]]; then
  echo "  Sample changes:"
  for s in "${samples[@]}"; do
    echo "    ${s}"
    echo "    + ${VERSION_STRING}"
  done
  echo ""
fi

if [[ "$total_errors" -gt 0 ]]; then
  echo "  Errors:"
  for e in "${error_files[@]}"; do
    echo "    ${e}"
  done
  echo ""
fi

if $DRY_RUN; then
  echo "Run without --dry-run to apply."
  if [[ -z "$SINGLE_FILE" && -z "$CATEGORY_FILTER" ]]; then
    echo ""
    echo "Tip: Use --category <name> to process one category at a time."
  fi
else
  if [[ "$total_updated" -gt 0 ]]; then
    echo "═══ ${total_updated} files updated"
    echo ""
    echo "Done. Run './scripts/generate-index.sh' to refresh AGENTS.json."
  elif [[ "$total_needs_version" -eq 0 ]]; then
    echo "═══ All agents already have version fields. Nothing to do."
  else
    echo "═══ No changes applied (${total_errors} errors)"
  fi
fi

if [[ "$total_errors" -gt 0 ]]; then
  exit 1
fi
exit 0
