#!/usr/bin/env bash
#
# Validates agent markdown files:
#   1. YAML frontmatter: name, description, emoji, color (ERROR)
#   2. Required sections: Identity, Mission, Rules, Deliverables, Workflow (WARN)
#   3. Meaningful content (>100 words) and file <10KB (WARN)
#   4. SOUL/AGENTS header coverage for convert.sh compatibility (WARN)
#   5. Optional fields: nexus_roles phase values, depends_on emptiness (WARN/INFO)
#
# Usage: ./scripts/lint-agents.sh [file ...]
#   If no files given, auto-discovers all categories and scans all agents.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# Auto-discover agent directories (shared logic — see _discover_dirs.sh)
source "$SCRIPT_DIR/_discover_dirs.sh"
AGENT_DIRS=()
while IFS= read -r d; do
  AGENT_DIRS+=("$d")
done < <(discover_agent_dirs)

REQUIRED_FRONTMATTER=("name" "description" "emoji" "color")
RECOMMENDED_SECTIONS=("Identity" "Core Mission" "Critical Rules" "Deliverable" "Workflow" "Success Metrics")

errors=0
warnings=0
short_files=0

classify_header_target() {
  local header_lower="$1"
  if [[ "$header_lower" =~ identity ]] ||
     [[ "$header_lower" =~ learning.*memory ]] ||
     [[ "$header_lower" =~ communication ]] ||
     [[ "$header_lower" =~ style ]] ||
     [[ "$header_lower" =~ critical.rule ]] ||
     [[ "$header_lower" =~ rules.you.must.follow ]]; then
    printf 'soul'
  else
    printf 'agents'
  fi
}

