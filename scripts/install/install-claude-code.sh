#!/usr/bin/env bash
#
# install-claude-code.sh -- Install/uninstall agents for Claude Code.
#
# Sourced by install.sh after lib.sh.  Requires SCRIPT_DIR, REPO_ROOT,
# AGENT_DIRS, slug_allowed, install_file, resolve_dest, ok, warn, err, etc.
# from lib.sh to already be in scope.

# Guard against double-inclusion
[[ -n "${_AGENCY_INSTALL_CLAUDE_CODE_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_CLAUDE_CODE_GUARD=1

install_claude_code() {
  local dest; dest="$(resolve_dest claude-code "${HOME}/.claude/agents")"
  local count=0 dir f slug
  mkdir -p "$dest"
  for dir in "${AGENT_DIRS[@]}"; do
    [[ -d "$REPO_ROOT/$dir" ]] || continue
    while IFS= read -r -d '' f; do
      is_agent_file "$f" || continue
      slug="$(basename "$f" .md)"; slug_allowed "$slug" || continue
      install_file "$f" "$dest/"; incr count
    done < <(find "$REPO_ROOT/$dir" -name "*.md" -type f -print0)
  done
  ok "Claude Code: $count agents -> $dest"
}

uninstall_claude_code() {
  uninstall_scoped "Claude Code" "$(resolve_dest claude-code "${HOME}/.claude/agents")" "" ".md"
}
