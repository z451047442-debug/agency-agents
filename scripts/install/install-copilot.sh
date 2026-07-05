#!/usr/bin/env bash
#
# install-copilot.sh -- Install agents for GitHub Copilot.
#
# Sourced by install.sh after lib.sh.

[[ -n "${_AGENCY_INSTALL_COPILOT_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_COPILOT_GUARD=1

install_copilot() {
  local dest_github; dest_github="$(resolve_dest copilot "${HOME}/.github/agents")"
  local dest_copilot="${HOME}/.copilot/agents"
  local count=0 dir f slug
  mkdir -p "$dest_github" "$dest_copilot"
  for dir in "${AGENT_DIRS[@]}"; do
    [[ -d "$REPO_ROOT/$dir" ]] || continue
    while IFS= read -r -d '' f; do
      is_agent_file "$f" || continue
      slug="$(agent_slug "$f")"; slug_allowed "$slug" || continue
      install_file "$f" "$dest_github/"
      install_file "$f" "$dest_copilot/"
      incr count
    done < <(find "$REPO_ROOT/$dir" -name "*.md" -type f -print0)
  done
  ok "Copilot: $count agents -> $dest_github"
  ok "Copilot: $count agents -> $dest_copilot"
  warn "Copilot: Verify VS Code setting 'chat.agentFilesLocations' includes your install path."
  dim  "         Open Settings (Ctrl/Cmd+,) -> search 'chat.agentFilesLocations'"
}
