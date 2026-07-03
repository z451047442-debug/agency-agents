#!/usr/bin/env bash
#
# agent-diff.sh — Diff agent files between versions and summarize changes.
#
# Usage:
#   ./scripts/agent-diff.sh path/to/agent.md           # diff against last commit
#   ./scripts/agent-diff.sh path/to/agent.md --since 7  # diff against 7 days ago
#   ./scripts/agent-diff.sh path/to/agent.md --commit abc123  # diff against specific commit
#   ./scripts/agent-diff.sh --category infrastructure    # show all changed agents in category
#   ./scripts/agent-diff.sh --changed                    # list all changed agent files since last commit
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Colour helpers ---
if [[ -t 1 && -z "${NO_COLOR:-}" && "${TERM:-}" != "dumb" ]]; then
  GREEN=$'\033[0;32m'
  YELLOW=$'\033[1;33m'
  RED=$'\033[0;31m'
  BOLD=$'\033[1m'
  RESET=$'\033[0m'
else
  GREEN=''; YELLOW=''; RED=''; BOLD=''; RESET=''
fi

# --- Usage ---
usage() {
  sed -n '3,10p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

# --- Resolve to repo-relative path ---
repo_relative() {
  local f="$1"
  f="$(cd "$(dirname "$f")" 2>/dev/null && pwd)/$(basename "$f")"
  printf '%s' "${f#$REPO_ROOT/}"
}

# --- Find the baseline commit for a file ---
resolve_baseline() {
  local file="$1" since="${2:-}" commit="${3:-}"

  if [[ -n "$commit" ]]; then
    if git -C "$REPO_ROOT" cat-file -e "$commit" 2>/dev/null; then
      echo "$commit"
      return
    else
      echo "ERROR: commit '$commit' not found" >&2
      exit 1
    fi
  fi

  if [[ -n "$since" ]]; then
    local since_date
    # Cross-platform "N days ago": use perl if available, otherwise python, otherwise approximate
    if command -v perl &>/dev/null; then
      since_date="$(perl -e "use POSIX; print POSIX::strftime('%Y-%m-%d', localtime(time - $since * 86400))")"
    elif command -v python3 &>/dev/null; then
      since_date="$(python3 -c "from datetime import datetime, timedelta; print((datetime.now() - timedelta(days=$since)).strftime('%Y-%m-%d'))")"
    elif command -v python &>/dev/null; then
      since_date="$(python -c "from datetime import datetime, timedelta; print((datetime.now() - timedelta(days=$since)).strftime('%Y-%m-%d'))")"
    else
      echo "ERROR: need perl or python to compute date for --since" >&2
      exit 1
    fi

    local commit_hash
    commit_hash="$(git -C "$REPO_ROOT" log --before="$since_date 00:00:00" -n 1 --format='%H' -- "$file" 2>/dev/null || true)"
    if [[ -z "$commit_hash" ]]; then
      # Fallback: use the oldest commit that touched this file
      commit_hash="$(git -C "$REPO_ROOT" log --reverse -n 1 --format='%H' -- "$file" 2>/dev/null || true)"
      if [[ -z "$commit_hash" ]]; then
        echo "ERROR: no commit history found for '$file' (untracked file?)" >&2
        exit 1
      fi
    fi
    echo "$commit_hash"
    return
  fi

  # Default: last commit that touched this file
  local commit_hash
  commit_hash="$(git -C "$REPO_ROOT" log -n 1 --format='%H' -- "$file" 2>/dev/null || true)"
  if [[ -z "$commit_hash" ]]; then
    echo "ERROR: no commit history found for '$file' (untracked file?)" >&2
    exit 1
  fi
  echo "$commit_hash"
}

# --- Parse frontmatter from a file revision ---
get_frontmatter() {
  local file="$1" commit="${2:-}"
  if [[ -n "$commit" ]]; then
    git -C "$REPO_ROOT" show "${commit}:$(repo_relative "$file")" 2>/dev/null | awk 'NR==1{next} /^---$/{exit} {print}'
  else
    awk 'NR==1{next} /^---$/{exit} {print}' "$file"
  fi
}

# --- Parse body from a file revision ---
get_body() {
  local file="$1" commit="${2:-}"
  if [[ -n "$commit" ]]; then
    git -C "$REPO_ROOT" show "${commit}:$(repo_relative "$file")" 2>/dev/null | awk 'BEGIN{fm=0} /^---$/{fm++; next} fm>=2{print}'
  else
    awk 'BEGIN{fm=0} /^---$/{fm++; next} fm>=2{print}' "$file"
  fi
}

# --- Get word count of body ---
get_word_count() {
  local file="$1" commit="${2:-}"
  echo "$(get_body "$file" "$commit" | wc -w | tr -d ' ')"
}

# --- Get a frontmatter field value ---
get_field() {
  local field="$1" frontmatter="$2"
  echo "$frontmatter" | awk -v f="$field" '$0 ~ "^" f ":" { sub("^" f ": *", ""); print; exit }'
}

# --- Extract section headers from body ---
get_sections() {
  local body="$1"
  echo "$body" | grep -E '^## ' | sed 's/^## //'
}

# --- Compute section word counts ---
section_word_counts() {
  local body="$1"
  local current_section="(preamble)"
  declare -A counts  # bash 4+, but we use a simpler approach

  local output=""
  local count=0

  while IFS= read -r line; do
    if [[ "$line" =~ ^##[[:space:]] ]]; then
      if [[ "$current_section" != "(preamble)" ]] || [[ $count -gt 0 ]]; then
        printf '%s\t%d\n' "$current_section" "$count"
      fi
      current_section="$(echo "$line" | sed 's/^## //' | sed 's/[^a-zA-Z0-9 &_-]//g' | tr -s ' ')"
      count=0
    else
      count=$(( count + $(echo "$line" | wc -w) ))
    fi
  done <<< "$body"

  # Flush last section
  printf '%s\t%d\n' "$current_section" "$count"
}

# --- Summarize frontmatter changes ---
diff_frontmatter() {
  local old_fm="$1" new_fm="$2"

  local old_fields=() new_fields=()
  while IFS= read -r line; do
    old_fields+=("$(echo "$line" | awk -F: '{print $1}')")
  done < <(echo "$old_fm" | grep -E '^[a-z_]+:' | awk -F: '{print $1}')
  while IFS= read -r line; do
    new_fields+=("$(echo "$line" | awk -F: '{print $1}')")
  done < <(echo "$new_fm" | grep -E '^[a-z_]+:' | awk -F: '{print $1}')

  # Added fields
  for f in "${new_fields[@]}"; do
    if ! printf '%s\n' "${old_fields[@]}" | grep -qx "$f"; then
      echo "    added: '${f}'"
    fi
  done

  # Removed fields
  for f in "${old_fields[@]}"; do
    if ! printf '%s\n' "${new_fields[@]}" | grep -qx "$f"; then
      echo "    removed: '${f}'"
    fi
  done

  # Changed fields
  for f in "${new_fields[@]}"; do
    if printf '%s\n' "${old_fields[@]}" | grep -qx "$f"; then
      local old_val new_val
      old_val="$(get_field "$f" "$old_fm")"
      new_val="$(get_field "$f" "$new_fm")"
      if [[ "$old_val" != "$new_val" ]]; then
        echo "    modified: '${f}'"
      fi
    fi
  done
}

# --- Diff a single agent file ---
diff_single() {
  local file="$1" baseline="$2"
  local rel
  rel="$(repo_relative "$file")"

  # Verify file is an agent (has frontmatter)
  local first_line
  first_line="$(head -1 "$file")"
  if [[ "$first_line" != "---" ]]; then
    echo "WARN: $rel does not appear to be an agent file (no YAML frontmatter)"
  fi

  # Get commit info for baseline
  local commit_info=""
  local commit_date=""
  local commit_author=""
  local days_ago=""

  if [[ -n "$baseline" ]]; then
    commit_info="$(git -C "$REPO_ROOT" show -s --format='%h %s' "$baseline" 2>/dev/null || echo "unknown")"
    commit_date="$(git -C "$REPO_ROOT" show -s --format='%ci' "$baseline" 2>/dev/null || echo "")"
    commit_author="$(git -C "$REPO_ROOT" show -s --format='%an' "$baseline" 2>/dev/null || echo "")"

    if [[ -n "$commit_date" ]]; then
      if command -v python3 &>/dev/null; then
        days_ago="$(python3 -c "
from datetime import datetime, timezone
commit_dt = datetime.strptime('$commit_date', '%Y-%m-%d %H:%M:%S %z')
delta = datetime.now(timezone.utc) - commit_dt
print(delta.days)
")"
      elif command -v python &>/dev/null; then
        days_ago="$(python -c "
from datetime import datetime, timezone
commit_dt = datetime.strptime('$commit_date', '%Y-%m-%d %H:%M:%S %z')
delta = datetime.now(timezone.utc) - commit_dt
print(delta.days)
")"
      fi
    fi
  fi

  echo ""
  echo "${BOLD}=== agent-diff: $rel ===${RESET}"
  echo -n "Last changed: "
  if [[ -n "$days_ago" ]]; then
    echo "${days_ago} days ago (commit ${commit_info})"
  elif [[ -n "$commit_info" ]]; then
    echo "commit ${commit_info}"
  else
    echo "unknown"
  fi

  if [[ -n "$commit_author" ]]; then
    echo "Author: ${commit_author}"
  fi

  echo ""
  echo "Changes:"

  # Frontmatter diff
  local old_fm new_fm
  old_fm="$(get_frontmatter "$file" "$baseline" || true)"
  new_fm="$(get_frontmatter "$file" "" || true)"

  local fm_diffs
  fm_diffs="$(diff_frontmatter "$old_fm" "$new_fm")"
  if [[ -n "$fm_diffs" ]]; then
    echo "  Frontmatter:"
    echo "$fm_diffs"
  else
    echo "  Frontmatter: unchanged"
  fi

  # Section diffs
  local old_body new_body
  old_body="$(get_body "$file" "$baseline" 2>/dev/null || true)"
  new_body="$(get_body "$file" "" 2>/dev/null || true)"

  local old_sections new_sections
  old_sections="$(section_word_counts "$old_body")"
  new_sections="$(section_word_counts "$new_body")"

  echo "  Sections:"

  # Build associative map of section name -> old count
  declare -A old_map
  while IFS=$'\t' read -r sec cnt; do
    [[ -n "$sec" ]] && old_map["$sec"]="${cnt:-0}"
  done <<< "$old_sections"

  declare -A new_map
  while IFS=$'\t' read -r sec cnt; do
    [[ -n "$sec" ]] && new_map["$sec"]="${cnt:-0}"
  done <<< "$new_sections"

  # Detect modified sections
  local all_sections=()
  for sec in "${!old_map[@]}"; do all_sections+=("$sec"); done
  for sec in "${!new_map[@]}"; do
    if ! printf '%s\n' "${all_sections[@]}" | grep -qxF "$sec"; then
      all_sections+=("$sec")
    fi
  done

  for sec in "${all_sections[@]}"; do
    local o="${old_map[$sec]:-0}" n="${new_map[$sec]:-0}"
    if [[ "$o" != "$n" ]]; then
      local delta=$(( n - o ))
      local sign="+"
      [[ $delta -lt 0 ]] && sign=""
      if [[ $o -eq 0 ]]; then
        echo "    ${sec} — ${sign}${delta} words (new section)"
      elif [[ $n -eq 0 ]]; then
        echo "    ${sec} — removed (was ${o} words)"
      else
        echo "    ${sec} — ${sign}${delta} words"
      fi
    fi
  done

  # Word count summary
  local old_wc new_wc
  old_wc="$(get_word_count "$file" "$baseline")"
  new_wc="$(get_word_count "$file" "")"
  local delta=$(( new_wc - old_wc ))
  local pct=0
  if [[ $old_wc -gt 0 ]]; then
    pct=$(( delta * 100 / old_wc ))
  fi
  local sign="+"
  [[ $delta -lt 0 ]] && sign=""

  echo ""
  echo "  Word count: ${old_wc} → ${new_wc} (${sign}${delta} words, ${sign}${pct}%)"
}

# --- Main ---

main() {
  cd "$REPO_ROOT"

  local mode="single"
  local file=""
  local category=""
  local since=""
  local commit=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --changed)   mode="changed"; shift ;;
      --category)  mode="category"; category="${2:?'--category requires a value'}"; shift 2 ;;
      --since)     since="${2:?'--since requires a value'}"; shift 2 ;;
      --commit)    commit="${2:?'--commit requires a value'}"; shift 2 ;;
      --help|-h)   usage ;;
      -*)          echo "Unknown option: $1" >&2; usage ;;
      *)           file="$1"; shift ;;
    esac
  done

  # --changed mode: list all changed agent .md files
  if [[ "$mode" == "changed" ]]; then
    echo "${BOLD}Changed agent files since last commit:${RESET}"
    echo ""

    local changed
    changed="$(git diff --name-only HEAD -- '*.md' '**/*.md' 2>/dev/null | grep -v '^docs/' | grep -v '^examples/' | grep -v '^integrations/' | grep -v '^.github/' | grep -v '^README.md' | grep -v '^CONTRIBUTING' || true)"

    if [[ -z "$changed" ]]; then
      echo "  (no agent files changed)"
      exit 0
    fi

    local count=0
    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      echo "  $f"
      count=$(( count + 1 ))
    done <<< "$changed"

    echo ""
    echo "${BOLD}Total: $count agent file(s) changed.${RESET}"
    echo "Run: ${GREEN}./scripts/agent-diff.sh <file>${RESET} for details."
    exit 0
  fi

  # --category mode: changed files filtered by category
  if [[ "$mode" == "category" ]]; then
    if [[ ! -d "$REPO_ROOT/$category" ]]; then
      echo "${RED}ERROR: category '$category' not found${RESET}" >&2
      exit 1
    fi

    echo "${BOLD}Changed agents in ${category}/:${RESET}"
    echo ""

    local changed
    changed="$(git diff --name-only HEAD -- "$category/"*.md 2>/dev/null || true)"

    if [[ -z "$changed" ]]; then
      echo "  (no agents changed in ${category}/)"
      exit 0
    fi

    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      diff_single "$f" "$(resolve_baseline "$f" "$since" "$commit")"
    done <<< "$changed"
    exit 0
  fi

  # Single file mode
  if [[ -z "$file" ]]; then
    echo "${RED}ERROR: no file specified${RESET}" >&2
    usage
  fi

  if [[ ! -f "$file" ]]; then
    echo "${RED}ERROR: file not found: $file${RESET}" >&2
    exit 1
  fi

  local baseline
  baseline="$(resolve_baseline "$file" "$since" "$commit")"
  diff_single "$file" "$baseline"
}

main "$@"
