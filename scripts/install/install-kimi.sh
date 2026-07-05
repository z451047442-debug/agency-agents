#!/usr/bin/env bash
#
# install-kimi.sh -- Install agents for Kimi Code.

[[ -n "${_AGENCY_INSTALL_KIMI_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_KIMI_GUARD=1

install_kimi() {
  local src="$INTEGRATIONS/kimi"
  local dest; dest="$(resolve_dest kimi "${HOME}/.config/kimi/agents")"
  local count=0

  [[ -d "$src" ]] || { err "integrations/kimi missing. Run convert.sh first."; return 1; }

  mkdir -p "$dest"

  local d
  while IFS= read -r -d '' d; do
    local name; name="$(basename "$d")"
    slug_allowed "$name" || continue
    mkdir -p "$dest/$name"
    install_file "$d/agent.yaml" "$dest/$name/agent.yaml"
    install_file "$d/system.md" "$dest/$name/system.md"
    incr count
  done < <(find "$src" -mindepth 1 -maxdepth 1 -type d -print0)

  ok "Kimi Code: installed $count agents to $dest"
  ok "Usage: kimi --agent-file ~/.config/kimi/agents/<agent-name>/agent.yaml"
}
