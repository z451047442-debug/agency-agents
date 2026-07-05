#!/usr/bin/env bash
#
# generate-index.sh — Scan all agent .md files and generate AGENTS.json.
#
# AGENTS.json is an auto-generated index. The sole manual source of truth is
# the .md files themselves.  This script reads YAML frontmatter from every
# agent file, derives metadata from file paths, and writes a sorted,
# formatted JSON index.
#
# Usage:
#   ./scripts/generate-index.sh [--check] [--out <path>]
#
#   --check     Exit 1 if the on-disk AGENTS.json differs from what would be
#               generated (used in CI to detect stale index).
#   --out       Write to a custom path (default: repo-root/AGENTS.json).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_FILE="$REPO_ROOT/AGENTS.json"
CHECK_MODE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      echo "Usage: generate-index.sh [--check] [--out PATH] [--help]"
      echo "Scans all agent .md files and regenerates AGENTS.json."
      exit 0
      ;;
    --check) CHECK_MODE=true; shift ;;
    --out)   OUT_FILE="${2:?'--out requires a value'}"; shift 2 ;;
    *)       echo "Unknown option: $1"; exit 2 ;;
  esac
done

TODAY="$(date +%Y-%m-%d)"

# ---- helpers ---------------------------------------------------------------

json_escape() {
  sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/\r//g'
}

get_field() {
  local field="$1" file="$2"
  awk -v f="$field" '
    /^---$/ { fm++; next }
    fm == 1 && $0 ~ "^" f ": " { sub("^" f ": ", ""); print; exit }
  ' "$file"
}

get_depends_on() {
  # Extract depends_on as a JSON array, or empty string if not present.
  # Handles both YAML list (- item) and inline array ([item1, item2]).
  local file="$1" field="$2"
  awk -v f="$field" '
    BEGIN { in_deps = 0; first = 1; pat = "^" f ":" }
    /^---$/ { fm++; next }
    fm >= 2 { exit }
    fm == 1 && $0 ~ pat {
      if ($0 ~ /\[/) {
        sub(pat "[[:space:]]*", "")
        gsub(/[\[\]]/, "")
        split($0, items, /,[[:space:]]*/)
        for (i in items) {
          gsub(/^[[:space:]]+|[[:space:]]+$/, "", items[i])
          printf "%s\"%s\"", (first ? "" : ","), items[i]
          first = 0
        }
        exit
      }
      in_deps = 1; next
    }
    in_deps && /^[[:space:]]*-[[:space:]]+/ {
      sub(/^[[:space:]]*-[[:space:]]+/, "")
      gsub(/^[[:space:]]+|[[:space:]]+$/, "")
      printf "%s\"%s\"", (first ? "" : ","), $0
      first = 0; next
    }
    in_deps && /^[a-z]/ { exit }
  ' "$file"
}

# ---- main ------------------------------------------------------------------

TMPFILE="$(mktemp)"
trap 'rm -f "$TMPFILE"' EXIT

cat > "$TMPFILE" <<HEREDOC
{"version":"1.0","generated":"${TODAY}","agents":[
HEREDOC

# Auto-discover agent directories (shared logic — see _discover_dirs.sh)
source "$SCRIPT_DIR/_discover_dirs.sh"
AGENT_DIRS=()
while IFS= read -r d; do
  AGENT_DIRS+=("$d")
done < <(discover_agent_dirs)

total=0
categories_set=""

for dname in "${AGENT_DIRS[@]}"; do
  dir="$REPO_ROOT/$dname"

  [[ -d "$dir" ]] || continue

  while IFS= read -r -d '' file; do
    first_line="$(head -1 "$file")"
    [[ "$first_line" == "---" ]] || continue

    name="$(get_field "name" "$file")"
    [[ -n "$name" ]] || continue

    description="$(get_field "description" "$file" | json_escape)"
    emoji="$(get_field "emoji" "$file" | json_escape)"

    # Derive fields from file path
    rel="${file#$REPO_ROOT/}"
    category="${dname}"
    filename="${rel##*/}"
    id="${filename%.md}"
    subpath="${rel#*/}"
    subdir="${subpath%"$filename"}"
    subdir="${subdir%/}"
    if [[ -n "$subdir" && "$subdir" != "$category" ]]; then
      subcategory="$subdir"
    else
      subcategory=""
    fi
    subcategory="$(echo "$subcategory" | json_escape)"

    depends_on_json="$(get_depends_on "$file" "depends_on")"
    nexus_roles_json="$(get_depends_on "$file" "nexus_roles")"

    # Build optional fields
    extra_fields=""
    if [[ -n "$depends_on_json" ]]; then
      extra_fields="${extra_fields},\"depends_on\":[${depends_on_json}]"
    fi
    if [[ -n "$nexus_roles_json" ]]; then
      extra_fields="${extra_fields},\"nexus_roles\":[${nexus_roles_json}]"
    fi

    printf -v entry '{"id":"%s","name":"%s","description":"%s","emoji":"%s","category":"%s","subcategory":"%s","path":"%s"%s},\n' \
      "$id" "$name" "$description" "$emoji" "$category" "$subcategory" "$rel" "$extra_fields"

    printf '%s' "$entry" >> "$TMPFILE"
    total=$((total + 1))
    categories_set+="$category"$'\n'
  done < <(find "$dir" -name '*.md' -type f -print0 | sort -z)
done

unique_categories=$(echo "$categories_set" | sort -u | wc -l | tr -d ' ')

# Remove trailing comma from last agent entry, then close JSON
sed -i '$ s/,$//' "$TMPFILE"

cat >> "$TMPFILE" <<HEREDOC
],"total_categories":${unique_categories},"total_agents":${total}}
HEREDOC

# ---- output ----------------------------------------------------------------

if $CHECK_MODE; then
  if [[ ! -f "$OUT_FILE" ]]; then
    echo "ERROR: $OUT_FILE does not exist. Run scripts/generate-index.sh first."
    exit 1
  fi
  if diff -q "$TMPFILE" "$OUT_FILE" >/dev/null 2>&1; then
    echo "OK: AGENTS.json is up to date ($total agents, $unique_categories categories)."
    exit 0
  else
    echo "ERROR: AGENTS.json is stale. Run scripts/generate-index.sh and commit the result."
    echo ""
    echo "Diff (expected vs actual):"
    diff "$TMPFILE" "$OUT_FILE" || true
    exit 1
  fi
fi

mv "$TMPFILE" "$OUT_FILE"
echo "Generated $OUT_FILE ($total agents, $unique_categories categories)."
