#!/usr/bin/env bash
#
# _discover_dirs.sh — Shared agent directory discovery for The Agency scripts.
#
# Source this file (don't execute directly) to get the discover_agent_dirs()
# function. All scripts that need to iterate over agent category directories
# should source this single file so exclusion lists stay in sync.
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]}")/_discover_dirs.sh"
#   AGENT_DIRS=()
#   while IFS= read -r d; do AGENT_DIRS+=("$d"); done < <(discover_agent_dirs)
#
# Requires: REPO_ROOT to be set to the repository root before calling.

# discover_agent_dirs — print every category directory under REPO_ROOT that
# contains at least one .md file, excluding non-agent directories.
#
# Output: one directory name per line
discover_agent_dirs() {
  for d in "$REPO_ROOT"/*/; do
    local dname="${d%/}"; dname="${dname##*/}"
    case "$dname" in
      # Tooling / generated / docs — never contain agent definitions
      examples|integrations|scripts|docs|schemas) continue ;;
      # Dot-directories — bash */ normally skips these, but be explicit
      .git|.github|.vs) continue ;;
    esac
    local count
    count=$(find "$d" -maxdepth 1 -name '*.md' -type f 2>/dev/null | wc -l)
    (( count > 0 )) && echo "$dname"
  done
}
