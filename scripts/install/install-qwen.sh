#!/usr/bin/env bash
#
# install-qwen.sh -- Install agents for Qwen Code.

[[ -n "${_AGENCY_INSTALL_QWEN_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_QWEN_GUARD=1

install_qwen() {
  local src="$INTEGRATIONS/qwen/agents"
  local dest; dest="$(resolve_dest qwen "${PWD}/.qwen/agents")"
  local count=0

  [[ -d "$src" ]] || { err "integrations/qwen missing. Run convert.sh first."; return 1; }

  mkdir -p "$dest"

  local f
  while IFS= read -r -d '' f; do
    slug_allowed "$(basename "$f" .md)" || continue
    install_file "$f" "$dest/"
    incr count
  done < <(find "$src" -maxdepth 1 -name "*.md" -print0)

  ok "Qwen Code: installed $count agents to $dest"
  warn "Qwen Code: project-scoped. Run from your project root to install there."
  warn "Tip: Run '/agents manage' in Qwen Code to refresh, or restart session"
}
