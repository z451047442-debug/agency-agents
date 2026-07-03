#!/usr/bin/env bash
#
# clean.sh — Cleanup generated and temporary files for The Agency.
#
# Usage:
#   ./scripts/clean.sh                  # clean generated integrations (safe)
#   ./scripts/clean.sh --all            # deep clean (integrations + temp + pycache)
#   ./scripts/clean.sh --dry-run        # preview what would be deleted
#   ./scripts/clean.sh --all --dry-run  # preview deep clean
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
  sed -n '3,9p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

# --- Format bytes into human-readable form ---
format_bytes() {
  local bytes="$1"
  if [[ $bytes -ge 1073741824 ]]; then
    printf '%.1fGB' "$(echo "scale=1; $bytes / 1073741824" | bc 2>/dev/null || python3 -c "print(round($bytes/1073741824,1))" 2>/dev/null || echo "$(( bytes / 1073741824 ))")"
  elif [[ $bytes -ge 1048576 ]]; then
    printf '%.1fMB' "$(echo "scale=1; $bytes / 1048576" | bc 2>/dev/null || python3 -c "print(round($bytes/1048576,1))" 2>/dev/null || echo "$(( bytes / 1048576 ))")"
  elif [[ $bytes -ge 1024 ]]; then
    printf '%.1fKB' "$(echo "scale=1; $bytes / 1024" | bc 2>/dev/null || python3 -c "print(round($bytes/1024,1))" 2>/dev/null || echo "$(( bytes / 1024 ))")"
  else
    printf '%dB' "$bytes"
  fi
}

# --- Get size of a path (for single files or directories) ---
get_size() {
  local path="$1"
  if [[ -f "$path" ]]; then
    stat -c%s "$path" 2>/dev/null || stat -f%z "$path" 2>/dev/null || echo 0
  elif [[ -d "$path" ]]; then
    # Portable du without --max-depth (non-POSIX on some platforms)
    local total=0
    while IFS= read -r f; do
      local sz
      sz="$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null || echo 0)"
      total=$(( total + sz ))
    done < <(find "$path" -type f 2>/dev/null || true)
    echo "$total"
  else
    echo 0
  fi
}

# --- Count files in a path ---
count_files() {
  local path="$1"
  if [[ -f "$path" ]]; then
    echo 1
  elif [[ -d "$path" ]]; then
    find "$path" -type f 2>/dev/null | wc -l | tr -d ' '
  else
    echo 0
  fi
}

# --- Collect integration paths to clean ---
collect_integration_paths() {
  local base="$REPO_ROOT/integrations"

  # antigravity: agency-*/ subdirectories
  if [[ -d "$base/antigravity" ]]; then
    for d in "$base/antigravity"/agency-*/; do
      [[ -d "$d" ]] && echo "$d"
    done
  fi

  # gemini-cli: skills/ directory
  if [[ -d "$base/gemini-cli/skills" ]]; then
    echo "$base/gemini-cli/skills"
  fi
  # gemini-cli: gemini-extension.json
  if [[ -f "$base/gemini-cli/gemini-extension.json" ]]; then
    echo "$base/gemini-cli/gemini-extension.json"
  fi

  # opencode: agents/ directory
  if [[ -d "$base/opencode/agents" ]]; then
    echo "$base/opencode/agents"
  fi

  # cursor: rules/ directory
  if [[ -d "$base/cursor/rules" ]]; then
    echo "$base/cursor/rules"
  fi

  # aider: CONVENTIONS.md
  if [[ -f "$base/aider/CONVENTIONS.md" ]]; then
    echo "$base/aider/CONVENTIONS.md"
  fi

  # windsurf: .windsurfrules
  if [[ -f "$base/windsurf/.windsurfrules" ]]; then
    echo "$base/windsurf/.windsurfrules"
  fi

  # openclaw: everything except README.md
  if [[ -d "$base/openclaw" ]]; then
    for item in "$base/openclaw"/*; do
      local bn
      bn="$(basename "$item")"
      [[ "$bn" == "README.md" ]] && continue
      [[ -e "$item" ]] && echo "$item"
    done
  fi

  # qwen: agents/ directory
  if [[ -d "$base/qwen/agents" ]]; then
    echo "$base/qwen/agents"
  fi

  # kimi: subdirectories (except README.md)
  if [[ -d "$base/kimi" ]]; then
    for item in "$base/kimi"/*/; do
      [[ -d "$item" ]] && echo "$item"
    done
  fi
}