lint_file() {
  local file="$1"

  if [[ ! -f "$file" ]]; then
    echo "ERROR $file: not a file"
    errors=$((errors + 1))
    return
  fi

  # 0. Reject CRLF line endings (repo standard is LF — see .gitattributes).
  # A trailing \r otherwise makes the frontmatter check below fail with a
  # confusing "missing frontmatter ---" even when the file clearly starts ---.
  if LC_ALL=C grep -q $'\r' "$file"; then
    echo "ERROR $file: CRLF line endings detected — convert to LF (e.g. 'perl -i -pe \"s/\\r\$//\" $file'); repo uses LF per .gitattributes"
    errors=$((errors + 1))
    return
  fi

  # 1. Check frontmatter delimiters
  local first_line
  first_line=$(head -1 "$file")
  if [[ "$first_line" != "---" ]]; then
    echo "ERROR $file: missing frontmatter ---"
    errors=$((errors + 1))
    return
  fi

  # Extract frontmatter
  local frontmatter
  frontmatter=$(awk 'NR==1{next} /^---$/{exit} {print}' "$file")

  if [[ -z "$frontmatter" ]]; then
    echo "ERROR $file: empty frontmatter"
    errors=$((errors + 1))
    return
  fi

  # 2. Check required frontmatter fields
  for field in "${REQUIRED_FRONTMATTER[@]}"; do
    if ! echo "$frontmatter" | grep -qE "^${field}:"; then
      echo "ERROR $file: missing frontmatter '${field}'"
      errors=$((errors + 1))
    fi
  done

  # 3. Check recommended sections (warn only)
  local body
  body=$(awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$file")

  for section in "${RECOMMENDED_SECTIONS[@]}"; do
    if ! echo "$body" | grep -qi "$section"; then
      echo "WARN  $file: missing section '${section}'"
      warnings=$((warnings + 1))
    fi
  done

  # 4. Check word count
  local word_count
  word_count=$(echo "$body" | wc -w | awk '{print $1}')
  if [[ "${word_count:-0}" -lt 100 ]]; then
    echo "WARN  $file: content too short (< 100 words, got ${word_count:-0})"
    short_files=$((short_files + 1))
    warnings=$((warnings + 1))
  fi

  # 5. Optional frontmatter fields (INFO only — not required, but validate shape if present)
  local nexus_roles
  nexus_roles=$(echo "$frontmatter" | awk '/^nexus_roles:/{flag=1; next} flag && /^  - /{print; next} flag && !/^  /{exit}')
  if [[ -n "$nexus_roles" ]]; then
    local valid_phases="phase-0-discovery phase-1-strategy phase-2-foundation phase-3-build phase-4-hardening phase-5-launch phase-6-operate"
    while IFS= read -r role_line; do
      local role_val
      role_val=$(echo "$role_line" | sed 's/^  - //' | sed 's/^"//;s/"$//')
      if [[ -n "$role_val" ]] && ! echo "$valid_phases" | grep -qw "$role_val"; then
        echo "WARN  $file: unknown nexus_roles value '${role_val}'. Valid: ${valid_phases// /, }"
        warnings=$((warnings + 1))
      fi
    done <<< "$nexus_roles"
  fi

  local depends_on
  depends_on=$(echo "$frontmatter" | awk '/^depends_on:/{flag=1; next} flag && /^  - /{print; next} flag && !/^  /{exit}')
  if [[ -n "$depends_on" ]]; then
    local dep_count
    dep_count=$(echo "$depends_on" | wc -l | tr -d ' ')
    if [[ "${dep_count:-0}" -eq 0 ]]; then
      echo "INFO  $file: depends_on is present but empty — consider removing it or listing dependencies"
    fi
  fi

  # 6. Check headers for convert.sh compatibility
  local soul_headers=0
  local agents_headers=0
  while IFS= read -r line; do
    if [[ "$line" =~ ^##[[:space:]] ]]; then
      local header_lower
      header_lower=$(printf '%s' "$line" | tr '[:upper:]' '[:lower:]')
      local target
      target=$(classify_header_target "$header_lower")
      if [[ "$target" == "soul" ]]; then
        soul_headers=$((soul_headers + 1))
      else
        agents_headers=$((agents_headers + 1))
      fi
    fi
  done <<< "$body"

  if [[ $soul_headers -eq 0 ]]; then
    echo "WARN  $file: no SOUL.md-mapped section headers"
    warnings=$((warnings + 1))
  fi
  if [[ $agents_headers -eq 0 ]]; then
    echo "WARN  $file: no AGENTS.md-mapped section headers"
    warnings=$((warnings + 1))
  fi

  # 7. Check filename prefix matches category directory
  local dir_name file_name
  dir_name=$(basename "$(dirname "$file")")
  file_name=$(basename "$file" .md)
  # game-development has engine subdirectories (unity/, unreal/, godot/, roblox/, blender/)
  if [[ "$dir_name" == "game-development" ]]; then
    dir_name=$(basename "$(dirname "$(dirname "$file")")")
  fi
  # Check that filename starts with "${dir_name}-" (handles compound names like data-science)
  if [[ "$file_name" != "${dir_name}-"* ]]; then
    echo "WARN  $file: filename '${file_name}' should start with '${dir_name}-'"
    warnings=$((warnings + 1))
  fi

  # 8. Check for broken internal links (markdown links to .md files)
  local file_dir; file_dir=$(dirname "$file")
  local links; links=$(echo "$body" | grep -oP '\[([^\]]*)\]\(([^)]+\.md)\)' 2>/dev/null || true)
  if [[ -n "$links" ]]; then
    while IFS= read -r link_line; do
      local url; url=$(echo "$link_line" | grep -oP '\(([^)]+)\)' | tr -d '()')
      [[ -n "$url" ]] || continue
      [[ "$url" =~ ^https?:// ]] && continue
      local target
      if [[ "$url" =~ ^/ ]]; then target="$REPO_ROOT$url"
      else target="$file_dir/$url"; fi
      target=$(cd "$(dirname "$target")" 2>/dev/null && echo "$(pwd)/$(basename "$target")" 2>/dev/null || echo "$target")
      if [[ ! -f "$target" ]]; then
        echo "WARN  $file: broken link '${url}' → target not found"
        warnings=$((warnings + 1))
      fi
    done <<< "$links"
  fi

  # 9. Check content freshness (warn if last git change > 12 months ago)
  if git -C "$REPO_ROOT" log -1 --format="%ad" --date=short -- "$file" 2>/dev/null | grep -q .; then
    local last_date; last_date=$(git -C "$REPO_ROOT" log -1 --format="%ad" --date=short -- "$file" 2>/dev/null)
    local cutoff; cutoff=$(date -d "12 months ago" +%Y-%m-%d 2>/dev/null || date -v-12m +%Y-%m-%d 2>/dev/null || echo "")
    if [[ -n "$cutoff" && "$last_date" < "$cutoff" ]]; then
      echo "INFO  $file: last modified $last_date (>12 months ago, may be stale)"
    fi
  fi
}

# Collect files
files=()
if [[ $# -gt 0 ]]; then
  files=("$@")
else
  for dir in "${AGENT_DIRS[@]}"; do
    [[ -d "$dir" ]] || continue
    while IFS= read -r f; do
      files+=("$f")
    done < <(find "$dir" -maxdepth 2 -name "*.md" -type f | sort)
  done
fi

if [[ ${#files[@]} -eq 0 ]]; then
  echo "No agent files found."
  exit 1
fi

echo "Linting ${#files[@]} agent files in ${#AGENT_DIRS[@]} categories..."
echo ""

for file in "${files[@]}"; do
  lint_file "$file"
done

echo ""
echo "═══════════════════════════════════"
echo "Files:    ${#files[@]}"
echo "Errors:   ${errors}"
echo "Warnings: ${warnings}"
echo "Short:    ${short_files} (< 100 words)"
echo "═══════════════════════════════════"

if [[ $errors -gt 0 ]]; then
  echo "FAILED — fix errors before merging"
  exit 1
else
  echo "PASSED"
  exit 0
fi