# --- Collect extra paths for --all mode ---
collect_all_paths() {
  cd "$REPO_ROOT"

  # __pycache__/ directories
  find . -type d -name '__pycache__' 2>/dev/null | while IFS= read -r d; do
    echo "$REPO_ROOT/${d#./}"
  done

  # *.pyc files (explicit)
  find . -type f -name '*.pyc' 2>/dev/null | while IFS= read -r f; do
    echo "$REPO_ROOT/${f#./}"
  done

  # .DS_Store (macOS)
  find . -type f -name '.DS_Store' 2>/dev/null | while IFS= read -r f; do
    echo "$REPO_ROOT/${f#./}"
  done

  # Thumbs.db (Windows)
  find . -type f -name 'Thumbs.db' 2>/dev/null | while IFS= read -r f; do
    echo "$REPO_ROOT/${f#./}"
  done

  # *.tmp and *.temp files
  find . -type f \( -name '*.tmp' -o -name '*.temp' \) 2>/dev/null | while IFS= read -r f; do
    echo "$REPO_ROOT/${f#./}"
  done

  # .cache/ directories
  find . -type d -name '.cache' 2>/dev/null | while IFS= read -r d; do
    echo "$REPO_ROOT/${d#./}"
  done
}

# --- Main ---

main() {
  local mode="safe"
  local dry_run=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --all)       mode="all"; shift ;;
      --dry-run)   dry_run=true; shift ;;
      --help|-h)   usage ;;
      *)           echo "${RED}Unknown option: $1${RESET}" >&2; usage ;;
    esac
  done

  echo ""
  echo "${BOLD}=== The Agency Cleanup ===${RESET}"
  echo ""

  if $dry_run; then
    echo "${YELLOW}Dry run — no files will be deleted.${RESET}"
    echo "Would remove:"
    echo ""
  fi

  # Collect paths
  local paths=()
  while IFS= read -r p; do
    [[ -z "$p" || ! -e "$p" ]] && continue
    paths+=("$p")
  done < <(collect_integration_paths)

  local extra_paths=()
  if [[ "$mode" == "all" ]]; then
    while IFS= read -r p; do
      [[ -z "$p" || ! -e "$p" ]] && continue
      extra_paths+=("$p")
    done < <(collect_all_paths)
  fi

  # Combine
  local all_paths=()
  for p in "${paths[@]}"; do all_paths+=("$p"); done
  for p in "${extra_paths[@]}"; do all_paths+=("$p"); done

  if [[ ${#all_paths[@]} -eq 0 ]]; then
    echo "${GREEN}Nothing to clean.${RESET}"
    echo ""
    exit 0
  fi

  # Compute stats and optionally delete
  local total_dirs=0
  local total_files=0
  local total_bytes=0

  for p in "${all_paths[@]}"; do
    local fc=0 sz=0
    fc="$(count_files "$p")"
    fc="${fc:-0}"
    sz="$(get_size "$p")"
    sz="${sz:-0}"
    total_files=$(( total_files + fc ))
    total_bytes=$(( total_bytes + sz ))

    # Count as a "dir" if it's a directory (not a single file)
    if [[ -d "$p" ]]; then
      total_dirs=$(( total_dirs + 1 ))
    fi

    # Display
    if $dry_run; then
      local rel
      rel="${p#$REPO_ROOT/}"
      local pretty_sz
      pretty_sz="$(format_bytes "$sz")"
      if [[ -f "$p" ]]; then
        echo "  $rel (1 file, ${pretty_sz})"
      else
        echo "  $rel/ (${fc} files, ${pretty_sz})"
      fi
    fi
  done

  local pretty_total
  pretty_total="$(format_bytes "$total_bytes")"

  if $dry_run; then
    echo ""
    echo "  ... ${#all_paths[@]} paths, ${total_files} files, ${pretty_total} total"
    echo ""
    echo "Run without ${GREEN}--dry-run${RESET} to clean."
    exit 0
  fi

  # Actually delete
  for p in "${all_paths[@]}"; do
    if [[ -d "$p" ]]; then
      rm -rf "$p"
    elif [[ -f "$p" ]]; then
      rm -f "$p"
    fi
  done

  echo "Cleaned integrations: ${total_dirs} dirs, ${total_files} files, ${pretty_total} freed."

  if [[ "$mode" == "all" ]]; then
    # Count extra
    local extra_dirs=0 extra_files=0 extra_bytes=0
    for p in "${extra_paths[@]}"; do
      local fc sz
      fc="$(count_files "$p")"; fc="${fc:-0}"
      sz="$(get_size "$p")"; sz="${sz:-0}"
      extra_files=$(( extra_files + fc ))
      extra_bytes=$(( extra_bytes + sz ))
      [[ -d "$p" ]] && extra_dirs=$(( extra_dirs + 1 ))
    done
    if [[ ${#extra_paths[@]} -gt 0 ]]; then
      local extra_pretty
      extra_pretty="$(format_bytes "$extra_bytes")"
      echo "Cleaned extras:   ${extra_dirs} dirs, ${extra_files} files, ${extra_pretty} freed."
    fi
  fi

  echo "Done."
  echo ""
}

main "$@"
